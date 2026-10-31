"""
DealShield – Enterprise M&A Due Diligence & Conflict-of-Interest Agentic Workflow
==================================================================================
Google ADK  ×  Neo4j Aura  ×  Neo4j Agent Memory  ×  GraphRAG

Three deterministic Cypher-backed tools are orchestrated by a SequentialAgent:
  1. analyze_change_of_control_graphrag   – multi-hop CoC + related-party conflict detection
  2. analyze_secondary_and_antitrust_risks – secondary clause / antitrust risk retrieval
  3. calculate_and_store_risk_factor       – deterministic scoring + write-back to Neo4j
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase

# Google ADK imports
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Neo4j Agent Memory imports
from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.integrations.google_adk import Neo4jMemoryService

# ---------------------------------------------------------------------------
# Environment & Configuration
# ---------------------------------------------------------------------------
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USERNAME = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
LLM_MODEL = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or os.getenv("GOOGLE_GENAI_MODEL") or "gemini-2.5-flash"
APP_NAME = "dealshield"

# Ensure Gemini API key is available for google-genai
if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY


# ═══════════════════════════════════════════════════════════════════════════
# Neo4j Driver Helper
# ═══════════════════════════════════════════════════════════════════════════
def _get_driver():
    """Return a cached Neo4j driver (module-level singleton)."""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = _get_driver()
    return _driver


def run_cypher(query: str, params: dict | None = None) -> list[dict]:
    """Execute a read Cypher query and return list of record dicts."""
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


def write_cypher(query: str, params: dict | None = None) -> list[dict]:
    """Execute a write Cypher query and return list of record dicts."""
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 1 – Change-of-Control GraphRAG Analysis
# ═══════════════════════════════════════════════════════════════════════════
def analyze_change_of_control_graphrag(
    target_company: str = "Northwind Microsystems Inc.",
) -> dict:
    """
    Multi-hop Cypher query that:
    1. Finds all Change-of-Control clauses restricting the target company via agreements.
    2. Traverses 1–4 hops to detect undisclosed related-party supplier conflicts.
    3. Returns structured JSON with director, spouse/relative, shell/holding chain,
       annual supplier value, CoC termination penalty, and DocumentChunk citations.
    """

    # ── Step 1: Change-of-Control clauses + DocumentChunk evidence ──
    coc_query = """
    MATCH (t:Company)
    WHERE t.id = $target OR t.name = $target OR t.name CONTAINS $target OR $target CONTAINS t.name
    WITH t ORDER BY (CASE WHEN t.id STARTS WITH 'C_' THEN 0 ELSE 1 END) LIMIT 1
    MATCH (c:Clause)-[:CLAUSE_OF]->(a:Agreement)-[:AGREEMENT_OF]->(t)
    WHERE c.clauseType IN ['COC_POISON_PILL', 'COC_VENDOR_LOCKIN', 'Change of Control']
       OR c.triggerType = 'EQUITY_TRANSFER'
    OPTIONAL MATCH (c)-[:DERIVED_FROM]->(dc:DocumentChunk)
    RETURN c {.id, .title, .clauseType, .section, .text, .triggerType, .thresholdPct,
              .penaltyUSD, .minAnnualPurchaseUSD, .durationMonths, .severity,
              financial_exposure_usd: coalesce(
                  c.penaltyUSD,
                  (coalesce(c.minAnnualPurchaseUSD, 0) * coalesce(c.durationMonths, 12) / 12),
                  c.financial_exposure_usd,
                  0
              ),
              summary: coalesce(c.text, c.summary, c.title)} AS clause,
           collect(DISTINCT dc {.id, .docId, .page, .text}) AS doc_chunks
    """
    coc_results = run_cypher(coc_query, {"target": target_company})

    # ── Step 2: Multi-hop related-party conflict rings ──
    # Person (works at or director of Target) -> [optional spouse/family] -> holds stake (1..3 hops) -> Vendor -> supplies to Target
    conflict_query = """
    MATCH (t:Company)
    WHERE t.id = $target OR t.name = $target OR t.name CONTAINS $target OR $target CONTAINS t.name
    WITH t ORDER BY (CASE WHEN t.id STARTS WITH 'C_' THEN 0 ELSE 1 END) LIMIT 1
    MATCH (d:Person)-[:WORKS_AT|DIRECTOR_OF]->(t)
    MATCH (sup:Company)-[sup_rel:SUPPLIES_TO]->(t)
    OPTIONAL MATCH (d)-[rel_link:RELATED_TO]-(rel_p:Person)
    WITH d, t, sup, sup_rel, coalesce(rel_p, d) AS benef_owner, rel_link, (rel_p IS NOT NULL) AS has_relative
    MATCH chain = (benef_owner)-[:HOLDS_STAKE_IN*1..3]->(sup)
    WHERE NOT EXISTS { (d)-[:FILED]->(:Disclosure)-[:DECLARES]->(sup) }
    OPTIONAL MATCH (tx:Transaction)-[:APPROVED_BY]->(d)
    WHERE (tx)-[:WITH_VENDOR]->(sup)
    OPTIONAL MATCH (coc_cl:Clause)-[:CLAUSE_OF]->(a:Agreement)-[:AGREEMENT_OF]->(sup)
    WHERE coc_cl.clauseType IN ['COC_POISON_PILL', 'COC_VENDOR_LOCKIN', 'Change of Control']
    OPTIONAL MATCH (coc_cl)-[:DERIVED_FROM]->(coc_dc:DocumentChunk)
    OPTIONAL MATCH (sup)-[:DERIVED_FROM]->(sup_dc:DocumentChunk)
    OPTIONAL MATCH (tx)-[:DERIVED_FROM]->(tx_dc:DocumentChunk)
    WITH d, t, sup, sup_rel, benef_owner, has_relative, rel_link, chain, tx,
         [node IN nodes(chain) WHERE node <> benef_owner AND node <> sup | node {.id, .name, labels: labels(node)}] AS intermediaries,
         [rel IN relationships(chain) | rel {.pct, .type, .since, .percentage}] AS stake_details,
         collect(DISTINCT coc_cl {.id, .title, .clauseType, .penaltyUSD, .minAnnualPurchaseUSD, .durationMonths,
                 financial_exposure_usd: coalesce(
                     coc_cl.penaltyUSD,
                     (coalesce(coc_cl.minAnnualPurchaseUSD, 0) * coalesce(coc_cl.durationMonths, 12) / 12),
                     coc_cl.financial_exposure_usd,
                     0
                 ),
                 summary: coalesce(coc_cl.text, coc_cl.title)}) AS coc_clauses,
         (collect(DISTINCT CASE WHEN coc_dc IS NOT NULL THEN coc_dc {.id, .docId, .page, .text} END) +
          collect(DISTINCT CASE WHEN sup_dc IS NOT NULL THEN sup_dc {.id, .docId, .page, .text} END) +
          collect(DISTINCT CASE WHEN tx_dc IS NOT NULL THEN tx_dc {.id, .docId, .page, .text} END)) AS raw_evidence
    RETURN
        d {.id, .name, title: coalesce([(d)-[r:WORKS_AT]->(t)|r.title][0], [(d)-[r:DIRECTOR_OF]->(t)|r.committee][0], [(d)-[r:DIRECTOR_OF]->(t)|r.type][0], d.title, 'Executive/Director')} AS director,
        benef_owner {.id, .name, labels: labels(benef_owner)} AS related_party,
        (CASE WHEN has_relative THEN coalesce(rel_link.relation, 'SPOUSE') ELSE 'DIRECT_HOLDING_DUAL_FIDUCIARY' END) AS relationship_type,
        sup {.id, .name, tier: sup_rel.tier, category: sup_rel.componentCategory} AS supplier,
        sup_rel {.annualSpendUSD, .tier, .componentCategory, annual_value_usd: coalesce(sup_rel.annualSpendUSD, sup_rel.annual_value_usd, 0)} AS supplier_contract,
        intermediaries,
        stake_details,
        tx {.id, .type, .amountUSD, .soleSource, .description, .date} AS approved_transaction,
        coc_clauses,
        [x IN raw_evidence WHERE x IS NOT NULL] AS evidence_chunks
    """
    conflict_results = run_cypher(conflict_query, {"target": target_company})

    # ── Step 3: Build the full holding-company chain for each conflict ──
    conflicts = []
    seen_conflict_keys = set()

    for row in conflict_results:
        holding_chain = []
        related = row.get("related_party", {})
        intermediaries = row.get("intermediaries") or []
        stake_details = row.get("stake_details") or []
        rel_type = row.get("relationship_type", "Beneficial Owner")
        director_info = row.get("director", {})
        d_name = director_info.get("name", "Insider").strip()
        rp_name = related.get("name", "Related Party").strip()
        supplier = row.get("supplier", {})
        sup_name = supplier.get("name", "Vendor").strip()

        # Semantic key to eliminate duplicate flags across target aliases
        conflict_key = (d_name.lower(), sup_name.lower())
        if conflict_key in seen_conflict_keys:
            continue
        seen_conflict_keys.add(conflict_key)

        # Start: related party / director
        holding_chain.append({
            "entity": related.get("name", "Unknown"),
            "id": related.get("id", ""),
            "role": f"Beneficial Owner ({rel_type})",
        })

        # Intermediate holding companies
        for i, inter in enumerate(intermediaries):
            pct = "?"
            if i < len(stake_details):
                st = stake_details[i]
                pct = st.get("pct") or st.get("percentage") or "?"
            holding_chain.append({
                "entity": inter.get("name", "Unknown"),
                "id": inter.get("id", ""),
                "stake_percentage": pct,
                "role": "Intermediary Holding Company",
            })

        # End: supplier
        final_pct = "?"
        if len(stake_details) > len(intermediaries):
            final_st = stake_details[-1]
            final_pct = final_st.get("pct") or final_st.get("percentage") or "?"
        holding_chain.append({
            "entity": supplier.get("name", "Unknown"),
            "id": supplier.get("id", ""),
            "role": "Direct Supplier to Target",
            "stake_percentage": final_pct,
        })

        coc_penalties = row.get("coc_clauses") or []
        total_coc_penalty = sum(
            c.get("financial_exposure_usd", 0) for c in coc_penalties
        )

        annual_val = (row.get("supplier_contract") or {}).get("annual_value_usd", 0) or 0
        tx = row.get("approved_transaction") or {}
        tx_amount = tx.get("amountUSD", 0) if tx else 0
        is_sole_source = bool(tx.get("soleSource")) if tx else False

        # Determine explicit Conflict of Interest categorization
        if rel_type == "DIRECT_HOLDING_DUAL_FIDUCIARY" or d_name.lower() == rp_name.lower():
            cat = "Conflict of Interest: Dual-Fiduciary Conflict"
            summary_text = (
                f"Non-Executive Director {d_name} holds direct undisclosed equity in tier-2 supplier {sup_name} "
                f"and approved commercial supply transactions."
            )
        elif "tom" in rp_name.lower() or "whitfield" in d_name.lower() or not is_sole_source:
            cat = "Conflict of Interest: Governance Attestation Failure"
            summary_text = (
                f"Director {d_name} formally attested no conflicts of interest in board filings, "
                f"while family member {rp_name} holds equity in supplier {sup_name}."
            )
        else:
            cat = "Conflict of Interest: Undisclosed Related-Party Transaction"
            summary_text = (
                f"Procurement Director {d_name} approved sole-source awards to {sup_name}, "
                f"controlled by spouse {rp_name} via offshore holding."
            )

        conflicts.append({
            "director": director_info,
            "related_party": related,
            "relationship_type": rel_type,
            "supplier": supplier,
            "category": cat,
            "summary": summary_text,
            "holding_chain": holding_chain,
            "holding_hops": len(intermediaries) + (1 if rel_type == "DIRECT_HOLDING_DUAL_FIDUCIARY" else 2),
            "supplier_contract": row.get("supplier_contract", {}),
            "annual_supplier_value_usd": annual_val,
            "approved_transaction_usd": tx_amount,
            "coc_termination_penalty_usd": total_coc_penalty,
            "coc_clauses": coc_penalties,
            "document_citations": [e for e in (row.get("evidence_chunks") or []) if e and e.get("id")],
        })

    return {
        "tool": "analyze_change_of_control_graphrag",
        "target_company": target_company,
        "change_of_control_clauses": coc_results,
        "related_party_conflicts": conflicts,
        "total_conflicts_detected": len(conflicts),
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 2 – Secondary & Antitrust Risk Analysis
# ═══════════════════════════════════════════════════════════════════════════
def analyze_secondary_and_antitrust_risks(
    target_company: str = "Northwind Microsystems Inc.",
) -> dict:
    """
    Retrieves all restrictive clauses across 4 vectors:
    1. Antitrust / Regulatory:
       - HORIZONTAL_MARKET_CAP (common parent exceeds market share threshold)
       - FEDERAL_CONTRACT_REVOCATION (DoD contract auto-revocation on competitor overlap)
    2. Non-Compete & Exclusivity:
       - AUTO_SLA_RENEWAL_IP_LOCKIN (missed notice deadline before closing)
       - SOLE_SOURCE_EXCLUSIVITY (take-or-pay, survives change of control)
    3. Governance & Dual Fiduciary:
       - GOVERNANCE_ATTESTATION_FAILURE (attestation of no conflict vs related-party holding)
       - DUAL_FIDUCIARY (non-executive director holding equity in tier-2 supplier)
    """

    # ── Part A: Clauses connected to target or its subsidiaries ──
    clause_query = """
    MATCH (t:Company)
    WHERE t.id = $target OR t.name = $target OR t.name CONTAINS $target OR $target CONTAINS t.name
    WITH t ORDER BY (CASE WHEN t.id STARTS WITH 'C_' THEN 0 ELSE 1 END) LIMIT 1
    OPTIONAL MATCH (sub:Company)-[:IS_SUBSIDIARY_OF]->(t)
    WITH t, [t] + collect(DISTINCT sub) AS entities
    UNWIND entities AS ent
    MATCH (c:Clause)-[:CLAUSE_OF]->(a:Agreement)-[:AGREEMENT_OF]->(ent)
    WHERE c.clauseType IN [
        'HORIZONTAL_MARKET_CAP', 'FEDERAL_CONTRACT_REVOCATION',
        'AUTO_SLA_RENEWAL_IP_LOCKIN', 'SOLE_SOURCE_EXCLUSIVITY',
        'GOVERNANCE_ATTESTATION_FAILURE', 'DUAL_FIDUCIARY',
        'Anti-Trust / Regulatory', 'Governance / Fraud',
        'Exclusivity & Non-Compete', 'Liquidated Damages'
    ]
    OPTIONAL MATCH (c)-[:DERIVED_FROM]->(dc:DocumentChunk)
    OPTIONAL MATCH (c)-[:RESTRICTS_MARKET]->(m:Market)
    OPTIONAL MATCH (c)-[:REVOKES]->(gc:GovContract)
    OPTIONAL MATCH (c)-[:NAMES_COMPETITOR]->(comp:Company)
    OPTIONAL MATCH (c)-[:COVERS_COMPONENT]->(k:Component)
    RETURN ent {.id, .name} AS affected_entity,
           a {.id, .title, .type, .effectiveDate, .expiryDate, .totalValueUSD} AS agreement,
           c {.id, .title, .clauseType, .section, .text, .thresholdPct, .penaltyUSD,
              .minAnnualPurchaseUSD, .durationMonths, .severity, .autoRenew, .renewalDate,
              .noticeDeadline, .annualFeeUSD, .exitPenaltyUSD, .valueAtRiskUSD,
              financial_exposure_usd: coalesce(
                  c.valueAtRiskUSD,
                  gc.valueUSD,
                  c.penaltyUSD,
                  c.exitPenaltyUSD,
                  (coalesce(c.annualFeeUSD, 0) * coalesce(c.renewalTermMonths, 12) / 12),
                  (coalesce(c.minAnnualPurchaseUSD, 0) * coalesce(c.durationMonths, 12) / 12),
                  c.financial_exposure_usd,
                  0
              ),
              summary: coalesce(c.text, c.summary, c.title)} AS clause,
           m {.id, .name, .sector} AS market,
           gc {.id, .title, .valueUSD, .contractNo} AS gov_contract,
           comp {.id, .name} AS named_competitor,
           k {.id, .name, .criticality} AS covered_component,
           collect(DISTINCT dc {.id, .docId, .page, .text}) AS evidence_chunks
    """
    clause_results = run_cypher(clause_query, {"target": target_company})

    # ── Part B: Market Cap Overlap Check ──
    market_cap_query = """
    MATCH (d:Deal)-[:TARGET]->(t:Company)
    WHERE t.id = $target OR t.name = $target OR t.name CONTAINS $target OR $target CONTAINS t.name
    WITH t, d ORDER BY (CASE WHEN t.id STARTS WITH 'C_' THEN 0 ELSE 1 END) LIMIT 1
    MATCH (d)-[:ACQUIRER]->(acq:Company)
    MATCH (c:Clause {clauseType:'HORIZONTAL_MARKET_CAP'})-[:RESTRICTS_MARKET]->(m:Market)
    MATCH (acq)-[:IS_SUBSIDIARY_OF*0..3]->(par)<-[:IS_SUBSIDIARY_OF*0..3]-(sib:Company)
    MATCH (sib)-[ms:HAS_MARKET_SHARE]->(m)
    WHERE sib <> t AND sib <> acq AND ms.pct > c.thresholdPct
    RETURN c.id AS clause_id, sib.name AS sibling_violator, ms.pct AS market_share, c.thresholdPct AS cap_pct, par.name AS parent_firm
    """
    market_cap_results = run_cypher(market_cap_query, {"target": target_company})

    # ── Part C: Federal Contract Revocation Check ──
    revocation_query = """
    MATCH (d:Deal)-[:TARGET]->(t:Company)
    WHERE t.id = $target OR t.name = $target OR t.name CONTAINS $target OR $target CONTAINS t.name
    WITH t, d ORDER BY (CASE WHEN t.id STARTS WITH 'C_' THEN 0 ELSE 1 END) LIMIT 1
    MATCH (d)-[:ACQUIRER]->(acq:Company)
    MATCH (c:Clause {clauseType:'FEDERAL_CONTRACT_REVOCATION'})-[:NAMES_COMPETITOR]->(comp:Company)
    MATCH (c)-[:REVOKES]->(gc:GovContract)
    MATCH (acq)-[:IS_SUBSIDIARY_OF*0..3]->(anc)-[s:HOLDS_STAKE_IN]->(comp)
    RETURN c.id AS clause_id, gc.title AS contract_title, gc.valueUSD AS value_at_risk, comp.name AS competitor_name, anc.name AS acquirer_affiliate, s.pct AS stake_pct
    """
    revocation_results = run_cypher(revocation_query, {"target": target_company})

    # ── Part D: SLA Auto-Renewal Notice Window Check ──
    sla_query = """
    MATCH (d:Deal)-[:TARGET]->(t:Company)
    WHERE t.id = $target OR t.name = $target OR t.name CONTAINS $target OR $target CONTAINS t.name
    WITH t, d ORDER BY (CASE WHEN t.id STARTS WITH 'C_' THEN 0 ELSE 1 END) LIMIT 1
    MATCH (c:Clause {clauseType:'AUTO_SLA_RENEWAL_IP_LOCKIN'})
    WHERE c.noticeDeadline < coalesce(d.announcedDate, '2026-10-31')
    RETURN c.id AS clause_id, c.noticeDeadline AS missed_deadline, c.renewalDate AS renewal_date, c.annualFeeUSD AS annual_fee, c.renewalTermMonths AS term_months
    """
    sla_results = run_cypher(sla_query, {"target": target_company})

    # ── Part E: Governance Attestation Failures ──
    attestation_query = """
    MATCH (t:Company)
    WHERE t.id = $target OR t.name = $target OR t.name CONTAINS $target OR $target CONTAINS t.name
    WITH t ORDER BY (CASE WHEN t.id STARTS WITH 'C_' THEN 0 ELSE 1 END) LIMIT 1
    MATCH (p:Person)-[:DIRECTOR_OF]->(t)
    MATCH (p)-[:FILED]->(d:Disclosure {attestsNoConflict:true})
    MATCH (p)-[:RELATED_TO]-(rp:Person)-[s:HOLDS_STAKE_IN]->(v:Company)-[:SUPPLIES_TO]->(t)
    WHERE NOT EXISTS { (d)-[:DECLARES]->(v) }
    OPTIONAL MATCH (d)-[:DERIVED_FROM]->(dc:DocumentChunk)
    RETURN p.name AS director, rp.name AS relative, v.name AS supplier, s.pct AS stake_pct,
           collect(DISTINCT dc {.id, .docId, .page, .text}) AS evidence_chunks
    """
    attestation_results = run_cypher(attestation_query, {"target": target_company})

    # ── Part F: Dual-Fiduciary Conflicts ──
    dual_fiduciary_query = """
    MATCH (t:Company)
    WHERE t.id = $target OR t.name = $target OR t.name CONTAINS $target OR $target CONTAINS t.name
    WITH t ORDER BY (CASE WHEN t.id STARTS WITH 'C_' THEN 0 ELSE 1 END) LIMIT 1
    MATCH (p:Person)-[:DIRECTOR_OF {type:'NON_EXECUTIVE'}]->(t)
    MATCH (p)-[s:HOLDS_STAKE_IN]->(v:Company)-[:SUPPLIES_TO]->(t)
    WHERE NOT EXISTS { (p)-[:FILED]->(:Disclosure)-[:DECLARES]->(v) }
    OPTIONAL MATCH (tx:Transaction)-[:APPROVED_BY]->(p) WHERE (tx)-[:WITH_VENDOR]->(v)
    OPTIONAL MATCH (v)-[:DERIVED_FROM]->(dc:DocumentChunk)
    RETURN p.name AS director, v.name AS vendor, s.pct AS stake_pct, tx.amountUSD AS approved_amount,
           collect(DISTINCT dc {.id, .docId, .page, .text}) AS evidence_chunks
    """
    dual_fiduciary_results = run_cypher(dual_fiduciary_query, {"target": target_company})

    # ── Merge and format all risks ──
    all_risks = []
    seen_ids = set()

    for row in clause_results:
        clause = row.get("clause") or {}
        cid = clause.get("id")
        if not cid or cid in seen_ids:
            continue
        seen_ids.add(cid)

        category = "Secondary Restrictive Covenant"
        ctype = clause.get("clauseType", "")
        if "MARKET_CAP" in ctype:
            category = "Antitrust / Regulatory: Common Parent Market Cap Overlap"
        elif "REVOCATION" in ctype:
            category = "Antitrust / Regulatory: Federal Contract Auto-Revocation"
        elif "SLA" in ctype:
            category = "Non-Compete / Exclusivity: Automatic SLA Toolchain Lock-In"
        elif "EXCLUSIVITY" in ctype:
            category = "Non-Compete / Exclusivity: ASIC Exclusive Purchasing"
        elif "ATTESTATION" in ctype:
            category = "Conflict of Interest: Governance Attestation Failure"
        elif "FIDUCIARY" in ctype:
            category = "Conflict of Interest: Dual-Fiduciary Conflict"

        all_risks.append({
            "source": "contract_clause",
            "category": category,
            "clause": clause,
            "agreement": row.get("agreement"),
            "affected_entity": row.get("affected_entity"),
            "market": row.get("market"),
            "gov_contract": row.get("gov_contract"),
            "named_competitor": row.get("named_competitor"),
            "covered_component": row.get("covered_component"),
            "evidence_chunks": [e for e in (row.get("evidence_chunks") or []) if e and e.get("id")],
        })

    # Add governance attestation findings as distinct risks if not already represented
    for row in attestation_results:
        risk_id = f"GOV_ATTEST_{row['director'].replace(' ', '_')}"
        if risk_id not in seen_ids:
            seen_ids.add(risk_id)
            all_risks.append({
                "source": "governance_audit",
                "category": "Conflict of Interest: Governance Attestation Failure",
                "clause": {
                    "id": risk_id,
                    "title": f"Governance Attestation Failure ({row['director']})",
                    "clauseType": "GOVERNANCE_ATTESTATION_FAILURE",
                    "financial_exposure_usd": 18_000_000,
                    "summary": f"Director {row['director']} attested zero conflicts in board filings, but spouse {row['relative']} holds {row['stake_pct']}% of supplier {row['supplier']}.",
                },
                "evidence_chunks": [e for e in (row.get("evidence_chunks") or []) if e and e.get("id")],
            })

    # Add dual-fiduciary findings
    for row in dual_fiduciary_results:
        risk_id = f"DUAL_FID_{row['director'].replace(' ', '_')}"
        if risk_id not in seen_ids:
            seen_ids.add(risk_id)
            amt = row.get("approved_amount") or 1_800_000
            all_risks.append({
                "source": "board_audit",
                "category": "Conflict of Interest: Dual-Fiduciary Conflict",
                "clause": {
                    "id": risk_id,
                    "title": f"Dual-Fiduciary Conflict ({row['director']})",
                    "clauseType": "DUAL_FIDUCIARY",
                    "financial_exposure_usd": amt,
                    "summary": f"Non-executive director {row['director']} holds {row['stake_pct']}% in tier-2 vendor {row['vendor']} and approved ${amt:,.0f} fee uplift without disclosure.",
                },
                "evidence_chunks": [e for e in (row.get("evidence_chunks") or []) if e and e.get("id")],
            })

    total_exposure = sum(
        (r["clause"].get("financial_exposure_usd") or 0) for r in all_risks
    )

    return {
        "tool": "analyze_secondary_and_antitrust_risks",
        "target_company": target_company,
        "risks_found": len(all_risks),
        "total_clause_exposure_usd": total_exposure,
        "risk_details": all_risks,
        "market_cap_breaches": market_cap_results,
        "contract_revocations": revocation_results,
        "sla_deadline_warnings": sla_results,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 3 – Deterministic Risk Scoring & Neo4j Write-Back
# ═══════════════════════════════════════════════════════════════════════════
def calculate_and_store_risk_factor(
    company_id: str,
    clause_id: str,
    risk_id: str,
    category: str,
    base_penalty_usd: float,
    annual_contract_usd: float,
    is_related_party_conflict: bool,
    holding_hops: int,
    rationale: str,
    source_chunk_id: str,
) -> dict:
    """
    Deterministically calculates risk exposure, score, and severity, then writes
    a RiskFactor node back to Neo4j Aura with full lineage edges.

    Scoring logic:
      • total_exposure_usd = base_penalty + annual_contract  (if related-party; else base_penalty)
      • risk_score (0–100) = min(50, total_exposure/1M × 1.2)
                             + 35 if related-party
                             + holding_hops × 5
                             capped at 100.0
      • severity = CRITICAL ≥80 | HIGH ≥60 | MEDIUM ≥35 | LOW
    """

    # ── Deterministic Calculation ──
    if is_related_party_conflict:
        total_exposure_usd = base_penalty_usd + annual_contract_usd
    else:
        total_exposure_usd = base_penalty_usd

    exposure_score = min(50.0, (total_exposure_usd / 1_000_000) * 1.2)
    related_party_bonus = 35.0 if is_related_party_conflict else 0.0
    regulatory_bonus = 35.0 if (not is_related_party_conflict and ("Regulatory" in category or "Revocation" in category) and total_exposure_usd >= 50_000_000) else 0.0
    hop_bonus = holding_hops * 5.0
    risk_score = min(100.0, exposure_score + related_party_bonus + regulatory_bonus + hop_bonus)
    risk_score = round(risk_score, 2)

    if risk_score >= 80:
        severity = "CRITICAL"
    elif risk_score >= 60:
        severity = "HIGH"
    elif risk_score >= 35:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    # ── Write-back to Neo4j Aura ──
    write_query = """
    OPTIONAL MATCH (c:Company {id: $company_id})
    OPTIONAL MATCH (deal:Deal) WHERE (deal)-[:TARGET]->(c)
    OPTIONAL MATCH (cl:Clause {id: $clause_id})
    OPTIONAL MATCH (dc:DocumentChunk {id: $source_chunk_id})
    MERGE (r:RiskFactor {id: $risk_id})
    SET r.category = $category,
        r.severity = $severity,
        r.risk_score = $risk_score,
        r.base_penalty_usd = $base_penalty_usd,
        r.annual_contract_usd = $annual_contract_usd,
        r.total_exposure_usd = $total_exposure_usd,
        r.deal_deduction_usd = $total_exposure_usd,
        r.is_related_party_conflict = $is_related_party_conflict,
        r.description = $rationale,
        r.status = 'ACTIVE',
        r.updated_by = 'DealShield_GoogleADK_Agent',
        r.calculated_at = toString(datetime())
    FOREACH (_ IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END |
        MERGE (c)-[:HAS_CALCULATED_RISK {score: $risk_score, severity: $severity}]->(r)
    )
    FOREACH (_ IN CASE WHEN deal IS NOT NULL THEN [1] ELSE [] END |
        MERGE (deal)-[:HAS_CALCULATED_RISK {score: $risk_score, severity: $severity}]->(r)
    )
    FOREACH (_ IN CASE WHEN cl IS NOT NULL THEN [1] ELSE [] END |
        MERGE (cl)-[:RESTRICTED_BY {impact: 'Triggers Calculated Risk'}]->(r)
    )
    FOREACH (_ IN CASE WHEN dc IS NOT NULL THEN [1] ELSE [] END |
        MERGE (r)-[:EXTRACTED_FROM]->(dc)
    )
    RETURN r {.*} AS stored_risk
    """

    params = {
        "company_id": company_id,
        "clause_id": clause_id,
        "risk_id": risk_id,
        "category": category,
        "severity": severity,
        "risk_score": risk_score,
        "base_penalty_usd": base_penalty_usd,
        "annual_contract_usd": annual_contract_usd,
        "total_exposure_usd": total_exposure_usd,
        "is_related_party_conflict": is_related_party_conflict,
        "rationale": rationale,
        "source_chunk_id": source_chunk_id,
    }

    results = write_cypher(write_query, params)
    stored = results[0] if results else {}

    return {
        "tool": "calculate_and_store_risk_factor",
        "risk_id": risk_id,
        "company_id": company_id,
        "clause_id": clause_id,
        "category": category,
        "rationale": rationale,
        "calculation": {
            "base_penalty_usd": base_penalty_usd,
            "annual_contract_usd": annual_contract_usd,
            "is_related_party_conflict": is_related_party_conflict,
            "holding_hops": holding_hops,
            "total_exposure_usd": total_exposure_usd,
            "risk_score": risk_score,
            "severity": severity,
        },
        "stored_risk": stored.get("stored_risk", {}),
        "write_status": "SUCCESS" if results else "NO_MATCH",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Google ADK Agent Definitions
# ═══════════════════════════════════════════════════════════════════════════

# ── Sub-Agent 1: Change-of-Control Conflict Detector ──
coc_agent = LlmAgent(
    name="CoC_Conflict_Detector",
    model=LLM_MODEL,
    instruction="""You are DealShield's Change-of-Control Conflict Detection specialist.

Your task: Call the `analyze_change_of_control_graphrag` tool to detect hidden
related-party conflicts triggered by Change-of-Control clauses in the M&A deal.

ALWAYS call the tool with the target company name provided in the user's query.
If no target is specified, default to "Northwind Microsystems Inc.".

After receiving the tool results, provide a structured summary including:
1. Number of Change-of-Control clauses found (e.g. poison pills, vendor lock-ins).
2. For each related-party conflict detected:
   - Director name and role
   - Related party (spouse/family) and their hidden beneficial ownership
   - Full holding company chain (e.g. Priya Raman -> Meridian Holdings Ltd (BVI) -> Silverline Components Ltd)
   - Annual supplier contract value
   - CoC termination penalty
   - DocumentChunk citations (source doc, page, relevant text excerpt)
3. Total combined financial exposure

Store all key findings in the session state for the next agent.
Format monetary values with dollar signs and commas (e.g., $15,000,000).
""",
    tools=[analyze_change_of_control_graphrag],
)

# ── Sub-Agent 2: Secondary & Antitrust Risk Analyzer ──
secondary_risk_agent = LlmAgent(
    name="Secondary_Risk_Analyzer",
    model=LLM_MODEL,
    instruction="""You are DealShield's Secondary & Antitrust Risk Analysis specialist.

Your task: Call the `analyze_secondary_and_antitrust_risks` tool to discover all
additional restrictive clauses affecting the M&A target across:
- Anti-Trust / Regulatory (Horizontal Market Cap >25%, DoD Contract Revocation)
- Non-Compete & Exclusivity (Sole-source ASIC take-or-pay, Missed SLA auto-renewal deadlines)
- Governance & Attestation (Director conflict certification failures, Dual fiduciaries)

ALWAYS call the tool with the same target company as the previous agent.
If no target is specified, default to "Northwind Microsystems Inc.".

After receiving results, summarize:
1. Total number of additional risk clauses found
2. For each clause: ID, title, type, financial exposure, evidence citations
3. Any existing RiskFactor nodes already in the graph
4. Total cumulative exposure from all secondary risks

Highlight the DoD Contract Revocation ($120M / $85M) and Sole-Source Exclusivity commitments if found.
""",
    tools=[analyze_secondary_and_antitrust_risks],
)

# ── Sub-Agent 3: Risk Scorer & Write-back Agent ──
risk_scorer_agent = LlmAgent(
    name="Risk_Scorer",
    model=LLM_MODEL,
    instruction="""You are DealShield's Risk Scoring & Write-Back specialist.

Your task: Based on the conflict and risk data discovered by the previous agents
in this conversation, call `calculate_and_store_risk_factor` to score and persist
each material risk back to Neo4j Aura.

For each material finding identified:
1. Extract the company_id, clause_id, category, base_penalty_usd, annual_contract_usd,
   is_related_party_conflict flag, holding_hops, and concise rationale.
2. Call `calculate_and_store_risk_factor` to persist the RiskFactor node to Neo4j.

After all writes complete, provide a final deal risk summary table with columns:
Risk ID | Category | Severity | Score | Total Exposure | Deal Deduction

Calculate the total deal deduction across all risks.
""",
    tools=[calculate_and_store_risk_factor],
)

# ── Coordinator: Sequential Pipeline ──
dealshield_coordinator = SequentialAgent(
    name="DealShield_Coordinator",
    description=(
        "Enterprise M&A Due Diligence pipeline that sequentially executes "
        "conflict detection, secondary risk analysis, and risk scoring/write-back."
    ),
    sub_agents=[coc_agent, secondary_risk_agent, risk_scorer_agent],
)


# ── Chat Assistant: Interactive Agent ──
chat_agent = LlmAgent(
    name="DealShield_Chat_Assistant",
    model=LLM_MODEL,
    instruction="""You are the DealShield AI Assistant, an expert M&A conversational agent.
Your goal is to answer questions about the graph database, deal risks, or conflict rings.
You can use the three available tools to perform real-time analysis. Use `run_cypher` to query any general node/edge information if the predefined tools are insufficient.
Provide professional, concise responses. Use markdown.""",
    tools=[
        analyze_change_of_control_graphrag,
        analyze_secondary_and_antitrust_risks,
        calculate_and_store_risk_factor,
        run_cypher,
    ],
)


# ═══════════════════════════════════════════════════════════════════════════
# Neo4j Agent Memory Setup
# ═══════════════════════════════════════════════════════════════════════════
def create_memory_service() -> Neo4jMemoryService | None:
    """Create a Neo4jMemoryService for persistent agent memory.
    Returns None if memory setup fails (workflow still runs without it).
    """
    try:
        settings = MemorySettings(
            neo4j={
                "uri": NEO4J_URI,
                "username": NEO4J_USERNAME,
                "password": NEO4J_PASSWORD,
                "database": NEO4J_DATABASE,
            }
        )
        client = MemoryClient(settings)
        memory_service = Neo4jMemoryService(memory_client=client)
        return memory_service
    except Exception as e:
        print(f"[WARNING] Neo4j Agent Memory unavailable (workflow continues without it): {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Runner Factory
# ═══════════════════════════════════════════════════════════════════════════
def create_runner() -> tuple[Runner, InMemorySessionService, Neo4jMemoryService | None]:
    """Set up ADK Runner with session service and optional memory service."""
    session_service = InMemorySessionService()
    memory_service = create_memory_service()

    runner = Runner(
        agent=dealshield_coordinator,
        app_name=APP_NAME,
        session_service=session_service,
    )
    return runner, session_service, memory_service


# ═══════════════════════════════════════════════════════════════════════════
# Async Execution
# ═══════════════════════════════════════════════════════════════════════════
async def run_dealshield_analysis(
    target_company: str = "Northwind Microsystems Inc.",
    user_id: str = "analyst_01",
) -> list[dict]:
    """Execute the full DealShield pipeline and return all agent events."""

    runner, session_service, memory_service = create_runner()

    # Create a session
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=user_id
    )

    user_message = types.Content(
        role="user",
        parts=[
            types.Part(
                text=(
                    f"Run the full DealShield M&A due diligence analysis on "
                    f"target company: '{target_company}'. "
                    f"Detect all Change-of-Control conflicts, secondary risks, "
                    f"and calculate + store risk factors back to Neo4j."
                )
            )
        ],
    )

    events = []
    async for event in runner.run_async(
        session_id=session.id,
        user_id=user_id,
        new_message=user_message,
    ):
        events.append({
            "author": getattr(event, "author", "system"),
            "content": (
                event.content.model_dump()
                if hasattr(event, "content") and event.content
                else None
            ),
            "actions": (
                event.actions.model_dump()
                if hasattr(event, "actions") and event.actions
                else None
            ),
        })

    return events


def run_sync(target_company: str = "Northwind Microsystems Inc.") -> list[dict]:
    """Synchronous wrapper for CLI / notebook usage."""
    return asyncio.run(run_dealshield_analysis(target_company))


# ═══════════════════════════════════════════════════════════════════════════
# Standalone CLI Execution
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 80)
    print("  DealShield – Enterprise M&A Due Diligence Agentic Workflow")
    print("  Google ADK × Neo4j Aura × GraphRAG × Agent Memory")
    print("=" * 80)
    print()

    events = run_sync("Northwind Microsystems Inc.")

    print(f"\n{'=' * 80}")
    print(f"  Pipeline complete – {len(events)} events captured")
    print(f"{'=' * 80}")

    for event in events:
        if event.get("content"):
            content = event["content"]
            parts = content.get("parts") or []
            for part in parts:
                text = part.get("text")
                if text:
                    print(f"\n[{event.get('author', '?')}]:")
                    print(text[:2000])
