#!/usr/bin/env python3
"""
DealShield v2 - synthetic M&A due-diligence graph generator.

Covers 4 vectors / 9 clause types:
  CONFLICT_OF_INTEREST   : UNDISCLOSED_RPT, GOVERNANCE_ATTESTATION_FAILURE, DUAL_FIDUCIARY
  CHANGE_OF_CONTROL      : COC_POISON_PILL, COC_VENDOR_LOCKIN
  ANTITRUST_REGULATORY   : HORIZONTAL_MARKET_CAP, FEDERAL_CONTRACT_REVOCATION
  NONCOMPETE_EXCLUSIVITY : AUTO_SLA_RENEWAL_IP_LOCKIN, SOLE_SOURCE_EXCLUSIVITY

USAGE
  # A) Direct to Neo4j / Aura over Bolt  (pip install neo4j)
  export NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io NEO4J_USER=neo4j NEO4J_PASSWORD=...
  python dealshield_generator.py --wipe --verify

  # B) Neo4j MCP: emit a .cypher file, then feed statements to the MCP write-cypher tool
  python dealshield_generator.py --emit-cypher dealshield_load.cypher

Also writes ground_truth.json (expected findings, for agent evaluation).
Planted scenarios are NOT pre-scored: the agent computes RiskFactor nodes and writes them
back (HAS_CALCULATED_RISK). Use --seed-risks to pre-populate them for UI testing only.
"""
import argparse, json, os, random
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

random.seed(42)

# ----------------------------------------------------------------------------- model
NODES = []   # (labels tuple, props)
RELS = []    # (type, (label,id), (label,id), props)
_seen = set()
_chunk_n = [0]


def node(labels, nid, **props):
    labels = (labels,) if isinstance(labels, str) else tuple(labels)
    key = (labels[0], nid)
    assert key not in _seen, f"duplicate id {key}"
    _seen.add(key)
    NODES.append((labels, {"id": nid, **{k: v for k, v in props.items() if v is not None}}))
    return (labels[0], nid)


def rel(rtype, a, b, **props):
    RELS.append((rtype, a, b, {k: v for k, v in props.items() if v is not None}))


def evidence(ref, doc, page, text, conf=0.95):
    """Lexical layer: DocumentChunk linked to the entity it supports."""
    _chunk_n[0] += 1
    cid = f"CH{_chunk_n[0]:04d}"
    ch = node("DocumentChunk", cid, text=text, page=page, docId=doc[1], chunkIndex=_chunk_n[0])
    rel("HAS_CHUNK", doc, ch)
    rel("DERIVED_FROM", ref, ch, confidence=conf, page=page)
    return ch


# ----------------------------------------------------------------------------- taxonomy
CLAUSE_TYPES = [
    # code, category, name, detection, description
    ("UNDISCLOSED_RPT", "CONFLICT_OF_INTEREST", "Undisclosed Related-Party Transaction", "GRAPH_PATTERN",
     "Sole-source contract approved by an insider whose family controls the vendor via (offshore) holding entities."),
    ("GOVERNANCE_ATTESTATION_FAILURE", "CONFLICT_OF_INTEREST", "Governance Attestation Failure", "GRAPH_PATTERN",
     "Director attests 'no conflicts' while a related party holds a stake in a supplier."),
    ("DUAL_FIDUCIARY", "CONFLICT_OF_INTEREST", "Dual-Fiduciary Conflict", "GRAPH_PATTERN",
     "Non-executive director holds an undisclosed equity stake in a tier-2 vendor."),
    ("COC_POISON_PILL", "CHANGE_OF_CONTROL", "Change-of-Control Poison Pill", "CLAUSE",
     "Liquidated termination penalty triggered by buyout / equity transfer above threshold."),
    ("COC_VENDOR_LOCKIN", "CHANGE_OF_CONTROL", "Mandatory Vendor Lock-In after CoC", "CLAUSE",
     "Minimum annual purchase from a named supplier for N months after change of control."),
    ("HORIZONTAL_MARKET_CAP", "ANTITRUST_REGULATORY", "Horizontal Market Cap (Common Parent)", "CLAUSE+GRAPH",
     "Target may not share a common parent with any entity above a market-share threshold."),
    ("FEDERAL_CONTRACT_REVOCATION", "ANTITRUST_REGULATORY", "Federal Contract Revocation on Overlap", "CLAUSE+GRAPH",
     "Gov/DoD contract auto-revoked if acquirer overlaps named competitors or exceeds share limits."),
    ("AUTO_SLA_RENEWAL_IP_LOCKIN", "NONCOMPETE_EXCLUSIVITY", "Automatic SLA Renewal & IP Lock-In", "CLAUSE",
     "Evergreen SLA auto-renews unless notice given in window; restricts alternative suppliers / IP reuse."),
    ("SOLE_SOURCE_EXCLUSIVITY", "NONCOMPETE_EXCLUSIVITY", "Sole-Source Exclusivity Commitment", "CLAUSE",
     "Long-term exclusive purchasing of a critical component under take-or-pay penalties."),
    ("CONFIDENTIALITY", "STANDARD", "Confidentiality", "CLAUSE", "Boilerplate."),
    ("PAYMENT_TERMS", "STANDARD", "Payment Terms", "CLAUSE", "Boilerplate."),
    ("GOVERNING_LAW", "STANDARD", "Governing Law", "CLAUSE", "Boilerplate."),
    ("INSOLVENCY_TERMINATION", "STANDARD", "Termination on Insolvency", "CLAUSE", "Not a CoC trigger (decoy)."),
]

SOURCES = ["MCA_PUBLIC_SEARCH", "CONTRACT", "REGULATORY_FILING", "CORPORATE_FILING", "BOARD_ROSTER", "EXCEL_FIGURES",
           "COMPANY_HISTORY"]


# ----------------------------------------------------------------------------- data build
def build(seed_risks=False):
    # --- taxonomy
    ct = {}
    for code, cat, name, det, desc in CLAUSE_TYPES:
        ct[code] = node("ClauseType", code, category=cat, name=name, detection=det, description=desc)

    # --- documents (source layer from team brainstorm)
    def doc(i, title, src, pages):
        return node("Document", i, title=title, source=src, pages=pages)

    d_msa = doc("DOC_MSA_SILVERLINE", "Master Supply Agreement - Silverline Components", "CONTRACT", 84)
    d_qua = doc("DOC_QUANTA", "Component Supply & Renewal Agreement - Quanta Fabrication", "CONTRACT", 41)
    d_asic = doc("DOC_ASIC", "ASIC Exclusive Supply Agreement - Hsinchu ASIC Works", "CONTRACT", 66)
    d_sla = doc("DOC_SLA", "SLA & IP License Addendum - CoreStack Cloud", "CONTRACT", 37)
    d_dod = doc("DOC_DOD", "DoD Contract W56-RSP-2024 + Ownership Covenant Annex", "CONTRACT", 120)
    d_mca = doc("DOC_MCA", "MCA Public Search - Meridian/Silverline Beneficial Ownership Extract", "MCA_PUBLIC_SEARCH", 9)
    d_reg = doc("DOC_BO_REG", "Beneficial Ownership Registry Extract (BVI / Singapore)", "REGULATORY_FILING", 14)
    d_cor = doc("DOC_CORP", "Northwind Corporate Filings - Director Conflict Disclosures FY2025", "CORPORATE_FILING", 22)
    d_brd = doc("DOC_BOARD", "Northwind Board Roster & Committee Charter", "BOARD_ROSTER", 6)
    d_xls = doc("DOC_XLS", "Market Share & Spend Figures (Excel export)", "EXCEL_FIGURES", 12)
    d_hist = doc("DOC_HIST", "Company History - Northwind Microsystems", "COMPANY_HISTORY", 18)

    # --- deal + core companies
    ACQ, TGT, FUND, ORION, VANG = "C_ACQ", "C_TGT", "C_FUND3", "C_ORION", "C_VANGUARD"
    fund = node(["Company", "Fund"], FUND, name="Helix Capital Fund III LP", jurisdiction="US-DE", type="PE_FUND")
    acq = node(["Company", "Acquirer"], ACQ, name="Helix Acquisition Corp", jurisdiction="US-DE", type="SPV")
    tgt = node(["Company", "Target"], TGT, name="Northwind Microsystems Inc.", jurisdiction="US-DE",
               type="OPERATING", revenueUSD=412_000_000, employees=1850, incorporationDate="2004-03-11")
    orion = node(["Company", "PortfolioCompany"], ORION, name="Orion Defense Electronics Inc.",
                 jurisdiction="US-VA", type="OPERATING")
    vang = node(["Company", "Competitor"], VANG, name="Vanguard Aerospace Corp.", jurisdiction="US-CA",
                type="OPERATING")
    ndef = node(["Company", "Subsidiary"], "C_TGT_DEF", name="Northwind Defense Systems LLC",
                jurisdiction="US-DE", type="OPERATING")
    nind = node(["Company", "Subsidiary"], "C_TGT_IN", name="Northwind India Pvt Ltd", jurisdiction="IN",
                type="OPERATING", cin="U32109PN2011PTC139842")
    rel("IS_SUBSIDIARY_OF", acq, fund, pct=100)
    rel("IS_SUBSIDIARY_OF", orion, fund, pct=62)
    rel("IS_SUBSIDIARY_OF", ndef, tgt, pct=100)
    rel("IS_SUBSIDIARY_OF", nind, tgt, pct=100)
    rel("HOLDS_STAKE_IN", fund, vang, pct=9.0, type="DIRECT", since="2022-06-01")
    evidence(vang, d_xls, 4, "Helix Capital Fund III LP holds 9.0% of Vanguard Aerospace Corp. (Schedule of Portfolio Holdings).")

    deal = node("Deal", "DEAL_AEGIS", name="Project Aegis", dealValueUSD=850_000_000, equityTransferPct=100.0,
                announcedDate="2026-10-12", expectedCloseDate="2027-01-31", status="DILIGENCE")
    rel("ACQUIRER", deal, acq)
    rel("TARGET", deal, tgt)

    # --- markets
    m_radar = node("Market", "M_RADAR", name="Defense Radar Signal Processing", sector="DEFENSE", naics="334511")
    m_asic = node("Market", "M_ASIC", name="Custom ASIC Fabrication", sector="SEMICONDUCTORS", naics="334413")
    rel("OPERATES_IN", tgt, m_radar)
    rel("HAS_MARKET_SHARE", orion, m_radar, pct=31.0, year=2025, source="EXCEL_FIGURES")
    rel("HAS_MARKET_SHARE", vang, m_radar, pct=28.0, year=2025, source="EXCEL_FIGURES")
    rel("HAS_MARKET_SHARE", tgt, m_radar, pct=7.5, year=2025, source="EXCEL_FIGURES")
    evidence(orion, d_xls, 7, "Orion Defense Electronics: 31.0% of Defense Radar Signal Processing market (FY2025).")

    asic = node("Component", "COMP_ASIC7", name="NW-7nm Radar ASIC", type="ASIC", criticality="CRITICAL")

    # --- people (board roster + management)
    def person(i, name, **kw):
        return node("Person", i, name=name, **kw)

    marcus = person("P_HALE", "Marcus Hale", nationality="US")
    dana = person("P_WHITFIELD", "Dana Whitfield", nationality="US")
    elena = person("P_VOSS", "Elena Voss", nationality="US")
    tom = person("P_TOM_W", "Tom Whitfield", nationality="US")
    arjun = person("P_RAMAN", "Arjun Raman", nationality="IN")
    priya = person("P_PRIYA", "Priya Raman", nationality="IN")
    sunita = person("P_RAO", "Sunita Rao", nationality="IN")
    neil = person("P_DAS", "Neil Das", nationality="IN")
    rel("WORKS_AT", marcus, tgt, title="CEO", since="2016-02-01", approvalLimitUSD=100_000_000)
    rel("WORKS_AT", arjun, tgt, title="VP Procurement", since="2018-07-01", department="Procurement",
        approvalLimitUSD=60_000_000)
    rel("WORKS_AT", sunita, tgt, title="CFO", since="2019-01-15", approvalLimitUSD=80_000_000)
    rel("DIRECTOR_OF", marcus, tgt, type="EXECUTIVE", since="2016-02-01")
    rel("DIRECTOR_OF", dana, tgt, type="NON_EXECUTIVE", since="2019-05-01", committee="AUDIT")
    rel("DIRECTOR_OF", elena, tgt, type="NON_EXECUTIVE", since="2020-09-01", committee="PROCUREMENT")
    rel("RELATED_TO", priya, arjun, relation="SPOUSE", verified=True, source="MCA_PUBLIC_SEARCH")
    rel("RELATED_TO", tom, dana, relation="SPOUSE", verified=True, source="CORPORATE_FILING")
    rel("RELATED_TO", neil, sunita, relation="SPOUSE", verified=True, source="CORPORATE_FILING")
    evidence(arjun, d_brd, 2, "Arjun Raman, VP Procurement, delegated authority up to USD 60M for sole-source awards.")
    for p, pg in ((marcus, 1), (dana, 2), (elena, 3)):
        evidence(p, d_brd, pg, f"Board roster entry for {p[1]} (see committee assignments).")

    # --- clean directors
    for i, nm in enumerate(["Ravi Menon", "Claire Dubois", "Hiroshi Tanaka"]):
        p = person(f"P_DIR{i}", nm)
        rel("DIRECTOR_OF", p, tgt, type="NON_EXECUTIVE", since=f"20{18 + i}-01-01")

    # --- disclosures (FY2025 annual director conflict attestation)
    def disclosure(p, declares=(), attests=True, page=1):
        did = f"DISC_{p[1]}_2025"
        d = node("Disclosure", did, year=2025, type="ANNUAL_DIRECTOR_CONFLICT", attestsNoConflict=attests,
                 filedDate="2026-02-20")
        rel("FILED", p, d)
        rel("DECLARES", d, declares[0]) if declares else None
        for extra in declares[1:]:
            rel("DECLARES", d, extra)
        evidence(d, d_cor, page, f"{p[1]} attests: 'I have no conflict of interest or related-party supplier interest.'"
                 if attests else f"{p[1]} declares interests as listed.")
        return d

    disclosure(dana, page=5)
    disclosure(elena, page=6)
    for i in range(3):
        disclosure(("Person", f"P_DIR{i}"), page=7 + i)
    # decoy: declared related-party -> NOT a finding
    brightpath = node(["Company", "Vendor"], "V_BRIGHT", name="Brightpath Logistics Pvt Ltd", jurisdiction="IN",
                      tier=1, cin="U63090MH2015PTC264411")
    rel("HOLDS_STAKE_IN", neil, brightpath, pct=60.0, type="DIRECT")
    disclosure(sunita, declares=(brightpath,), attests=False, page=11)

    # =============== SCENARIO 1: CoC poison pill + vendor lock-in + undisclosed RPT (offshore, 4-hop) ===============
    silver = node(["Company", "Vendor"], "V_SILVER", name="Silverline Components Ltd", jurisdiction="IN", tier=1,
                  cin="U31900PN2014PLC152233")
    merid = node(["Company", "Offshore", "Shell"], "C_MERIDIAN", name="Meridian Holdings Ltd", jurisdiction="BVI",
                 isOffshore=True, isShell=True, type="HOLDING")
    rel("HOLDS_STAKE_IN", priya, merid, pct=100.0, type="BENEFICIAL", since="2019-03-01")
    rel("HOLDS_STAKE_IN", merid, silver, pct=90.0, type="DIRECT", since="2019-03-05")
    rel("SUPPLIES_TO", silver, tgt, tier=1, componentCategory="PCB_ASSEMBLY", annualSpendUSD=9_600_000)
    evidence(silver, d_mca, 3, "Silverline Components Ltd: shareholder Meridian Holdings Ltd (BVI) holds 90% of paid-up capital.")
    evidence(merid, d_reg, 5, "Meridian Holdings Ltd (BVI): sole beneficial owner - Priya Raman (100%).")
    evidence(priya, d_mca, 4, "Priya Raman, DIN-linked spouse of Arjun Raman; residing Pune, Maharashtra.")

    a1 = node("Agreement", "A_MSA_SILVER", title="Master Supply Agreement - Silverline", type="MSA",
              effectiveDate="2023-04-01", expiryDate="2028-03-31", totalValueUSD=48_000_000, governingLaw="Delaware")
    rel("AGREEMENT_OF", a1, tgt, role="BUYER")
    rel("AGREEMENT_OF", a1, silver, role="SUPPLIER")
    c_pill = node("Clause", "CL_COC_PILL_SILVER", clauseType="COC_POISON_PILL", section="14.3",
                  title="Termination Fee on Change of Control",
                  text="Upon any transfer of more than 50% of the voting equity of Buyer, Supplier may terminate and Buyer shall pay a liquidated sum of USD 15,000,000.",
                  triggerType="EQUITY_TRANSFER", thresholdPct=50.0, penaltyUSD=15_000_000, severity="HIGH")
    c_lock = node("Clause", "CL_COC_LOCK_SILVER", clauseType="COC_VENDOR_LOCKIN", section="14.5",
                  title="Post-CoC Minimum Purchase Commitment",
                  text="Following a Change of Control, Buyer shall purchase not less than USD 4,200,000 per year from Supplier for 60 months.",
                  triggerType="EQUITY_TRANSFER", thresholdPct=50.0, minAnnualPurchaseUSD=4_200_000,
                  durationMonths=60, severity="HIGH")
    for c, pg in ((c_pill, 47), (c_lock, 48)):
        rel("CLAUSE_OF", c, a1)
        rel("INSTANCE_OF", c, ct[c[1] and ("COC_POISON_PILL" if c is c_pill else "COC_VENDOR_LOCKIN")])
        evidence(c, d_msa, pg, "Section 14 - Change of Control (verbatim clause text as extracted).")
    tx1 = node("Transaction", "TX_SILVER_AWARD", type="SOLE_SOURCE_AWARD", amountUSD=48_000_000, date="2023-03-20",
               soleSource=True, description="Sole-source award of PCB assembly program, no competitive bid.")
    rel("IS_PART_OF", tx1, tgt)
    rel("UNDER_AGREEMENT", tx1, a1)
    rel("WITH_VENDOR", tx1, silver)
    rel("APPROVED_BY", tx1, arjun, date="2023-03-20", withinAuthority=True)
    evidence(tx1, d_msa, 2, "Approved by: Arjun Raman, VP Procurement. Sole-source justification: 'incumbent supplier'.")
    b1 = node("Benefit", "BEN_SILVER_PILL", type="TERMINATION_FEE", amountUSD=15_000_000,
              description="Liquidated fee payable to Silverline on CoC.")
    rel("HAS_BENEFIT", tx1, b1)
    rel("ACCRUES_TO", b1, silver)
    rel("ACCRUES_TO", b1, priya, indirect=True, via="Meridian Holdings Ltd")

    # =============== SCENARIO 2: dual fiduciary - director holds stake in tier-2 vendor ===============
    quanta = node(["Company", "Vendor"], "V_QUANTA", name="Quanta Fabrication Pte Ltd", jurisdiction="SG", tier=2)
    rel("HOLDS_STAKE_IN", elena, quanta, pct=12.0, type="DIRECT", since="2021-04-01")
    rel("SUPPLIES_TO", quanta, tgt, tier=2, componentCategory="WAFER_FAB", annualSpendUSD=3_100_000)
    a2 = node("Agreement", "A_QUANTA", title="Component Supply & Renewal Agreement - Quanta", type="SUPPLY",
              effectiveDate="2022-01-01", expiryDate="2027-12-31", totalValueUSD=15_500_000, governingLaw="Singapore")
    rel("AGREEMENT_OF", a2, tgt, role="BUYER")
    rel("AGREEMENT_OF", a2, quanta, role="SUPPLIER")
    tx2 = node("Transaction", "TX_QUANTA_RENEW", type="RENEWAL_FEE", amountUSD=1_800_000, date="2025-11-10",
               soleSource=False, description="Renewal fee uplift of 12% approved by Procurement Committee.")
    rel("IS_PART_OF", tx2, tgt)
    rel("UNDER_AGREEMENT", tx2, a2)
    rel("WITH_VENDOR", tx2, quanta)
    rel("APPROVED_BY", tx2, elena, date="2025-11-10", role="PROCUREMENT_COMMITTEE_CHAIR")
    evidence(quanta, d_reg, 9, "Quanta Fabrication Pte Ltd (ACRA extract): shareholder Elena R. Voss, 12.0%.")
    evidence(tx2, d_qua, 12, "Renewal fee USD 1.8M approved by Procurement Committee (Chair: E. Voss), minutes of 10-Nov-2025.")

    # =============== SCENARIO 3: attestation failure - spouse owns CoreStack (+ auto-renew SLA) ===============
    core = node(["Company", "Vendor"], "V_CORESTACK", name="CoreStack Cloud Services Inc.", jurisdiction="US-WA", tier=1)
    rel("HOLDS_STAKE_IN", tom, core, pct=35.0, type="DIRECT", since="2017-01-01")
    rel("SUPPLIES_TO", core, tgt, tier=1, componentCategory="CLOUD_EDA", annualSpendUSD=6_000_000)
    evidence(core, d_cor, 18, "CoreStack Cloud Services Inc. Form D / cap table: Thomas Whitfield 35%.")
    a4 = node("Agreement", "A_SLA_CORE", title="SLA & IP License Addendum - CoreStack", type="SLA",
              effectiveDate="2023-01-15", expiryDate="2027-01-15", totalValueUSD=18_000_000, governingLaw="Washington")
    rel("AGREEMENT_OF", a4, tgt, role="CUSTOMER")
    rel("AGREEMENT_OF", a4, core, role="PROVIDER")
    c_sla = node("Clause", "CL_SLA_CORE", clauseType="AUTO_SLA_RENEWAL_IP_LOCKIN", section="9.2",
                 title="Automatic Renewal & Exclusive Toolchain IP License",
                 text="SLA renews automatically for successive 36-month terms unless Customer gives written notice at least 90 days before renewal; Customer shall not migrate EDA IP libraries to a third-party provider during any term.",
                 autoRenew=True, renewalTermMonths=36, noticeDays=90, renewalDate="2027-01-15",
                 noticeDeadline="2026-10-17", annualFeeUSD=6_000_000, exitPenaltyUSD=4_500_000, severity="HIGH")
    rel("CLAUSE_OF", c_sla, a4)
    rel("INSTANCE_OF", c_sla, ct["AUTO_SLA_RENEWAL_IP_LOCKIN"])
    evidence(c_sla, d_sla, 21, "Section 9.2 - automatic renewal for 36 months; 90-day written notice; no migration of IP libraries.")
    tx4 = node("Transaction", "TX_CORE_SLA", type="SLA_RENEWAL", amountUSD=18_000_000, date="2022-12-20", soleSource=False,
               description="Three-year SLA and IP license.")
    rel("IS_PART_OF", tx4, tgt)
    rel("UNDER_AGREEMENT", tx4, a4)
    rel("WITH_VENDOR", tx4, core)
    rel("APPROVED_BY", tx4, sunita, date="2022-12-20")

    # =============== SCENARIO 4: ASIC sole-source exclusivity (take-or-pay) ===============
    hsin = node(["Company", "Vendor"], "V_HSINCHU", name="Hsinchu ASIC Works Co. Ltd", jurisdiction="TW", tier=1)
    rel("SUPPLIES_TO", hsin, tgt, tier=1, componentCategory="ASIC", annualSpendUSD=9_000_000)
    rel("SUPPLIES_COMPONENT", hsin, asic, sole=True)
    a3 = node("Agreement", "A_ASIC", title="ASIC Exclusive Supply Agreement - Hsinchu", type="SUPPLY",
              effectiveDate="2024-07-01", expiryDate="2031-06-30", totalValueUSD=63_000_000, governingLaw="Singapore")
    rel("AGREEMENT_OF", a3, tgt, role="BUYER")
    rel("AGREEMENT_OF", a3, hsin, role="SUPPLIER")
    c_ss = node("Clause", "CL_SOLE_ASIC", clauseType="SOLE_SOURCE_EXCLUSIVITY", section="6.1",
                title="Exclusive Purchasing - 7nm Radar ASIC",
                text="Buyer shall purchase 100% of its requirements for the NW-7nm Radar ASIC exclusively from Supplier for 84 months; shortfall below USD 9,000,000 p.a. is payable as take-or-pay; breach penalty USD 22,000,000.",
                durationMonths=84, minAnnualPurchaseUSD=9_000_000, penaltyUSD=22_000_000, exclusivityPct=100.0,
                survivesChangeOfControl=True, severity="CRITICAL")
    rel("CLAUSE_OF", c_ss, a3)
    rel("INSTANCE_OF", c_ss, ct["SOLE_SOURCE_EXCLUSIVITY"])
    rel("COVERS_COMPONENT", c_ss, asic)
    evidence(c_ss, d_asic, 29, "Section 6.1 - exclusive requirements purchasing of NW-7nm Radar ASIC for 84 months.")
    rel("OPERATES_IN", hsin, m_asic)

    # =============== SCENARIO 5: antitrust - common parent cap + DoD revocation ===============
    gc = node("GovContract", "GC_DOD_RSP", agency="Department of Defense", title="Radar Signal Processor LRIP",
              contractNo="W56-RSP-2024-0081", valueUSD=120_000_000, awardDate="2024-09-30")
    rel("AWARDED_TO", gc, ndef)
    a5 = node("Agreement", "A_DOD", title="DoD Contract W56-RSP-2024-0081 - Ownership Covenant Annex", type="GOV_CONTRACT",
              effectiveDate="2024-09-30", expiryDate="2029-09-29", totalValueUSD=120_000_000, governingLaw="US-Federal")
    rel("AGREEMENT_OF", a5, ndef, role="CONTRACTOR")
    c_cap = node("Clause", "CL_CAP_DOD", clauseType="HORIZONTAL_MARKET_CAP", section="H.12",
                 title="Common Parent Restriction",
                 text="Contractor shall not share a common parent with any entity holding more than 25% share of the Defense Radar Signal Processing market.",
                 thresholdPct=25.0, severity="CRITICAL")
    c_rev = node("Clause", "CL_REV_DOD", clauseType="FEDERAL_CONTRACT_REVOCATION", section="H.14",
                 title="Automatic Revocation on Competitor Overlap",
                 text="This contract is revoked automatically and immediately if the Contractor's ultimate parent holds any interest in Vanguard Aerospace Corp. or exceeds the market share limit in H.12.",
                 thresholdPct=25.0, automatic=True, valueAtRiskUSD=120_000_000, severity="CRITICAL")
    for c, code, pg in ((c_cap, "HORIZONTAL_MARKET_CAP", 88), (c_rev, "FEDERAL_CONTRACT_REVOCATION", 89)):
        rel("CLAUSE_OF", c, a5)
        rel("INSTANCE_OF", c, ct[code])
        evidence(c, d_dod, pg, f"Section {c[1][-3:]} - ownership covenant text extracted from contract annex.")
    rel("RESTRICTS_MARKET", c_cap, m_radar)
    rel("RESTRICTS_MARKET", c_rev, m_radar)
    rel("REVOKES", c_rev, gc)
    rel("NAMES_COMPETITOR", c_rev, vang)

    # =============== DECOYS (must NOT be flagged) ===============
    atlas = node(["Company", "Vendor"], "V_ATLAS", name="Atlas Licensing LLC", jurisdiction="US-TX", tier=1)
    a6 = node("Agreement", "A_ATLAS", title="Technology License - Atlas", type="LICENSE", effectiveDate="2022-05-01",
              expiryDate="2027-04-30", totalValueUSD=2_000_000, governingLaw="Texas")
    rel("AGREEMENT_OF", a6, tgt, role="LICENSEE")
    rel("AGREEMENT_OF", a6, atlas, role="LICENSOR")
    c_cap2 = node("Clause", "CL_CAP_ATLAS", clauseType="HORIZONTAL_MARKET_CAP", section="11.1",
                  title="Common Parent Restriction (40%)",
                  text="Licensee shall not share a common parent with an entity above 40% market share.",
                  thresholdPct=40.0, severity="LOW")
    rel("CLAUSE_OF", c_cap2, a6)
    rel("INSTANCE_OF", c_cap2, ct["HORIZONTAL_MARKET_CAP"])
    rel("RESTRICTS_MARKET", c_cap2, m_radar)          # Orion 31% < 40% -> not breached
    evidence(c_cap2, d_dod, 91, "Atlas licence s.11.1 market-cap threshold is 40%.")
    c_ins = node("Clause", "CL_INSOLV_BRIGHT", clauseType="INSOLVENCY_TERMINATION", section="12.2",
                 title="Termination on Insolvency", text="Either party may terminate on insolvency.",
                 triggerType="INSOLVENCY", penaltyUSD=2_000_000, severity="LOW")
    a7 = node("Agreement", "A_BRIGHT", title="Logistics Services - Brightpath", type="SERVICES",
              effectiveDate="2021-01-01", expiryDate="2026-12-31", totalValueUSD=4_000_000, governingLaw="India")
    rel("AGREEMENT_OF", a7, tgt, role="CUSTOMER")
    rel("AGREEMENT_OF", a7, brightpath, role="PROVIDER")
    rel("CLAUSE_OF", c_ins, a7)
    rel("INSTANCE_OF", c_ins, ct["INSOLVENCY_TERMINATION"])
    rel("SUPPLIES_TO", brightpath, tgt, tier=1, componentCategory="LOGISTICS", annualSpendUSD=800_000)
    tx7 = node("Transaction", "TX_BRIGHT", type="SOLE_SOURCE_AWARD", amountUSD=4_000_000, date="2020-12-01", soleSource=True,
               description="Logistics award; related-party interest was declared by CFO.")
    rel("IS_PART_OF", tx7, tgt)
    rel("UNDER_AGREEMENT", tx7, a7)
    rel("WITH_VENDOR", tx7, brightpath)
    rel("APPROVED_BY", tx7, sunita, date="2020-12-01")

    # =============== NOISE: ordinary vendors, agreements and boilerplate ===============
    names = ["Apex Metals", "Bluefin Plastics", "Cobalt Tooling", "Delta Packaging", "Evergreen Chemicals",
             "Fulcrum Machining", "Granite Cables", "Harbor Testing Labs", "Ionic Coatings", "Juniper Fasteners",
             "Keystone Wire", "Lumen Optics"]
    approvers = [marcus, arjun, sunita]
    for i, nm in enumerate(names):
        v = node(["Company", "Vendor"], f"V_N{i:02d}", name=f"{nm} Ltd", jurisdiction=random.choice(["US-OH", "IN", "DE", "MX"]),
                 tier=random.choice([1, 1, 2]))
        rel("SUPPLIES_TO", v, tgt, tier=1, componentCategory="GENERAL", annualSpendUSD=random.randint(2, 40) * 100_000)
        ag = node("Agreement", f"A_N{i:02d}", title=f"Supply Agreement - {nm}", type="SUPPLY",
                  effectiveDate=f"202{random.randint(0, 4)}-0{random.randint(1, 9)}-01",
                  expiryDate=f"202{random.randint(6, 9)}-12-31", totalValueUSD=random.randint(1, 20) * 500_000,
                  governingLaw=random.choice(["Delaware", "New York", "India"]))
        rel("AGREEMENT_OF", ag, tgt, role="BUYER")
        rel("AGREEMENT_OF", ag, v, role="SUPPLIER")
        for j, code in enumerate(random.sample(["CONFIDENTIALITY", "PAYMENT_TERMS", "GOVERNING_LAW"], 2)):
            c = node("Clause", f"CL_N{i:02d}_{j}", clauseType=code, title=code.title(), severity="LOW",
                     text=f"Standard {code.lower().replace('_', ' ')} provision.")
            rel("CLAUSE_OF", c, ag)
            rel("INSTANCE_OF", c, ct[code])
        t = node("Transaction", f"TX_N{i:02d}", type="PURCHASE", amountUSD=random.randint(1, 20) * 500_000,
                 date=f"2024-0{random.randint(1, 9)}-15", soleSource=False, description="Competitively bid purchase.")
        rel("IS_PART_OF", t, tgt)
        rel("UNDER_AGREEMENT", t, ag)
        rel("WITH_VENDOR", t, v)
        rel("APPROVED_BY", t, random.choice(approvers), date="2024-01-15")
        # regulatory filing layer
    node("RegulatoryFiling", "RF_HSR_DRAFT", type="HSR_PREMERGER_NOTIFICATION", filedWith="FTC/DOJ", status="NOT_FILED",
         description="HSR filing required; DoD novation / FOCI review also required for Northwind Defense Systems.")
    rel("FILING_FOR", ("RegulatoryFiling", "RF_HSR_DRAFT"), deal)

    # =============== ground truth ===============
    truth = [
        {"id": "GT1", "type": "UNDISCLOSED_RPT", "severity": "CRITICAL",
         "path": "Transaction TX_SILVER_AWARD -APPROVED_BY-> Arjun Raman -RELATED_TO(SPOUSE)- Priya Raman -HOLDS_STAKE_IN-> Meridian (BVI) -HOLDS_STAKE_IN-> Silverline",
         "indicativeExposureUSD": 15_000_000},
        {"id": "GT2", "type": "COC_POISON_PILL", "clause": "CL_COC_PILL_SILVER", "indicativeExposureUSD": 15_000_000},
        {"id": "GT3", "type": "COC_VENDOR_LOCKIN", "clause": "CL_COC_LOCK_SILVER", "indicativeExposureUSD": 21_000_000,
         "note": "4.2M x 5 yrs minimum purchase commitment (obligation, not pure loss)"},
        {"id": "GT4", "type": "DUAL_FIDUCIARY", "path": "Elena Voss -12%-> Quanta (tier-2) -SUPPLIES_TO-> Northwind; no disclosure",
         "indicativeExposureUSD": 1_800_000},
        {"id": "GT5", "type": "GOVERNANCE_ATTESTATION_FAILURE",
         "path": "Dana Whitfield attests none; spouse Tom Whitfield owns 35% of CoreStack (supplier)"},
        {"id": "GT6", "type": "AUTO_SLA_RENEWAL_IP_LOCKIN", "clause": "CL_SLA_CORE",
         "note": "Notice deadline 2026-10-17 already passed; renews 2027-01-15 for 36 months (~18M)",
         "indicativeExposureUSD": 18_000_000},
        {"id": "GT7", "type": "SOLE_SOURCE_EXCLUSIVITY", "clause": "CL_SOLE_ASIC", "indicativeExposureUSD": 22_000_000},
        {"id": "GT8", "type": "HORIZONTAL_MARKET_CAP",
         "path": "Helix Acquisition -SUBSIDIARY_OF-> Fund III <-SUBSIDIARY_OF- Orion (31% > 25%)", "valueAtRiskUSD": 120_000_000},
        {"id": "GT9", "type": "FEDERAL_CONTRACT_REVOCATION", "clause": "CL_REV_DOD",
         "path": "Fund III -9%-> Vanguard (named competitor)", "valueAtRiskUSD": 120_000_000},
        {"id": "DECOY_1", "expect": "NOT FLAGGED", "why": "Brightpath: CFO's spouse stake was declared"},
        {"id": "DECOY_2", "expect": "NOT FLAGGED", "why": "Atlas cap is 40% > Orion 31%"},
        {"id": "DECOY_3", "expect": "NOT A CoC FINDING", "why": "Brightpath clause is insolvency, not equity transfer"},
    ]

    if seed_risks:
        for g in truth:
            if "indicativeExposureUSD" in g or "valueAtRiskUSD" in g:
                r = node("RiskFactor", f"RISK_{g['id']}", category="SEEDED", subtype=g["type"],
                         severity=g.get("severity", "HIGH"), status="SEEDED_FOR_UI_TESTING",
                         deductionUSD=g.get("indicativeExposureUSD", 0))
                rel("HAS_CALCULATED_RISK", deal, r)
                rel("OF_TYPE", r, ct[g["type"]])
    return truth


# ----------------------------------------------------------------------------- loading
def constraint_statements():
    labels = sorted({l[0] for l, _ in NODES})
    st = [f"CREATE CONSTRAINT {l.lower()}_id IF NOT EXISTS FOR (n:{l}) REQUIRE n.id IS UNIQUE" for l in labels]
    st += ["CREATE INDEX company_name IF NOT EXISTS FOR (n:Company) ON (n.name)",
           "CREATE INDEX person_name IF NOT EXISTS FOR (n:Person) ON (n.name)",
           "CREATE INDEX clause_type IF NOT EXISTS FOR (n:Clause) ON (n.clauseType)",
           "CREATE FULLTEXT INDEX chunk_text IF NOT EXISTS FOR (n:DocumentChunk) ON EACH [n.text]",
           "CREATE FULLTEXT INDEX clause_text IF NOT EXISTS FOR (n:Clause) ON EACH [n.text, n.title]"]
    return st


def node_batches():
    g = defaultdict(list)
    for labels, props in NODES:
        g[labels].append({"id": props["id"], "props": props})
    out = []
    for labels, rows in g.items():
        extra = "".join(f":{x}" for x in labels[1:])
        q = f"UNWIND $rows AS r MERGE (n:{labels[0]} {{id: r.id}}) SET n += r.props" + (f" SET n{extra}" if extra else "")
        out.append((q, rows))
    return out


def rel_batches():
    g = defaultdict(list)
    for t, a, b, p in RELS:
        g[(t, a[0], b[0])].append({"a": a[1], "b": b[1], "props": p})
    return [(f"UNWIND $rows AS r MATCH (a:{fl} {{id: r.a}}) MATCH (b:{tl} {{id: r.b}}) "
             f"MERGE (a)-[x:{t}]->(b) SET x += r.props", rows) for (t, fl, tl), rows in g.items()]


def cy(v):
    """Python -> Cypher literal (for MCP emit mode)."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(cy(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"`{k}`: {cy(x)}" for k, x in v.items()) + "}"
    raise TypeError(v)


def chunks(rows, n):
    for i in range(0, len(rows), n):
        yield rows[i:i + n]


def emit(path):
    lines = ["// DealShield v2 load script - run each statement via Neo4j MCP write-cypher (or cypher-shell -f)"]
    lines += [s + ";" for s in constraint_statements()]
    for q, rows in node_batches() + rel_batches():
        for part in chunks(rows, 40):
            lines.append(q.replace("$rows", cy(part)) + ";")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {len(lines)} statements -> {path}")


VERIFY = [
    ("COI-1 undisclosed related-party sole-source (multi-hop)",
     """MATCH (tx:Transaction {soleSource:true})-[:APPROVED_BY]->(p:Person)-[:RELATED_TO]-(rp:Person),
              (rp)-[:HOLDS_STAKE_IN*1..3]->(v:Company)<-[:WITH_VENDOR]-(tx)
        WHERE NOT EXISTS { (p)-[:FILED]->(:Disclosure)-[:DECLARES]->(v) }
        RETURN p.name AS approver, rp.name AS relative, v.name AS vendor, tx.amountUSD AS amountUSD"""),
    ("COI-2 dual fiduciary (non-exec director, tier-2 vendor)",
     """MATCH (p:Person)-[:DIRECTOR_OF {type:'NON_EXECUTIVE'}]->(t:Target), (p)-[s:HOLDS_STAKE_IN]->(v:Company)-[:SUPPLIES_TO {tier:2}]->(t)
        WHERE NOT EXISTS { (p)-[:FILED]->(:Disclosure)-[:DECLARES]->(v) }
        RETURN p.name AS director, v.name AS vendor, s.pct AS stakePct"""),
    ("COI-3 governance attestation failure",
     """MATCH (p:Person)-[:DIRECTOR_OF]->(t:Target), (p)-[:FILED]->(d:Disclosure {attestsNoConflict:true}),
              (p)-[:RELATED_TO]-(r:Person)-[s:HOLDS_STAKE_IN]->(v:Company)-[:SUPPLIES_TO]->(t)
        WHERE NOT EXISTS { (d)-[:DECLARES]->(v) }
        RETURN p.name AS director, r.name AS relative, v.name AS supplier, s.pct AS pct"""),
    ("COC-1 triggered poison pills + lock-ins",
     """MATCH (d:Deal)-[:TARGET]->(t), (c:Clause)-[:CLAUSE_OF]->(:Agreement)-[:AGREEMENT_OF]->(t)
        WHERE c.clauseType IN ['COC_POISON_PILL','COC_VENDOR_LOCKIN'] AND c.triggerType='EQUITY_TRANSFER' AND d.equityTransferPct > c.thresholdPct
        RETURN c.clauseType AS type, c.penaltyUSD AS penalty, c.minAnnualPurchaseUSD * c.durationMonths / 12 AS lockInUSD"""),
    ("AT-1 common-parent cap breach",
     """MATCH (:Deal)-[:ACQUIRER]->(a)-[:IS_SUBSIDIARY_OF*1..3]->(par)<-[:IS_SUBSIDIARY_OF*1..3]-(sib)-[ms:HAS_MARKET_SHARE]->(m:Market)<-[:RESTRICTS_MARKET]-(c:Clause {clauseType:'HORIZONTAL_MARKET_CAP'})
        WHERE sib <> a AND ms.pct > c.thresholdPct
        RETURN c.id AS clause, sib.name AS sibling, ms.pct AS share, c.thresholdPct AS cap"""),
    ("AT-2 federal contract revocation (named competitor overlap)",
     """MATCH (:Deal)-[:ACQUIRER]->(a)-[:IS_SUBSIDIARY_OF*0..3]->(anc)-[s:HOLDS_STAKE_IN]->(comp:Company)<-[:NAMES_COMPETITOR]-(c:Clause)-[:REVOKES]->(g:GovContract)
        RETURN g.title AS contract, g.valueUSD AS valueAtRisk, comp.name AS competitor, anc.name AS holder, s.pct AS pct"""),
    ("NC-1 auto-renew SLA past notice window",
     """MATCH (d:Deal), (c:Clause {clauseType:'AUTO_SLA_RENEWAL_IP_LOCKIN'})
        WHERE c.noticeDeadline < d.announcedDate AND c.renewalDate <= d.expectedCloseDate
        RETURN c.id AS clause, c.noticeDeadline AS missedDeadline, c.renewalTermMonths AS lockMonths"""),
    ("NC-2 sole-source exclusivity",
     """MATCH (c:Clause {clauseType:'SOLE_SOURCE_EXCLUSIVITY'})-[:COVERS_COMPONENT]->(k:Component)
        RETURN c.id AS clause, k.name AS component, c.durationMonths AS months, c.penaltyUSD AS penalty"""),
]


def run_neo4j(args):
    from neo4j import GraphDatabase
    uri = os.environ["NEO4J_URI"]
    user = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME", "neo4j")
    drv = GraphDatabase.driver(uri, auth=(user, os.environ["NEO4J_PASSWORD"]))
    db = os.environ.get("NEO4J_DATABASE", "neo4j")
    with drv, drv.session(database=db) as s:
        if args.wipe:
            s.run("MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 5000 ROWS").consume()
            print("wiped database")
        for st in constraint_statements():
            s.run(st).consume()
        for q, rows in node_batches():
            for part in chunks(rows, 500):
                s.run(q, rows=part).consume()
        for q, rows in rel_batches():
            for part in chunks(rows, 500):
                s.run(q, rows=part).consume()
        print(f"loaded {len(NODES)} nodes, {len(RELS)} relationships")
        if args.verify:
            for name, q in VERIFY:
                recs = s.run(q).data()
                print(f"\n[{'OK ' if recs else 'EMPTY'}] {name}")
                for r in recs:
                    print("   ", r)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--wipe", action="store_true", help="delete everything first")
    ap.add_argument("--verify", action="store_true", help="run detection queries after load")
    ap.add_argument("--emit-cypher", metavar="FILE", help="write Cypher file instead of connecting (Neo4j MCP)")
    ap.add_argument("--seed-risks", action="store_true", help="pre-create RiskFactor nodes (UI testing only)")
    ap.add_argument("--truth", default="ground_truth.json")
    a = ap.parse_args()
    truth = build(a.seed_risks)
    json.dump(truth, open(a.truth, "w"), indent=2)
    print(f"built {len(NODES)} nodes / {len(RELS)} relationships; ground truth -> {a.truth}")
    if a.emit_cypher:
        emit(a.emit_cypher)
    else:
        run_neo4j(a)
