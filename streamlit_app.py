"""
DealShield – Streamlit Interactive Demo UI
==========================================
Premium dark-themed dashboard for the M&A Due Diligence Agentic Workflow.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Page configuration – must be the first Streamlit command
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DealShield – M&A Due Diligence AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Premium CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* Root variables */
:root {
    --bg-primary: #0a0e1a;
    --bg-secondary: #111827;
    --bg-card: #1a1f35;
    --bg-card-hover: #242b45;
    --accent-blue: #3b82f6;
    --accent-cyan: #06b6d4;
    --accent-purple: #8b5cf6;
    --accent-emerald: #10b981;
    --accent-amber: #f59e0b;
    --accent-red: #ef4444;
    --accent-rose: #f43f5e;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --border-subtle: rgba(255,255,255,0.06);
    --gradient-critical: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    --gradient-high: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    --gradient-medium: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    --gradient-hero: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
}

/* Global font */
html, body, [class*="css"], .stMarkdown, .stText {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Hide Streamlit defaults */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Main background */
.stApp {
    background: var(--bg-primary) !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%) !important;
    border-right: 1px solid var(--border-subtle);
}

section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li,
section[data-testid="stSidebar"] label {
    color: var(--text-secondary) !important;
}

/* Hero header */
.hero-container {
    background: var(--gradient-hero);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 2.5rem 2rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero-container::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-container::after {
    content: '';
    position: absolute;
    bottom: -30%;
    left: -10%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(6,182,212,0.1) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-title {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #f1f5f9 0%, #a5b4fc 50%, #06b6d4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
    position: relative;
    z-index: 1;
}
.hero-subtitle {
    font-size: 1.05rem;
    color: var(--text-secondary);
    font-weight: 400;
    line-height: 1.6;
    position: relative;
    z-index: 1;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(139,92,246,0.15);
    border: 1px solid rgba(139,92,246,0.3);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.75rem;
    color: #a5b4fc;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-bottom: 1rem;
    position: relative;
    z-index: 1;
}

/* Metric cards */
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.metric-card:hover {
    background: var(--bg-card-hover);
    border-color: rgba(139,92,246,0.3);
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.3);
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    border-radius: 12px 12px 0 0;
}
.metric-card.critical::before { background: var(--gradient-critical); }
.metric-card.high::before { background: var(--gradient-high); }
.metric-card.medium::before { background: var(--gradient-medium); }
.metric-card.info::before { background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue)); }
.metric-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.5rem;
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 800;
    color: var(--text-primary);
    line-height: 1.2;
}
.metric-subtext {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
}

/* Risk severity badges */
.severity-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.8px;
}
.severity-critical {
    background: rgba(239,68,68,0.15);
    color: #fca5a5;
    border: 1px solid rgba(239,68,68,0.3);
}
.severity-high {
    background: rgba(245,158,11,0.15);
    color: #fcd34d;
    border: 1px solid rgba(245,158,11,0.3);
}
.severity-medium {
    background: rgba(59,130,246,0.15);
    color: #93c5fd;
    border: 1px solid rgba(59,130,246,0.3);
}
.severity-low {
    background: rgba(16,185,129,0.15);
    color: #6ee7b7;
    border: 1px solid rgba(16,185,129,0.3);
}

/* Section panels */
.section-panel {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Evidence cards */
.evidence-card {
    background: rgba(6,182,212,0.05);
    border: 1px solid rgba(6,182,212,0.15);
    border-radius: 8px;
    padding: 1rem;
    margin-top: 0.75rem;
    font-size: 0.85rem;
    color: var(--text-secondary);
    line-height: 1.6;
}
.evidence-source {
    font-size: 0.7rem;
    color: var(--accent-cyan);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.25rem;
}

/* Chain visualization */
.chain-step {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(139,92,246,0.1);
    border: 1px solid rgba(139,92,246,0.2);
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 0.8rem;
    color: #c4b5fd;
    font-weight: 500;
}
.chain-arrow {
    color: var(--text-muted);
    font-size: 1.1rem;
    margin: 0 4px;
}

/* Progress / status indicator */
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}
.status-dot.active { background: var(--accent-emerald); box-shadow: 0 0 8px rgba(16,185,129,0.5); }
.status-dot.pending { background: var(--accent-amber); }
.status-dot.error { background: var(--accent-red); }

/* Agent event log */
.agent-event {
    background: var(--bg-secondary);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
    font-size: 0.82rem;
    color: var(--text-secondary);
    font-family: 'Inter', monospace;
}
.agent-event .agent-name {
    color: var(--accent-purple);
    font-weight: 600;
}

/* Animated pulse for running state */
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 5px rgba(139,92,246,0.3); }
    50% { box-shadow: 0 0 20px rgba(139,92,246,0.6); }
}
.running-indicator {
    animation: pulse-glow 2s ease-in-out infinite;
    border: 1px solid rgba(139,92,246,0.4) !important;
}

/* Button overrides */
.stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 2rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.3px;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(99,102,241,0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 25px rgba(99,102,241,0.5) !important;
}

/* Expander styling */
.streamlit-expanderHeader {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
}

/* Table overrides */
.stDataFrame { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Import workflow
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dealshield_adk_workflow import (
    analyze_change_of_control_graphrag,
    analyze_secondary_and_antitrust_risks,
    calculate_and_store_risk_factor,
    run_cypher,
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def fmt_usd(val: float | int | None) -> str:
    if val is None:
        return "$0"
    return f"${val:,.0f}"


def severity_badge(sev: str) -> str:
    sev_lower = sev.lower() if sev else "low"
    icons = {"critical": "🔴", "high": "🟠", "medium": "🔵", "low": "🟢"}
    icon = icons.get(sev_lower, "⚪")
    return f'<span class="severity-badge severity-{sev_lower}">{icon} {sev.upper()}</span>'


def chain_html(chain: list[dict]) -> str:
    parts = []
    for i, step in enumerate(chain):
        name = step.get("entity", step.get("name", "?"))
        parts.append(f'<span class="chain-step">{name}</span>')
        if i < len(chain) - 1:
            parts.append('<span class="chain-arrow">→</span>')
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; margin-bottom:1.5rem;">
        <div style="font-size:2.5rem;">🛡️</div>
        <div style="font-size:1.3rem; font-weight:800; background: linear-gradient(135deg, #a5b4fc, #06b6d4);
             -webkit-background-clip:text; -webkit-text-fill-color:transparent;">DealShield</div>
        <div style="font-size:0.7rem; color:#64748b; font-weight:600; letter-spacing:1.5px; text-transform:uppercase;">
            M&A Due Diligence AI</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    target_company = st.text_input(
        "🎯 Target Company",
        value="TargetTech Inc.",
        help="The acquisition target to analyze",
    )

    st.markdown("---")
    st.markdown("##### ⚡ Tech Stack")
    st.markdown("""
    - 🧠 **Google ADK** `SequentialAgent`
    - 🔷 **Neo4j Aura** Cloud Graph
    - 🔍 **GraphRAG** Multi-hop Cypher
    - 💾 **Neo4j Agent Memory**
    - 🤖 **Gemini 2.5 Flash**
    """)

    st.markdown("---")
    st.markdown("##### 📊 Graph Stats")
    try:
        stats = run_cypher("""
            MATCH (c:Company) WITH count(c) AS companies
            MATCH (e:Executive) WITH companies, count(e) AS executives
            MATCH (cl:Clause) WITH companies, executives, count(cl) AS clauses
            MATCH (dc:DocumentChunk) WITH companies, executives, clauses, count(dc) AS chunks
            RETURN companies, executives, clauses, chunks
        """)
        if stats:
            s = stats[0]
            col1, col2 = st.columns(2)
            col1.metric("Companies", s.get("companies", 0))
            col2.metric("Executives", s.get("executives", 0))
            col1.metric("Clauses", s.get("clauses", 0))
            col2.metric("Doc Chunks", s.get("chunks", 0))
        st.markdown(f'<div style="text-align:center;"><span class="status-dot active"></span>'
                    f'<span style="font-size:0.75rem; color:#10b981;">Neo4j Connected</span></div>',
                    unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Neo4j connection failed: {e}")

# ---------------------------------------------------------------------------
# Hero Header
# ---------------------------------------------------------------------------
st.markdown(f"""
<div class="hero-container">
    <div class="hero-badge">🛡️ ENTERPRISE M&A DUE DILIGENCE</div>
    <div class="hero-title">DealShield AI Analysis</div>
    <div class="hero-subtitle">
        Agentic multi-hop GraphRAG conflict detection for the proposed acquisition of
        <strong>{target_company}</strong> by <strong>Horizon Private Equity</strong>.
        Powered by Google ADK, Neo4j Aura, and Gemini 2.5 Flash.
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Main tabs
# ---------------------------------------------------------------------------
tab_analysis, tab_graph, tab_events = st.tabs([
    "🔍 Risk Analysis", "🕸️ Graph Explorer", "📋 Agent Events"
])

with tab_analysis:
    # Run analysis button
    run_col1, run_col2 = st.columns([3, 1])
    with run_col1:
        st.markdown(f"""
        <div style="color: var(--text-secondary); font-size:0.9rem;">
            Click <strong>Run Full Analysis</strong> to execute the 3-stage agentic pipeline on
            <code>{target_company}</code>.
        </div>
        """, unsafe_allow_html=True)
    with run_col2:
        run_button = st.button("🚀 Run Full Analysis", use_container_width=True)

    if run_button:
        # ── Stage 1: Change-of-Control ──
        with st.status("🔎 Stage 1: Detecting Change-of-Control Conflicts...", expanded=True) as status1:
            st.write("Running multi-hop GraphRAG traversal on Neo4j Aura...")
            coc_result = analyze_change_of_control_graphrag(target_company)
            st.session_state["coc_result"] = coc_result
            status1.update(
                label=f"✅ Stage 1 Complete – {coc_result['total_conflicts_detected']} conflicts detected",
                state="complete",
            )

        # ── Stage 2: Secondary Risks ──
        with st.status("📋 Stage 2: Scanning Secondary & Antitrust Risks...", expanded=True) as status2:
            st.write("Querying Anti-Trust, Governance, Exclusivity, and Liquidated Damages clauses...")
            sec_result = analyze_secondary_and_antitrust_risks(target_company)
            st.session_state["sec_result"] = sec_result
            status2.update(
                label=f"✅ Stage 2 Complete – {sec_result['risks_found']} risk clauses found",
                state="complete",
            )

        # ── Stage 3: Score & Write-Back ──
        with st.status("⚡ Stage 3: Calculating & Storing Risk Factors...", expanded=True) as status3:
            st.write("Computing deterministic risk scores and writing to Neo4j Aura...")

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
                        "Holdings in annual director conflict attestation. Exposure "
                        "equals the full $18.5M contract value."
                    ),
                    "source_chunk_id": "DOC-CHUNK-102",
                },
            ]

            scored_risks = []
            for risk in risks_to_score:
                result = calculate_and_store_risk_factor(**risk)
                scored_risks.append(result)
                st.write(
                    f"  ✓ {risk['risk_id']}: {result['calculation']['severity']} "
                    f"(score {result['calculation']['risk_score']}) – "
                    f"{fmt_usd(result['calculation']['total_exposure_usd'])}"
                )

            st.session_state["scored_risks"] = scored_risks
            status3.update(
                label=f"✅ Stage 3 Complete – {len(scored_risks)} risk factors stored in Neo4j",
                state="complete",
            )

        st.session_state["analysis_complete"] = True
        st.success("🎉 Full DealShield analysis pipeline complete!")

    # ── Display Results ──
    if st.session_state.get("analysis_complete"):
        coc_result = st.session_state.get("coc_result", {})
        sec_result = st.session_state.get("sec_result", {})
        scored_risks = st.session_state.get("scored_risks", [])

        # KPI Cards
        st.markdown("### 📊 Deal Risk Dashboard")

        total_exposure = sum(
            r["calculation"]["total_exposure_usd"] for r in scored_risks
        )
        critical_count = sum(
            1 for r in scored_risks if r["calculation"]["severity"] == "CRITICAL"
        )
        high_count = sum(
            1 for r in scored_risks if r["calculation"]["severity"] == "HIGH"
        )

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f"""
            <div class="metric-card critical">
                <div class="metric-label">Total Deal Exposure</div>
                <div class="metric-value">{fmt_usd(total_exposure)}</div>
                <div class="metric-subtext">Combined risk deductions</div>
            </div>
            """, unsafe_allow_html=True)
        with k2:
            st.markdown(f"""
            <div class="metric-card critical">
                <div class="metric-label">Critical Risks</div>
                <div class="metric-value">{critical_count}</div>
                <div class="metric-subtext">Score ≥ 80</div>
            </div>
            """, unsafe_allow_html=True)
        with k3:
            st.markdown(f"""
            <div class="metric-card high">
                <div class="metric-label">High Risks</div>
                <div class="metric-value">{high_count}</div>
                <div class="metric-subtext">Score ≥ 60</div>
            </div>
            """, unsafe_allow_html=True)
        with k4:
            conflicts_count = coc_result.get("total_conflicts_detected", 0)
            st.markdown(f"""
            <div class="metric-card info">
                <div class="metric-label">Conflict Rings</div>
                <div class="metric-value">{conflicts_count}</div>
                <div class="metric-subtext">Related-party chains</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Risk Factor Table ──
        st.markdown("### 🎯 Calculated Risk Factors")
        for risk in scored_risks:
            calc = risk["calculation"]
            sev = calc["severity"]
            st.markdown(f"""
            <div class="section-panel">
                <div class="section-title">
                    {severity_badge(sev)}
                    &nbsp; {risk['risk_id']} – {risk.get('clause_id', '')}
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:1rem; margin-bottom:0.75rem;">
                    <div>
                        <div class="metric-label">Risk Score</div>
                        <div style="font-size:1.3rem; font-weight:700; color:var(--text-primary);">{calc['risk_score']}/100</div>
                    </div>
                    <div>
                        <div class="metric-label">Base Penalty</div>
                        <div style="font-size:1.1rem; font-weight:600; color:var(--text-primary);">{fmt_usd(calc['base_penalty_usd'])}</div>
                    </div>
                    <div>
                        <div class="metric-label">Annual Contract</div>
                        <div style="font-size:1.1rem; font-weight:600; color:var(--text-primary);">{fmt_usd(calc['annual_contract_usd'])}</div>
                    </div>
                    <div>
                        <div class="metric-label">Total Exposure</div>
                        <div style="font-size:1.1rem; font-weight:700; color:{'#fca5a5' if sev == 'CRITICAL' else '#fcd34d' if sev == 'HIGH' else '#93c5fd'};">
                            {fmt_usd(calc['total_exposure_usd'])}
                        </div>
                    </div>
                </div>
                <div style="font-size:0.82rem; color:var(--text-secondary); line-height:1.6;">
                    {'🔗 Related-party conflict' if calc['is_related_party_conflict'] else '📋 Direct regulatory risk'}
                    &nbsp;•&nbsp; Holding hops: {calc['holding_hops']}
                    &nbsp;•&nbsp; Write status: <span style="color:#10b981;">{risk.get('write_status', 'N/A')}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Change-of-Control Conflicts Detail ──
        st.markdown("### 🕵️ Change-of-Control Conflict Chains")

        conflicts = coc_result.get("related_party_conflicts", [])
        if conflicts:
            for i, conflict in enumerate(conflicts):
                director = conflict.get("director", {})
                related = conflict.get("related_party", {})

                st.markdown(f"""
                <div class="section-panel">
                    <div class="section-title">
                        ⚠️ Conflict Ring {i + 1}: {director.get('name', 'Unknown')} → {related.get('name', 'Unknown')}
                    </div>
                    <div style="margin-bottom:0.75rem;">
                        <div class="metric-label">Ownership Chain</div>
                        {chain_html(conflict.get('holding_chain', []))}
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:1rem;">
                        <div>
                            <div class="metric-label">Director</div>
                            <div style="color:var(--text-primary); font-weight:600;">{director.get('name', '?')}</div>
                            <div style="font-size:0.75rem; color:var(--text-muted);">{director.get('title', '')}</div>
                        </div>
                        <div>
                            <div class="metric-label">Annual Supplier Value</div>
                            <div style="color:var(--accent-amber); font-weight:700; font-size:1.1rem;">
                                {fmt_usd(conflict.get('annual_supplier_value_usd', 0))}
                            </div>
                        </div>
                        <div>
                            <div class="metric-label">CoC Penalty</div>
                            <div style="color:var(--accent-red); font-weight:700; font-size:1.1rem;">
                                {fmt_usd(conflict.get('coc_termination_penalty_usd', 0))}
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Evidence citations
                citations = conflict.get("document_citations", [])
                for doc in citations:
                    if doc and doc.get("id"):
                        st.markdown(f"""
                        <div class="evidence-card">
                            <div class="evidence-source">📄 {doc.get('source_doc', 'Unknown')} — Page {doc.get('page', '?')}</div>
                            {doc.get('text', 'No text available')}
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("No related-party conflict rings detected for this target.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Secondary Risks ──
        st.markdown("### 📋 Secondary & Antitrust Risks")
        sec_risks = sec_result.get("risk_details", [])
        if sec_risks:
            for risk_detail in sec_risks:
                clause = risk_detail.get("clause", {})
                st.markdown(f"""
                <div class="section-panel">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                        <div style="font-weight:600; color:var(--text-primary);">
                            {clause.get('id', '?')} – {clause.get('title', 'Unknown')}
                        </div>
                        <div style="color:var(--accent-amber); font-weight:700;">
                            {fmt_usd(clause.get('financial_exposure_usd', 0))}
                        </div>
                    </div>
                    <div style="font-size:0.82rem; color:var(--text-secondary);">
                        Type: <strong>{clause.get('clause_type', 'N/A')}</strong>
                        &nbsp;•&nbsp; Source: {risk_detail.get('source', 'unknown')}
                    </div>
                    <div style="font-size:0.82rem; color:var(--text-muted); margin-top:0.25rem;">
                        {clause.get('summary', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                evidence = risk_detail.get("evidence_chunks", [])
                for doc in evidence:
                    if doc and doc.get("id"):
                        with st.expander(f"📄 Evidence: {doc.get('source_doc', '?')}"):
                            st.caption(f"Page {doc.get('page', '?')} | Chunk ID: {doc.get('id', '?')}")
                            st.write(doc.get("text", ""))
        else:
            st.info("No additional secondary risk clauses found.")

        # ── Final Summary ──
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div class="section-panel" style="border-color: rgba(239,68,68,0.3); background: rgba(239,68,68,0.03);">
            <div class="section-title" style="color: #fca5a5;">
                ⚖️ Deal Impact Summary
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:2rem;">
                <div>
                    <div class="metric-label">Total Deal Deduction</div>
                    <div style="font-size:2rem; font-weight:800; color:#fca5a5;">
                        {fmt_usd(total_exposure)}
                    </div>
                    <div style="font-size:0.82rem; color:var(--text-muted); margin-top:0.25rem;">
                        Sum of all calculated risk factor exposures
                    </div>
                </div>
                <div>
                    <div class="metric-label">Risk Breakdown</div>
                    <div style="font-size:0.85rem; color:var(--text-secondary); line-height:2;">
                        🔴 CRITICAL: {critical_count} risk(s)<br>
                        🟠 HIGH: {high_count} risk(s)<br>
                        📊 Total Factors Stored: {len(scored_risks)}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tab 2: Graph Explorer
# ---------------------------------------------------------------------------
with tab_graph:
    st.markdown("### 🕸️ Neo4j Graph Explorer")
    st.markdown("""
    <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:1rem;">
        Run custom Cypher queries against the DealShield knowledge graph in Neo4j Aura.
    </div>
    """, unsafe_allow_html=True)

    preset_queries = {
        "🎯 Focal Deal Structure": (
            "MATCH (acquirer:Company {id:'COMP-001'})-[r:HOLDS_STAKE_IN]->"
            "(target:Company {id:'COMP-002'}) "
            "RETURN acquirer.name AS Acquirer, r.status AS Deal_Status, "
            "target.name AS Target, target.valuation_usd AS Valuation"
        ),
        "🕵️ Marcus Vance Conflict Chain": (
            "MATCH (d:Executive {id:'EXEC-001'})-[:DIRECTOR_OF]->"
            "(spouse:Executive {id:'EXEC-002'})-[:HOLDS_STAKE_IN]->"
            "(holding:Company)-[:HOLDS_STAKE_IN]->(supplier:Company)-"
            "[:SUPPLIES_TO]->(t:Company {id:'COMP-002'}) "
            "RETURN d.name AS Director, spouse.name AS Spouse, "
            "holding.name AS Holding_Co, supplier.name AS Supplier, "
            "[(supplier)-[s:SUPPLIES_TO]->(t)|s.annual_value_usd][0] AS Annual_Value"
        ),
        "📋 All CoC Clauses + Evidence": (
            "MATCH (t:Company {name:'TargetTech Inc.'})-[:RESTRICTED_BY]->"
            "(cl:Clause {clause_type:'Change of Control'})-[:EXTRACTED_FROM]->"
            "(dc:DocumentChunk) "
            "RETURN cl.id AS Clause, cl.title AS Title, "
            "cl.financial_exposure_usd AS Exposure, "
            "dc.source_doc AS Document, dc.page AS Page"
        ),
        "⚡ Stored Risk Factors": (
            "MATCH (c:Company)-[:HAS_CALCULATED_RISK]->(r:RiskFactor) "
            "WHERE r.updated_by = 'DealShield_GoogleADK_Agent' "
            "RETURN r.id AS Risk_ID, r.category AS Category, r.severity AS Severity, "
            "r.risk_score AS Score, r.total_exposure_usd AS Exposure, "
            "r.deal_deduction_usd AS Deal_Deduction, r.calculated_at AS Calculated"
        ),
        "🔗 All Related-Party Conflicts (Multi-hop)": (
            "MATCH (d:Executive)-[:DIRECTOR_OF]->(t:Company {name:'TargetTech Inc.'})"
            "<-[s:SUPPLIES_TO]-(sup:Company)<-[:HOLDS_STAKE_IN*1..2]-(rel:Executive)"
            "<-[:DIRECTOR_OF]-(d) "
            "RETURN d.name AS Director, rel.name AS Related_Party, "
            "sup.name AS Supplier, s.annual_value_usd AS Annual_Value"
        ),
    }

    selected_preset = st.selectbox("📌 Preset Queries", options=list(preset_queries.keys()))
    default_query = preset_queries[selected_preset]

    custom_query = st.text_area(
        "Cypher Query",
        value=default_query,
        height=100,
    )

    if st.button("▶️ Execute Query", use_container_width=True):
        try:
            results = run_cypher(custom_query)
            if results:
                st.dataframe(results, use_container_width=True)
                st.caption(f"{len(results)} record(s) returned")
            else:
                st.info("Query returned no results.")
        except Exception as e:
            st.error(f"Cypher error: {e}")

# ---------------------------------------------------------------------------
# Tab 3: Agent Events
# ---------------------------------------------------------------------------
with tab_events:
    st.markdown("### 📋 Agentic Pipeline Event Log")
    st.markdown("""
    <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:1rem;">
        Detailed trace of the SequentialAgent pipeline execution across all 3 sub-agents.
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("analysis_complete"):
        st.markdown("""
        <div class="section-panel">
            <div class="section-title">🤖 Pipeline Execution Summary</div>
            <div style="font-size:0.85rem; color:var(--text-secondary); line-height:2;">
                <span class="status-dot active"></span> <strong>Stage 1</strong>: CoC_Conflict_Detector – <code>analyze_change_of_control_graphrag</code><br>
                <span class="status-dot active"></span> <strong>Stage 2</strong>: Secondary_Risk_Analyzer – <code>analyze_secondary_and_antitrust_risks</code><br>
                <span class="status-dot active"></span> <strong>Stage 3</strong>: Risk_Scorer – <code>calculate_and_store_risk_factor</code> × 3 calls
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Raw JSON results
        with st.expander("🔍 Stage 1: Change-of-Control Results (JSON)"):
            st.json(st.session_state.get("coc_result", {}))

        with st.expander("🔍 Stage 2: Secondary Risk Results (JSON)"):
            st.json(st.session_state.get("sec_result", {}))

        with st.expander("🔍 Stage 3: Risk Scoring Results (JSON)"):
            st.json(st.session_state.get("scored_risks", []))
    else:
        st.info("Run the analysis first to see agent events.")
