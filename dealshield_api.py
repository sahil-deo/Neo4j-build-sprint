"""
DealShield – FastAPI Backend
=============================
REST API layer exposing the 3 DealShield tools + graph explorer.
Serves the React frontend and provides CORS-enabled JSON endpoints.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

# Import the workflow tools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dealshield_adk_workflow import (
    analyze_change_of_control_graphrag,
    analyze_secondary_and_antitrust_risks,
    calculate_and_store_risk_factor,
    run_cypher,
)

# ─── App Setup ────────────────────────────────────────────────────────────
app = FastAPI(
    title="DealShield API",
    description="Enterprise M&A Due Diligence & Conflict-of-Interest API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request/Response Models ─────────────────────────────────────────────
class TargetRequest(BaseModel):
    target_company: str = "TargetTech Inc."


class CypherRequest(BaseModel):
    query: str


class RiskScoreRequest(BaseModel):
    company_id: str
    clause_id: str
    risk_id: str
    category: str
    base_penalty_usd: float
    annual_contract_usd: float
    is_related_party_conflict: bool
    holding_hops: int
    rationale: str
    source_chunk_id: str


# ─── Health & Stats ──────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    try:
        stats = run_cypher("RETURN 1 AS ok")
        return {"status": "healthy", "neo4j": "connected", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        return {"status": "degraded", "neo4j": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/graph/stats")
def graph_stats():
    """Get graph statistics."""
    try:
        result = run_cypher("""
            MATCH (c:Company) WITH count(c) AS companies
            MATCH (e:Executive) WITH companies, count(e) AS executives
            MATCH (cl:Clause) WITH companies, executives, count(cl) AS clauses
            MATCH (dc:DocumentChunk) WITH companies, executives, clauses, count(dc) AS doc_chunks
            MATCH (rf:RiskFactor) WITH companies, executives, clauses, doc_chunks, count(rf) AS risk_factors
            MATCH (s:Subsidiary) WITH companies, executives, clauses, doc_chunks, risk_factors, count(s) AS subsidiaries
            RETURN companies, executives, clauses, doc_chunks, risk_factors, subsidiaries
        """)
        return result[0] if result else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Tool 1: Change-of-Control Analysis ─────────────────────────────────
@app.post("/api/analyze/coc")
def analyze_coc(req: TargetRequest):
    """Run Change-of-Control conflict detection."""
    try:
        return analyze_change_of_control_graphrag(req.target_company)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Tool 2: Secondary & Antitrust Risks ────────────────────────────────
@app.post("/api/analyze/secondary")
def analyze_secondary(req: TargetRequest):
    """Run secondary and antitrust risk analysis."""
    try:
        return analyze_secondary_and_antitrust_risks(req.target_company)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Tool 3: Risk Scoring & Write-back ──────────────────────────────────
@app.post("/api/analyze/score")
def score_risk(req: RiskScoreRequest):
    """Score and store a single risk factor."""
    try:
        return calculate_and_store_risk_factor(
            company_id=req.company_id,
            clause_id=req.clause_id,
            risk_id=req.risk_id,
            category=req.category,
            base_penalty_usd=req.base_penalty_usd,
            annual_contract_usd=req.annual_contract_usd,
            is_related_party_conflict=req.is_related_party_conflict,
            holding_hops=req.holding_hops,
            rationale=req.rationale,
            source_chunk_id=req.source_chunk_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Full Pipeline ───────────────────────────────────────────────────────
@app.post("/api/analyze/full")
def run_full_pipeline(req: TargetRequest):
    """Run the complete 3-stage DealShield pipeline."""
    try:
        # Stage 1
        coc_result = analyze_change_of_control_graphrag(req.target_company)

        # Stage 2
        secondary_result = analyze_secondary_and_antitrust_risks(req.target_company)

        # Stage 3: Score the 3 key risks
        risks_to_score = [
            {
                "company_id": "COMP-002",
                "clause_id": "CL-402",
                "risk_id": "RISK-CALC-001",
                "category": "Undisclosed Related-Party + Change-of-Control",
                "base_penalty_usd": 15_000_000,
                "annual_contract_usd": 18_500_000,
                "is_related_party_conflict": True,
                "holding_hops": 2,
                "rationale": (
                    "Director Marcus Vance's spouse Elena Rostova-Vance holds 42% "
                    "of Vanguard Pacific Holdings, which owns 65% of sole-source "
                    "supplier Apex MicroSystems LLC. The $18.5M annual supply contract "
                    "combined with the $15M CoC poison-pill penalty creates $33.5M "
                    "total exposure."
                ),
                "source_chunk_id": "DOC-CHUNK-101",
            },
            {
                "company_id": "COMP-002",
                "clause_id": "CL-819",
                "risk_id": "RISK-CALC-002",
                "category": "Anti-Trust / Regulatory – DoD Contract Revocation",
                "base_penalty_usd": 45_000_000,
                "annual_contract_usd": 0,
                "is_related_party_conflict": False,
                "holding_hops": 0,
                "rationale": (
                    "Acquirer Horizon Private Equity's existing defense portfolio "
                    "creates >25% market share overlap, triggering immediate revocation "
                    "of TargetTech's $45M DoD contract per Clause 9.4."
                ),
                "source_chunk_id": "DOC-CHUNK-103",
            },
            {
                "company_id": "COMP-002",
                "clause_id": "CL-205",
                "risk_id": "RISK-CALC-003",
                "category": "Governance / Fraud – Director Attestation Failure",
                "base_penalty_usd": 18_500_000,
                "annual_contract_usd": 0,
                "is_related_party_conflict": True,
                "holding_hops": 2,
                "rationale": (
                    "Marcus Vance failed to disclose spousal beneficial ownership "
                    "in sole-source vendor Apex MicroSystems via Vanguard Pacific "
                    "Holdings in annual director conflict attestation."
                ),
                "source_chunk_id": "DOC-CHUNK-102",
            },
        ]

        scored_risks = []
        for risk in risks_to_score:
            result = calculate_and_store_risk_factor(**risk)
            scored_risks.append(result)

        total_exposure = sum(r["calculation"]["total_exposure_usd"] for r in scored_risks)

        return {
            "status": "complete",
            "target_company": req.target_company,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stages": {
                "coc_analysis": coc_result,
                "secondary_risks": secondary_result,
                "scored_risks": scored_risks,
            },
            "summary": {
                "total_conflicts": coc_result.get("total_conflicts_detected", 0),
                "total_secondary_risks": secondary_result.get("risks_found", 0),
                "total_risks_scored": len(scored_risks),
                "total_deal_deduction_usd": total_exposure,
                "critical_count": sum(1 for r in scored_risks if r["calculation"]["severity"] == "CRITICAL"),
                "high_count": sum(1 for r in scored_risks if r["calculation"]["severity"] == "HIGH"),
                "medium_count": sum(1 for r in scored_risks if r["calculation"]["severity"] == "MEDIUM"),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Graph Explorer ──────────────────────────────────────────────────────
@app.post("/api/graph/query")
def execute_cypher(req: CypherRequest):
    """Execute a read-only Cypher query."""
    query = req.query.strip()
    # Basic safety: block destructive operations
    blocked = ["DELETE", "DETACH", "DROP", "CREATE", "SET ", "REMOVE", "MERGE"]
    upper = query.upper()
    for kw in blocked:
        if kw in upper and "RETURN" not in upper[:upper.find(kw)]:
            # Allow MERGE/SET etc. only if they appear after RETURN (unlikely in reads)
            raise HTTPException(status_code=400, detail=f"Write operations not allowed via explorer. Blocked: {kw}")
    try:
        results = run_cypher(query)
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Preset Queries ──────────────────────────────────────────────────────
@app.get("/api/graph/presets")
def get_presets():
    """Return preset Cypher queries."""
    return {
        "presets": [
            {
                "id": "focal_deal",
                "label": "🎯 Focal Deal Structure",
                "query": (
                    "MATCH (acquirer:Company {id:'COMP-001'})-[r:HOLDS_STAKE_IN]->"
                    "(target:Company {id:'COMP-002'}) "
                    "RETURN acquirer.name AS Acquirer, r.status AS Deal_Status, "
                    "target.name AS Target, target.valuation_usd AS Valuation"
                ),
            },
            {
                "id": "conflict_chain",
                "label": "🕵️ Marcus Vance Conflict Chain",
                "query": (
                    "MATCH (d:Executive {id:'EXEC-001'})-[:DIRECTOR_OF]->"
                    "(spouse:Executive {id:'EXEC-002'})-[:HOLDS_STAKE_IN]->"
                    "(holding:Company)-[:HOLDS_STAKE_IN]->(supplier:Company)-"
                    "[:SUPPLIES_TO]->(t:Company {id:'COMP-002'}) "
                    "RETURN d.name AS Director, spouse.name AS Spouse, "
                    "holding.name AS Holding_Co, supplier.name AS Supplier, "
                    "[(supplier)-[s:SUPPLIES_TO]->(t)|s.annual_value_usd][0] AS Annual_Value"
                ),
            },
            {
                "id": "coc_clauses",
                "label": "📋 All CoC Clauses + Evidence",
                "query": (
                    "MATCH (t:Company {name:'TargetTech Inc.'})-[:RESTRICTED_BY]->"
                    "(cl:Clause {clause_type:'Change of Control'})-[:EXTRACTED_FROM]->"
                    "(dc:DocumentChunk) "
                    "RETURN cl.id AS Clause, cl.title AS Title, "
                    "cl.financial_exposure_usd AS Exposure, "
                    "dc.source_doc AS Document, dc.page AS Page"
                ),
            },
            {
                "id": "stored_risks",
                "label": "⚡ Stored Risk Factors",
                "query": (
                    "MATCH (c:Company)-[:HAS_CALCULATED_RISK]->(r:RiskFactor) "
                    "WHERE r.updated_by = 'DealShield_GoogleADK_Agent' "
                    "RETURN r.id AS Risk_ID, r.category AS Category, r.severity AS Severity, "
                    "r.risk_score AS Score, r.total_exposure_usd AS Exposure, "
                    "r.deal_deduction_usd AS Deal_Deduction, r.calculated_at AS Calculated"
                ),
            },
            {
                "id": "all_conflicts",
                "label": "🔗 All Related-Party Conflicts",
                "query": (
                    "MATCH (d:Executive)-[:DIRECTOR_OF]->(t:Company {name:'TargetTech Inc.'})"
                    "<-[s:SUPPLIES_TO]-(sup:Company)<-[:HOLDS_STAKE_IN*1..2]-(rel:Executive)"
                    "<-[:DIRECTOR_OF]-(d) "
                    "RETURN d.name AS Director, rel.name AS Related_Party, "
                    "sup.name AS Supplier, s.annual_value_usd AS Annual_Value"
                ),
            },
        ]
    }


# ─── Serve React build (production) ─────────────────────────────────────
# ─── Serve Static UI (Vanilla JS) ─────────────────────────────────────────
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
