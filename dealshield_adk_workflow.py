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
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", ""))
LLM_MODEL = "gemini-2.5-flash"
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
    target_company: str = "TargetTech Inc.",
) -> dict:
    """
    Multi-hop Cypher query that:
    1. Finds all Change-of-Control clauses restricting the target company.
    2. Traverses 1–4 hops to detect undisclosed related-party supplier conflicts.
    3. Returns structured JSON with director, spouse, shell/holding chain,
       annual supplier value, CoC termination penalty, and DocumentChunk citations.
    """

    # ── Step 1: Change-of-Control clauses + DocumentChunk evidence ──
    coc_query = """
    MATCH (t:Company {name: $target})-[:RESTRICTED_BY]->(cl:Clause)
    WHERE cl.clause_type = 'Change of Control'
    OPTIONAL MATCH (cl)-[:EXTRACTED_FROM]->(dc:DocumentChunk)
    RETURN cl {.id, .title, .clause_type, .financial_exposure_usd, .summary} AS clause,
           collect(DISTINCT dc {.id, .source_doc, .page, .text}) AS doc_chunks
    """
    coc_results = run_cypher(coc_query, {"target": target_company})

    # ── Step 2: Multi-hop related-party conflict rings ──
    # Director -> Target <- Supplier <- Holding(1..2 hops) <- Related Party <- Director (spouse link)
    conflict_query = """
    MATCH (d:Executive)-[:DIRECTOR_OF]->(t:Company {name: $target})
          <-[sup_rel:SUPPLIES_TO]-(sup:Company)
          <-[:HOLDS_STAKE_IN*1..2]-(rel_party)
          <-[:DIRECTOR_OF]-(d)
    WHERE rel_party:Executive OR rel_party:Company
    // Collect the full holding chain between rel_party and sup
    OPTIONAL MATCH chain = (rel_party)-[:HOLDS_STAKE_IN*1..2]->(sup)
    WITH d, t, sup, sup_rel, rel_party,
         [node IN nodes(chain) WHERE node <> rel_party AND node <> sup | node {.id, .name, labels: labels(node)}] AS intermediaries,
         [rel IN relationships(chain) | rel {.percentage, .status}] AS stake_details
    // Get the spouse/related-party link details
    OPTIONAL MATCH (d)-[spouse_link:DIRECTOR_OF]->(rel_party)
    WHERE spouse_link.role CONTAINS 'Spouse' OR spouse_link.role CONTAINS 'Related Party'
        OR spouse_link.role CONTAINS 'Family'
    // Get CoC clauses for quantification
    OPTIONAL MATCH (t)-[:RESTRICTED_BY]->(coc_clause:Clause {clause_type: 'Change of Control'})
    OPTIONAL MATCH (coc_clause)-[:EXTRACTED_FROM]->(coc_doc:DocumentChunk)
    RETURN
        d {.id, .name, .title} AS director,
        rel_party {.id, .name, .title, labels: labels(rel_party)} AS related_party,
        spouse_link.role AS relationship_type,
        sup {.id, .name, .role} AS supplier,
        sup_rel {.annual_value_usd, .criticality} AS supplier_contract,
        intermediaries,
        stake_details,
        collect(DISTINCT coc_clause {.id, .title, .financial_exposure_usd, .summary}) AS coc_clauses,
        collect(DISTINCT coc_doc {.id, .source_doc, .page, .text}) AS coc_evidence
    """
    conflict_results = run_cypher(conflict_query, {"target": target_company})

    # ── Step 3: Build the full holding-company chain for each conflict ──
    conflicts = []
    for row in conflict_results:
        # Reconstruct the ownership chain
        holding_chain = []
        related = row.get("related_party", {})
        intermediaries = row.get("intermediaries") or []
        stake_details = row.get("stake_details") or []

        # Start: related party
        holding_chain.append({
            "entity": related.get("name", "Unknown"),
            "id": related.get("id", ""),
            "role": "Beneficial Owner (Related Party)",
        })

        # Intermediate holding companies
        for i, inter in enumerate(intermediaries):
            pct = stake_details[i].get("percentage", "?") if i < len(stake_details) else "?"
            holding_chain.append({
                "entity": inter.get("name", "Unknown"),
                "id": inter.get("id", ""),
                "stake_percentage": pct,
            })

        # End: supplier
        supplier = row.get("supplier", {})
        holding_chain.append({
            "entity": supplier.get("name", "Unknown"),
            "id": supplier.get("id", ""),
            "role": "Direct Supplier to Target",
        })

        coc_penalties = row.get("coc_clauses") or []
        total_coc_penalty = sum(
            c.get("financial_exposure_usd", 0) for c in coc_penalties
        )

        conflicts.append({
            "director": row.get("director", {}),
            "related_party": related,
            "relationship_type": row.get("relationship_type", "Undisclosed"),
            "holding_chain": holding_chain,
            "holding_hops": len(intermediaries) + 2,  # related_party -> (intermediaries) -> supplier
            "supplier_contract": row.get("supplier_contract", {}),
            "annual_supplier_value_usd": (row.get("supplier_contract") or {}).get(
                "annual_value_usd", 0
            ),
            "coc_termination_penalty_usd": total_coc_penalty,
            "coc_clauses": coc_penalties,
            "document_citations": row.get("coc_evidence") or [],
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
    target_company: str = "TargetTech Inc.",
) -> dict:
    """
    Retrieves all restrictive clauses (Anti-Trust, Governance/Fraud, Exclusivity,
    Liquidated Damages) connected to the target company or its subsidiaries,
    plus existing RiskFactor nodes and DocumentChunk evidence.
    Also picks up key clauses like CL-819 and CL-205 that reference the target
    by content even if not graph-linked.
    """

    # ── Part A: Clauses directly linked to target or its subsidiaries ──
    linked_query = """
    MATCH (t:Company {name: $target})
    OPTIONAL MATCH (t)-[:OWNS_SUBSIDIARY]->(sub:Subsidiary)
    WITH t, collect(sub) AS subs

    // Clauses on the company itself
    OPTIONAL MATCH (t)-[:RESTRICTED_BY]->(cl:Clause)
    WHERE cl.clause_type IN [
        'Anti-Trust / Regulatory', 'Governance / Fraud',
        'Exclusivity & Non-Compete', 'Liquidated Damages'
    ]
    WITH t, subs, collect(DISTINCT cl) AS company_clauses

    // Clauses on subsidiaries (if Subsidiary nodes can have RESTRICTED_BY)
    UNWIND (CASE WHEN size(subs) > 0 THEN subs ELSE [null] END) AS sub
    OPTIONAL MATCH (sub)-[:RESTRICTED_BY]->(scl:Clause)
    WHERE scl IS NOT NULL AND scl.clause_type IN [
        'Anti-Trust / Regulatory', 'Governance / Fraud',
        'Exclusivity & Non-Compete', 'Liquidated Damages'
    ]
    WITH t, company_clauses, collect(DISTINCT scl) AS sub_clauses

    WITH t, company_clauses + sub_clauses AS all_clauses
    UNWIND (CASE WHEN size(all_clauses) > 0 THEN all_clauses ELSE [null] END) AS cl
    OPTIONAL MATCH (cl)-[:EXTRACTED_FROM]->(dc:DocumentChunk) WHERE cl IS NOT NULL
    OPTIONAL MATCH (cl)-[:RESTRICTED_BY]->(rf:RiskFactor) WHERE cl IS NOT NULL
    RETURN
        cl {.id, .title, .clause_type, .financial_exposure_usd, .summary} AS clause,
        collect(DISTINCT dc {.id, .source_doc, .page, .text}) AS evidence_chunks,
        collect(DISTINCT rf {.id, .category, .severity, .description}) AS risk_factors
    """
    linked_results = run_cypher(linked_query, {"target": target_company})

    # ── Part B: Key named clauses that may not be graph-linked ──
    named_query = """
    MATCH (cl:Clause)
    WHERE cl.id IN ['CL-819', 'CL-205']
    OPTIONAL MATCH (cl)-[:EXTRACTED_FROM]->(dc:DocumentChunk)
    OPTIONAL MATCH (cl)-[:RESTRICTED_BY]->(rf:RiskFactor)
    OPTIONAL MATCH (rf)-[:EXTRACTED_FROM]->(rdc:DocumentChunk)
    RETURN
        cl {.id, .title, .clause_type, .financial_exposure_usd, .summary} AS clause,
        collect(DISTINCT dc {.id, .source_doc, .page, .text}) AS evidence_chunks,
        collect(DISTINCT rf {.id, .category, .severity, .description}) AS risk_factors,
        collect(DISTINCT rdc {.id, .source_doc, .page, .text}) AS risk_evidence
    """
    named_results = run_cypher(named_query, {"target": target_company})

    # ── Part C: Supplier-linked clauses affecting the target supply chain ──
    supplier_clause_query = """
    MATCH (sup:Company)-[:SUPPLIES_TO]->(t:Company {name: $target})
    MATCH (sup)-[:RESTRICTED_BY]->(cl:Clause)
    WHERE cl.clause_type IN [
        'Anti-Trust / Regulatory', 'Governance / Fraud',
        'Exclusivity & Non-Compete', 'Liquidated Damages',
        'Change of Control'
    ]
    OPTIONAL MATCH (cl)-[:EXTRACTED_FROM]->(dc:DocumentChunk)
    OPTIONAL MATCH (cl)-[:RESTRICTED_BY]->(rf:RiskFactor)
    RETURN
        sup {.id, .name} AS supplier,
        cl {.id, .title, .clause_type, .financial_exposure_usd, .summary} AS clause,
        collect(DISTINCT dc {.id, .source_doc, .page, .text}) AS evidence_chunks,
        collect(DISTINCT rf {.id, .category, .severity, .description}) AS risk_factors
    """
    supplier_results = run_cypher(supplier_clause_query, {"target": target_company})

    # ── Merge and deduplicate ──
    seen_clause_ids = set()
    all_risks = []

    for source_label, results in [
        ("direct_company_or_subsidiary", linked_results),
        ("named_key_clause", named_results),
        ("supplier_chain", supplier_results),
    ]:
        for row in results:
            clause = row.get("clause") or {}
            if clause is None or clause.get("id") is None:
                continue
            cid = clause["id"]
            if cid in seen_clause_ids:
                continue
            seen_clause_ids.add(cid)

            evidence = row.get("evidence_chunks") or []
            # Also include risk_evidence if present (from named clauses)
            risk_evidence = row.get("risk_evidence") or []
            combined_evidence = evidence + [
                e for e in risk_evidence if e not in evidence
            ]
            # Remove null entries
            combined_evidence = [e for e in combined_evidence if e and e.get("id")]

            all_risks.append({
                "source": source_label,
                "supplier": row.get("supplier"),
                "clause": clause,
                "evidence_chunks": combined_evidence,
                "existing_risk_factors": [
                    rf for rf in (row.get("risk_factors") or []) if rf and rf.get("id")
                ],
            })

    # Total financial exposure
    total_exposure = sum(
        (r["clause"].get("financial_exposure_usd") or 0) for r in all_risks
    )

    return {
        "tool": "analyze_secondary_and_antitrust_risks",
        "target_company": target_company,
        "risks_found": len(all_risks),
        "total_clause_exposure_usd": total_exposure,
        "risk_details": all_risks,
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
    hop_bonus = holding_hops * 5.0
    risk_score = min(100.0, exposure_score + related_party_bonus + hop_bonus)
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
    MATCH (c:Company {id: $company_id})
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
    MERGE (c)-[:HAS_CALCULATED_RISK {score: $risk_score, severity: $severity}]->(r)
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
If no target is specified, default to "TargetTech Inc.".

After receiving the tool results, provide a structured summary including:
1. Number of Change-of-Control clauses found
2. For each related-party conflict detected:
   - Director name and role
   - Related party (spouse/family) and their hidden beneficial ownership
   - Full holding company chain (e.g. Elena Rostova-Vance → Vanguard Pacific Holdings → Apex MicroSystems LLC)
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
additional restrictive clauses affecting the M&A target, beyond Change-of-Control.

Focus on these clause categories:
- Anti-Trust / Regulatory (e.g., DoD contract revocation risks)
- Governance / Fraud (e.g., undisclosed attestation breaches)
- Exclusivity & Non-Compete
- Liquidated Damages

ALWAYS call the tool with the same target company as the previous agent.
If no target is specified, default to "TargetTech Inc.".

After receiving results, summarize:
1. Total number of additional risk clauses found
2. For each clause: ID, title, type, financial exposure, evidence citations
3. Any existing RiskFactor nodes already in the graph
4. Total cumulative exposure from all secondary risks

Highlight the DoD Anti-Trust Restriction (CL-819, $45M) and Board Attestation
Breach (CL-205, $18.5M) if found.
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

You MUST calculate and store these specific risk factors:

**Risk 1 – CoC Related-Party Conflict (RISK-CALC-001)**:
- company_id: "COMP-002"
- clause_id: "CL-402"
- risk_id: "RISK-CALC-001"
- category: "Undisclosed Related-Party + Change-of-Control"
- base_penalty_usd: 15000000 (the $15M CoC termination penalty)
- annual_contract_usd: 18500000 (the $18.5M annual supplier value)
- is_related_party_conflict: true
- holding_hops: 2 (Elena → Vanguard Pacific → Apex MicroSystems)
- rationale: "Director Marcus Vance's spouse Elena Rostova-Vance holds 42% of Vanguard Pacific Holdings, which owns 65% of sole-source supplier Apex MicroSystems LLC. The $18.5M annual supply contract combined with the $15M CoC poison-pill penalty creates $33.5M total exposure."
- source_chunk_id: "DOC-CHUNK-101"

**Risk 2 – DoD Anti-Trust (RISK-CALC-002)**:
- company_id: "COMP-002"
- clause_id: "CL-819"
- risk_id: "RISK-CALC-002"
- category: "Anti-Trust / Regulatory – DoD Contract Revocation"
- base_penalty_usd: 45000000
- annual_contract_usd: 0
- is_related_party_conflict: false
- holding_hops: 0
- rationale: "Acquirer Horizon Private Equity's existing defense portfolio creates >25% market share overlap, triggering immediate revocation of TargetTech's $45M DoD contract per Clause 9.4."
- source_chunk_id: "DOC-CHUNK-103"

**Risk 3 – Board Attestation Breach (RISK-CALC-003)**:
- company_id: "COMP-002"
- clause_id: "CL-205"
- risk_id: "RISK-CALC-003"
- category: "Governance / Fraud – Director Attestation Failure"
- base_penalty_usd: 18500000
- annual_contract_usd: 0
- is_related_party_conflict: true
- holding_hops: 2
- rationale: "Marcus Vance failed to disclose spousal beneficial ownership in sole-source vendor Apex MicroSystems via Vanguard Pacific Holdings in annual director conflict attestation. Exposure equals the full $18.5M contract value."
- source_chunk_id: "DOC-CHUNK-102"

Call the tool THREE times – once for each risk. After all writes complete,
provide a final deal risk summary table with columns:
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
                "user": NEO4J_USERNAME,
                "password": NEO4J_PASSWORD,
                "database": NEO4J_DATABASE,
            }
        )
        client = MemoryClient(settings)
        memory_service = Neo4jMemoryService(memory_client=client)
        return memory_service
    except Exception as e:
        print(f"⚠ Neo4j Agent Memory unavailable (workflow continues without it): {e}")
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
    target_company: str = "TargetTech Inc.",
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


def run_sync(target_company: str = "TargetTech Inc.") -> list[dict]:
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

    events = run_sync("TargetTech Inc.")

    print(f"\n{'=' * 80}")
    print(f"  Pipeline complete – {len(events)} events captured")
    print(f"{'=' * 80}")

    # Print final agent outputs
    for event in events:
        if event.get("content"):
            content = event["content"]
            parts = content.get("parts") or []
            for part in parts:
                text = part.get("text")
                if text:
                    print(f"\n[{event.get('author', '?')}]:")
                    print(text[:2000])
