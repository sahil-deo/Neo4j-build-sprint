#!/usr/bin/env python3
"""
DealShield - GOLDEN SCENARIOS, two isolated subgraphs, same ontology.

  Subgraph A  "Project Aegis"   (:Golden:GoldenA, ids GA_*)   Use cases 1+2: Conflict of Interest + Change of Control
      Helix Acquisition Corp (acquirer) -> Northwind Microsystems (target)
      Silverline Components Ltd (conflicted vendor) + Meridian Holdings Ltd BVI (offshore ownership link)

  Subgraph B  "Project Vector"  (:Golden:GoldenB, ids GB_*)   Use cases 3+4: Anti-Trust/Regulatory + Non-Compete/Exclusivity
      Orion Defense Electronics (acquirer) -> Aurora Sensor Technologies (target)
      Hsinchu ASIC Works (sole-source supplier) + CoreStack Cloud Services (auto-renewing SLA provider)

No relationship connects A to B, or either to any other data in the database.

USAGE
  # Bolt / Aura   (loads from .env automatically via python-dotenv)
  python dealshield_golden_v2.py --wipe-golden --verify

  # Neo4j MCP: emit Cypher, then run each statement through the MCP write-cypher tool
  python dealshield_golden_v2.py --emit-cypher golden_load.cypher

  --only A | B     build just one subgraph
  --seed-risks     pre-create RiskFactor nodes (UI testing only; the agent normally writes these)
"""
import argparse, json, os
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

NODES, RELS, _seen, _n = [], [], set(), [0]
CUR = {"tag": None, "p": None}


def node(labels, nid, **props):
    labels = ((labels,) if isinstance(labels, str) else tuple(labels)) + ("Golden", CUR["tag"])
    assert (labels[0], nid) not in _seen, f"duplicate {nid}"
    _seen.add((labels[0], nid))
    props = {k: v for k, v in props.items() if v is not None}
    NODES.append((labels, {"id": nid, "scenario": CUR["tag"].upper().replace("GOLDEN", "GOLDEN_"), **props}))
    return (labels[0], nid)


def rel(t, a, b, **p):
    RELS.append((t, a, b, {k: v for k, v in p.items() if v is not None}))


def evidence(ref, doc, page, text, conf=0.97):
    _n[0] += 1
    ch = node("DocumentChunk", f"{CUR['p']}CH{_n[0]:02d}", text=text, page=page, docId=doc[1], chunkIndex=_n[0])
    rel("HAS_CHUNK", doc, ch)
    rel("DERIVED_FROM", ref, ch, confidence=conf, page=page)


def doc(i, title, src, pages):
    return node("Document", i, title=title, source=src, pages=pages)


def agreement(i, tgt, cp, title, typ, eff, exp, val, law, role_t, role_c):
    a = node("Agreement", i, title=title, type=typ, effectiveDate=eff, expiryDate=exp, totalValueUSD=val, governingLaw=law)
    rel("AGREEMENT_OF", a, tgt, role=role_t)
    if cp:
        rel("AGREEMENT_OF", a, cp, role=role_c)
    return a


def clause(i, agr, d, page, **p):
    c = node("Clause", i, **p)
    rel("CLAUSE_OF", c, agr)
    evidence(c, d, page, p.get("text", "")[:240])
    return c


def transaction(i, tgt, agr, vendor, approver, **p):
    t = node("Transaction", i, **p)
    rel("IS_PART_OF", t, tgt)
    rel("UNDER_AGREEMENT", t, agr)
    rel("WITH_VENDOR", t, vendor)
    rel("APPROVED_BY", t, approver, date=p.get("date"))
    return t


# ============================================================================================
# SUBGRAPH A - Conflict of Interest + Change of Control
# ============================================================================================
def build_a(seed_risks):
    CUR.update(tag="GoldenA", p="GA_")
    d_msa = doc("GA_DOC_MSA", "Master Supply Agreement - Northwind / Silverline", "CONTRACT", 84)
    d_mca = doc("GA_DOC_MCA", "MCA Public Search - Silverline Shareholding & Director Extract", "MCA_PUBLIC_SEARCH", 9)
    d_bvi = doc("GA_DOC_BVI", "BVI Beneficial Ownership Registry Extract - Meridian Holdings", "REGULATORY_FILING", 14)
    d_cor = doc("GA_DOC_CORP", "Northwind Corporate Filings - FY2025 Director/Officer Conflict Disclosures", "CORPORATE_FILING", 22)
    d_brd = doc("GA_DOC_BOARD", "Northwind Board Roster & Delegation of Authority", "BOARD_ROSTER", 6)
    d_xls = doc("GA_DOC_XLS", "Northwind Vendor Spend Register (Excel export)", "EXCEL_FIGURES", 12)

    acq = node(["Company", "Acquirer"], "GA_ACQ", name="Helix Acquisition Corp", jurisdiction="US-DE", type="SPV")
    tgt = node(["Company", "Target"], "GA_TGT", name="Northwind Microsystems Inc.", jurisdiction="US-DE", type="OPERATING",
               revenueUSD=412_000_000, incorporationDate="2004-03-11")
    vnd = node(["Company", "Vendor"], "GA_VND", name="Silverline Components Ltd", jurisdiction="IN", type="OPERATING",
               cin="U31900PN2014PLC152233", tier=2)
    mer = node(["Company", "Offshore", "Shell"], "GA_MERIDIAN", name="Meridian Holdings Ltd", jurisdiction="BVI",
               type="HOLDING", isOffshore=True, isShell=True)
    evidence(vnd, d_mca, 3, "Silverline Components Ltd: shareholders - Meridian Holdings Ltd (BVI) 70%, E. R. Voss 12%, T. Whitfield 8%, others 10%.")
    evidence(mer, d_bvi, 5, "Meridian Holdings Ltd (BVI): sole beneficial owner Priya Raman (100%).")
    evidence(vnd, d_xls, 2, "FY2025 vendor spend register: Silverline Components Ltd - USD 9.6M, sole-source flag = Y.")

    deal = node("Deal", "GA_DEAL", name="Project Aegis", dealValueUSD=850_000_000, equityTransferPct=100.0,
                announcedDate="2026-10-12", diligenceDate="2026-10-30", expectedCloseDate="2027-01-31", status="DILIGENCE")
    rel("ACQUIRER", deal, acq)
    rel("TARGET", deal, tgt)
    rf = node("RegulatoryFiling", "GA_RF_HSR", type="HSR_PREMERGER_NOTIFICATION", filedWith="FTC/DOJ", status="NOT_FILED",
              description="HSR notification required for USD 850M acquisition.")
    rel("FILING_FOR", rf, deal)

    arjun = node("Person", "GA_ARJUN", name="Arjun Raman", nationality="IN")
    priya = node("Person", "GA_PRIYA", name="Priya Raman", nationality="IN")
    dana = node("Person", "GA_DANA", name="Dana Whitfield", nationality="US")
    tom = node("Person", "GA_TOM", name="Tom Whitfield", nationality="US")
    elena = node("Person", "GA_ELENA", name="Elena Voss", nationality="US")
    rel("WORKS_AT", arjun, tgt, title="VP Procurement", department="Procurement", since="2018-07-01", approvalLimitUSD=60_000_000)
    rel("DIRECTOR_OF", dana, tgt, type="NON_EXECUTIVE", committee="AUDIT_CHAIR", since="2019-05-01")
    rel("DIRECTOR_OF", elena, tgt, type="NON_EXECUTIVE", committee="PROCUREMENT_CHAIR", since="2020-09-01")
    rel("RELATED_TO", priya, arjun, relation="SPOUSE", verified=True, source="MCA_PUBLIC_SEARCH")
    rel("RELATED_TO", tom, dana, relation="SPOUSE", verified=True, source="CORPORATE_FILING")
    evidence(arjun, d_brd, 2, "Arjun Raman, VP Procurement: delegated authority to award sole-source contracts up to USD 60M.")
    evidence(priya, d_mca, 4, "Priya Raman: spouse of Arjun Raman (Northwind employee), per MCA director KYC cross-reference.")
    evidence(dana, d_brd, 3, "Dana Whitfield - Independent Director, Audit Committee Chair.")
    evidence(elena, d_brd, 4, "Elena Voss - Independent Director, Chair of Procurement Committee.")

    rel("HOLDS_STAKE_IN", priya, mer, pct=100.0, type="BENEFICIAL", since="2019-03-01")
    rel("HOLDS_STAKE_IN", mer, vnd, pct=70.0, type="DIRECT", since="2019-03-05")
    rel("HOLDS_STAKE_IN", elena, vnd, pct=12.0, type="DIRECT", since="2021-04-01")
    rel("HOLDS_STAKE_IN", tom, vnd, pct=8.0, type="DIRECT", since="2020-08-15")
    rel("SUPPLIES_TO", vnd, tgt, tier=2, componentCategory="PCB_ASSEMBLY", annualSpendUSD=9_600_000)
    evidence(elena, d_cor, 17, "Cap-table extract (Silverline): Elena R. Voss 12.0% - acquired 2021-04-01.")
    evidence(tom, d_cor, 18, "Cap-table extract (Silverline): Thomas Whitfield 8.0% - acquired 2020-08-15.")

    # disclosures: filed, but nothing DECLARED (no DECLARES edge) -> baseline for "undisclosed"
    for p, pg in ((arjun, 4), (dana, 5), (elena, 6)):
        d = node("Disclosure", f"GA_DISC_{p[1][3:]}", year=2025, type="ANNUAL_CONFLICT_DISCLOSURE",
                 attestsNoConflict=True, filedDate="2026-02-20")
        rel("FILED", p, d)
        evidence(d, d_cor, pg, f"{p[1]} attests: 'I and my immediate family have no interest in any supplier of the Company.'")

    a_msa = agreement("GA_A_MSA", tgt, vnd, "Master Supply Agreement - Silverline", "MSA", "2023-04-01", "2028-03-31",
                      48_000_000, "Delaware", "BUYER", "SUPPLIER")
    clause("GA_CL_COC_PILL", a_msa, d_msa, 47, clauseType="COC_POISON_PILL", section="14.3",
           title="Termination Fee on Change of Control",
           text="Upon any transfer of more than 50% of the voting equity of Buyer, Supplier may terminate this Agreement and Buyer shall pay a liquidated sum of USD 15,000,000 within 30 days.",
           triggerType="EQUITY_TRANSFER", thresholdPct=50.0, penaltyUSD=15_000_000, severity="HIGH")
    clause("GA_CL_COC_LOCK", a_msa, d_msa, 48, clauseType="COC_VENDOR_LOCKIN", section="14.5",
           title="Post-CoC Minimum Purchase Commitment",
           text="Following a Change of Control, Buyer shall purchase not less than USD 4,200,000 per year from Supplier for a period of 60 months.",
           triggerType="EQUITY_TRANSFER", thresholdPct=50.0, minAnnualPurchaseUSD=4_200_000, durationMonths=60, severity="HIGH")

    t1 = transaction("GA_TX_AWARD", tgt, a_msa, vnd, arjun, type="SOLE_SOURCE_AWARD", amountUSD=48_000_000, date="2023-03-20",
                     soleSource=True, description="Sole-source award of the Silverline master supply program; no competitive bid.")
    rel("APPROVED_BY", t1, arjun, withinAuthority=True)
    evidence(t1, d_msa, 2, "Approved by Arjun Raman, VP Procurement. Justification recorded: 'incumbent supplier, no alternate bids'.")
    b1 = node("Benefit", "GA_BEN_PILL", type="TERMINATION_FEE", amountUSD=15_000_000,
              description="USD 15M liquidated fee payable to Silverline on change of control.")
    b2 = node("Benefit", "GA_BEN_LOCK", type="GUARANTEED_REVENUE", amountUSD=21_000_000,
              description="USD 4.2M x 5 years guaranteed minimum purchases.")
    rel("HAS_BENEFIT", t1, b1)
    rel("HAS_BENEFIT", t1, b2)
    rel("ACCRUES_TO", b1, vnd, sharePct=100.0)
    rel("ACCRUES_TO", b2, vnd, sharePct=100.0)
    rel("ACCRUES_TO", b1, priya, sharePct=70.0, indirect=True, via="Meridian Holdings Ltd")
    rel("ACCRUES_TO", b1, elena, sharePct=12.0, indirect=True, via="Silverline equity")
    rel("ACCRUES_TO", b1, tom, sharePct=8.0, indirect=True, via="Silverline equity")
    t2 = transaction("GA_TX_RENEWAL_FEE", tgt, a_msa, vnd, elena, type="RENEWAL_FEE", amountUSD=1_800_000, date="2025-11-10",
                     soleSource=False, description="12% fee uplift on annual renewal approved by the Procurement Committee.")
    rel("APPROVED_BY", t2, elena, role="PROCUREMENT_COMMITTEE_CHAIR")
    evidence(t2, d_msa, 61, "Minutes 10-Nov-2025: renewal fee uplift of USD 1.8M approved; chair E. Voss did not recuse.")

    truth = [
        {"subgraph": "A", "useCase": "CONFLICT_OF_INTEREST", "id": "GA-1A", "type": "UNDISCLOSED_RPT", "severity": "CRITICAL",
         "path": "GA_TX_AWARD -APPROVED_BY-> Arjun Raman -RELATED_TO(SPOUSE)- Priya Raman -HOLDS_STAKE_IN(100%)-> Meridian (BVI) -HOLDS_STAKE_IN(70%)-> Silverline",
         "indicativeExposureUSD": 48_000_000},
        {"subgraph": "A", "useCase": "CONFLICT_OF_INTEREST", "id": "GA-1B", "type": "GOVERNANCE_ATTESTATION_FAILURE",
         "path": "Dana Whitfield attests no conflict; spouse Tom Whitfield holds 8% of supplier Silverline"},
        {"subgraph": "A", "useCase": "CONFLICT_OF_INTEREST", "id": "GA-1C", "type": "DUAL_FIDUCIARY",
         "path": "Elena Voss (NED, Procurement Chair) holds 12% of tier-2 vendor Silverline and approved the 1.8M renewal fee",
         "indicativeExposureUSD": 1_800_000},
        {"subgraph": "A", "useCase": "CHANGE_OF_CONTROL", "id": "GA-2A", "type": "COC_POISON_PILL", "clause": "GA_CL_COC_PILL",
         "indicativeExposureUSD": 15_000_000, "insiderLookThroughPct": 90},
        {"subgraph": "A", "useCase": "CHANGE_OF_CONTROL", "id": "GA-2B", "type": "COC_VENDOR_LOCKIN", "clause": "GA_CL_COC_LOCK",
         "indicativeExposureUSD": 21_000_000, "note": "obligation (4.2M x 5y), not pure loss"},
    ]
    if seed_risks:
        seed(deal, truth, "GA_RISK_")
    return truth


# ============================================================================================
# SUBGRAPH B - Anti-Trust & Regulatory + Non-Compete & Exclusivity
# ============================================================================================
def build_b(seed_risks):
    CUR.update(tag="GoldenB", p="GB_")
    d_dod = doc("GB_DOC_DOD", "DoD Contract N00-ARP-2025-0142 + Ownership Covenant Annex", "CONTRACT", 120)
    d_asic = doc("GB_DOC_ASIC", "ASIC Exclusive Supply Agreement - Aurora / Hsinchu", "CONTRACT", 66)
    d_sla = doc("GB_DOC_SLA", "SLA & IP License Addendum - Aurora / CoreStack", "CONTRACT", 37)
    d_xls = doc("GB_DOC_XLS", "Airborne Radar Market Share Figures (Excel export)", "EXCEL_FIGURES", 12)
    d_reg = doc("GB_DOC_REG", "FTC/DOJ Pre-Merger Screening Memo - Project Vector", "REGULATORY_FILING", 18)
    d_brd = doc("GB_DOC_BOARD", "Aurora Officer Roster & Delegation of Authority", "BOARD_ROSTER", 4)

    acq = node(["Company", "Acquirer"], "GB_ACQ", name="Orion Defense Electronics Inc.", jurisdiction="US-VA", type="OPERATING",
               revenueUSD=2_900_000_000)
    tgt = node(["Company", "Target"], "GB_TGT", name="Aurora Sensor Technologies Inc.", jurisdiction="US-CA", type="OPERATING",
               revenueUSD=265_000_000, incorporationDate="2009-06-22")
    asicv = node(["Company", "Vendor"], "GB_HSINCHU", name="Hsinchu ASIC Works Co. Ltd", jurisdiction="TW", type="OPERATING", tier=1)
    core = node(["Company", "Vendor"], "GB_CORESTACK", name="CoreStack Cloud Services Inc.", jurisdiction="US-WA", type="OPERATING", tier=1)

    deal = node("Deal", "GB_DEAL", name="Project Vector", dealValueUSD=640_000_000, equityTransferPct=100.0,
                announcedDate="2026-10-05", diligenceDate="2026-10-30", expectedCloseDate="2027-02-28", status="DILIGENCE",
                combinedSharePct=40.0, hhiDelta=558.0)
    rel("ACQUIRER", deal, acq)
    rel("TARGET", deal, tgt)
    rf = node("RegulatoryFiling", "GB_RF_HSR", type="HSR_PREMERGER_NOTIFICATION", filedWith="FTC/DOJ", status="NOT_FILED",
              description="HSR notification required; DoD consent / novation review required for the radar contract.")
    rel("FILING_FOR", rf, deal)
    evidence(rf, d_reg, 3, "Screening memo: combined share 40.0% in Airborne Radar Signal Processing; HHI delta 558; second request likely.")

    # a clean control person: approves transactions, no stakes, no relatives -> COI queries must stay empty in B
    meera = node("Person", "GB_MEERA", name="Meera Iyer", nationality="IN")
    rel("WORKS_AT", meera, tgt, title="Chief Procurement Officer", department="Procurement", since="2017-03-01",
        approvalLimitUSD=80_000_000)
    d = node("Disclosure", "GB_DISC_MEERA", year=2025, type="ANNUAL_CONFLICT_DISCLOSURE", attestsNoConflict=True, filedDate="2026-02-18")
    rel("FILED", meera, d)
    evidence(meera, d_brd, 2, "Meera Iyer, CPO: delegated authority up to USD 80M; no related-party interests on file.")

    # ---------------- use case 3: anti-trust & regulatory
    mkt = node("Market", "GB_M_RADAR", name="Airborne Radar Signal Processing", sector="DEFENSE", naics="334511")
    rel("HAS_MARKET_SHARE", acq, mkt, pct=31.0, year=2025, source="EXCEL_FIGURES")
    rel("HAS_MARKET_SHARE", tgt, mkt, pct=9.0, year=2025, source="EXCEL_FIGURES")
    evidence(acq, d_xls, 7, "Orion Defense Electronics holds 31.0% of Airborne Radar Signal Processing (FY2025); Aurora 9.0%.")
    gc = node("GovContract", "GB_GC_DOD", agency="Department of Defense", title="Airborne Radar Processing Production",
              contractNo="N00-ARP-2025-0142", valueUSD=85_000_000, awardDate="2025-03-31")
    rel("AWARDED_TO", gc, tgt)
    a_dod = agreement("GB_A_DOD", tgt, None, "DoD Contract N00-ARP-2025-0142 - Ownership Covenant Annex", "GOV_CONTRACT",
                      "2025-03-31", "2030-03-30", 85_000_000, "US-Federal", "CONTRACTOR", None)
    c_cap = clause("GB_CL_CAP", a_dod, d_dod, 88, clauseType="HORIZONTAL_MARKET_CAP", section="H.12",
                   title="Common Parent Restriction",
                   text="Contractor shall not share a common parent with, or be controlled by, any entity holding more than 25% share of the Airborne Radar Signal Processing market.",
                   thresholdPct=25.0, severity="CRITICAL")
    rel("RESTRICTS_MARKET", c_cap, mkt)
    c_rev = clause("GB_CL_REVOKE", a_dod, d_dod, 89, clauseType="FEDERAL_CONTRACT_REVOCATION", section="H.14",
                   title="Automatic Revocation on Competitor Overlap",
                   text="This contract is revoked automatically and immediately upon acquisition of the Contractor by Orion Defense Electronics Inc. (named direct competitor) or by any entity exceeding the market share limit in H.12.",
                   thresholdPct=25.0, automatic=True, valueAtRiskUSD=85_000_000, severity="CRITICAL")
    rel("RESTRICTS_MARKET", c_rev, mkt)
    rel("NAMES_COMPETITOR", c_rev, acq)
    rel("REVOKES", c_rev, gc)

    # ---------------- use case 4: non-compete & exclusivity
    asic = node("Component", "GB_COMP_ASIC", name="AR-5nm Radar ASIC", type="ASIC", criticality="CRITICAL")
    rel("SUPPLIES_TO", asicv, tgt, tier=1, componentCategory="ASIC", annualSpendUSD=9_000_000)
    rel("SUPPLIES_COMPONENT", asicv, asic, sole=True)
    rel("SUPPLIES_TO", core, tgt, tier=1, componentCategory="CLOUD_EDA", annualSpendUSD=6_000_000)
    a_asic = agreement("GB_A_ASIC", tgt, asicv, "ASIC Exclusive Supply Agreement", "SUPPLY", "2024-07-01", "2031-06-30",
                       63_000_000, "Singapore", "BUYER", "SUPPLIER")
    c_ss = clause("GB_CL_SOLE_ASIC", a_asic, d_asic, 29, clauseType="SOLE_SOURCE_EXCLUSIVITY", section="6.1",
                  title="Exclusive Purchasing - 5nm Radar ASIC",
                  text="Buyer shall purchase 100% of its requirements for the AR-5nm Radar ASIC exclusively from Supplier for 84 months. Shortfall below USD 9,000,000 per annum is payable as take-or-pay. Breach of exclusivity carries a penalty of USD 22,000,000, and this section survives any change of control of Buyer.",
                  durationMonths=84, minAnnualPurchaseUSD=9_000_000, penaltyUSD=22_000_000, exclusivityPct=100.0,
                  survivesChangeOfControl=True, severity="CRITICAL")
    rel("COVERS_COMPONENT", c_ss, asic)
    a_sla = agreement("GB_A_SLA", tgt, core, "SLA & IP License Addendum", "SLA", "2023-01-15", "2027-01-15",
                      18_000_000, "Washington", "CUSTOMER", "PROVIDER")
    clause("GB_CL_SLA", a_sla, d_sla, 21, clauseType="AUTO_SLA_RENEWAL_IP_LOCKIN", section="9.2",
           title="Automatic Renewal & Exclusive IP Toolchain License",
           text="The SLA renews automatically for successive 36-month terms unless Customer gives written notice at least 90 days before the renewal date. During any term Customer shall not migrate Supplier-licensed IP libraries or firmware to a third-party provider.",
           autoRenew=True, renewalTermMonths=36, noticeDays=90, renewalDate="2027-01-15", noticeDeadline="2026-10-17",
           annualFeeUSD=6_000_000, exitPenaltyUSD=4_500_000, severity="HIGH")
    t1 = transaction("GB_TX_ASIC", tgt, a_asic, asicv, meera, type="SOLE_SOURCE_AWARD", amountUSD=63_000_000, date="2024-06-10",
                     soleSource=True, description="Seven-year sole-source ASIC award; single qualified foundry.")
    t2 = transaction("GB_TX_SLA", tgt, a_sla, core, meera, type="SLA_RENEWAL", amountUSD=18_000_000, date="2022-12-20",
                     soleSource=False, description="Three-year SLA and IP license.")
    b1 = node("Benefit", "GB_BEN_TOP", type="TAKE_OR_PAY_REVENUE", amountUSD=63_000_000,
              description="USD 9M x 7 years guaranteed minimum purchases.")
    b2 = node("Benefit", "GB_BEN_RENEW", type="AUTO_RENEWAL_REVENUE", amountUSD=18_000_000,
              description="36-month renewal at USD 6M per year.")
    rel("HAS_BENEFIT", t1, b1)
    rel("HAS_BENEFIT", t2, b2)
    rel("ACCRUES_TO", b1, asicv, sharePct=100.0)
    rel("ACCRUES_TO", b2, core, sharePct=100.0)

    truth = [
        {"subgraph": "B", "useCase": "ANTITRUST_REGULATORY", "id": "GB-3A", "type": "HORIZONTAL_MARKET_CAP", "clause": "GB_CL_CAP",
         "path": "Orion (31%) > 25% cap; becomes Aurora's parent at close", "valueAtRiskUSD": 85_000_000},
        {"subgraph": "B", "useCase": "ANTITRUST_REGULATORY", "id": "GB-3B", "type": "FEDERAL_CONTRACT_REVOCATION", "clause": "GB_CL_REVOKE",
         "path": "Clause names Orion as direct competitor; Orion is the acquirer", "valueAtRiskUSD": 85_000_000},
        {"subgraph": "B", "useCase": "NONCOMPETE_EXCLUSIVITY", "id": "GB-4A", "type": "SOLE_SOURCE_EXCLUSIVITY", "clause": "GB_CL_SOLE_ASIC",
         "indicativeExposureUSD": 22_000_000},
        {"subgraph": "B", "useCase": "NONCOMPETE_EXCLUSIVITY", "id": "GB-4B", "type": "AUTO_SLA_RENEWAL_IP_LOCKIN", "clause": "GB_CL_SLA",
         "note": "notice deadline 2026-10-17 missed; renews 2027-01-15 for 36 months before closing 2027-02-28",
         "indicativeExposureUSD": 18_000_000},
        {"subgraph": "B", "expect": "NO conflict-of-interest or change-of-control findings (negative control)"},
    ]
    if seed_risks:
        seed(deal, truth, "GB_RISK_")
    return truth


def seed(deal, truth, prefix):
    for g in truth:
        if "type" in g:
            r = node("RiskFactor", prefix + g["id"], category=g["useCase"], subtype=g["type"], status="SEEDED_FOR_UI_TESTING",
                     deductionUSD=g.get("indicativeExposureUSD", g.get("valueAtRiskUSD", 0)))
            rel("HAS_CALCULATED_RISK", deal, r)


# ============================================================================================
# loading
# ============================================================================================
def constraints():
    labels = sorted({l[0] for l, _ in NODES})
    return [f"CREATE CONSTRAINT {l.lower()}_id IF NOT EXISTS FOR (n:{l}) REQUIRE n.id IS UNIQUE" for l in labels] + [
        "CREATE FULLTEXT INDEX chunk_text IF NOT EXISTS FOR (n:DocumentChunk) ON EACH [n.text]",
        "CREATE FULLTEXT INDEX clause_text IF NOT EXISTS FOR (n:Clause) ON EACH [n.text, n.title]"]


def node_batches():
    g = defaultdict(list)
    for labels, props in NODES:
        g[labels].append({"id": props["id"], "props": props})
    return [(f"UNWIND $rows AS r MERGE (n:{l[0]} {{id: r.id}}) SET n += r.props SET n{''.join(':' + x for x in l[1:])}", rows)
            for l, rows in g.items()]


def rel_batches():
    g = defaultdict(list)
    for t, a, b, p in RELS:
        g[(t, a[0], b[0])].append({"a": a[1], "b": b[1], "props": p})
    return [(f"UNWIND $rows AS r MATCH (a:{fl} {{id: r.a}}) MATCH (b:{tl} {{id: r.b}}) MERGE (a)-[x:{t}]->(b) SET x += r.props", rows)
            for (t, fl, tl), rows in g.items()]


def cy(v):
    if v is None: return "null"
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, (int, float)): return repr(v)
    if isinstance(v, str): return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (list, tuple)): return "[" + ", ".join(cy(x) for x in v) + "]"
    if isinstance(v, dict): return "{" + ", ".join(f"`{k}`: {cy(x)}" for k, x in v.items()) + "}"
    raise TypeError(v)


def emit(path):
    lines = ["// DealShield GOLDEN subgraphs A+B - run each statement via Neo4j MCP write-cypher (or cypher-shell -f)"]
    lines += [s + ";" for s in constraints()]
    for q, rows in node_batches() + rel_batches():
        for i in range(0, len(rows), 40):
            lines.append(q.replace("$rows", cy(rows[i:i + 40])) + ";")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"wrote {len(lines)} statements -> {path}")


# (name, cypher with @T placeholder for the subgraph label, subgraph label, expectation)
Q = {
    "iso": "MATCH (a:@T)--(b) WHERE NOT b:@T RETURN count(*) AS leaks",
    "1A": """MATCH (tx:@T:Transaction {soleSource:true})-[:APPROVED_BY]->(p:Person)-[:RELATED_TO]-(rp:Person)-[:HOLDS_STAKE_IN*1..3]->(v:Company)<-[:WITH_VENDOR]-(tx)
             WHERE NOT EXISTS { (p)-[:FILED]->(:Disclosure)-[:DECLARES]->(v) }
             RETURN p.name AS approver, rp.name AS spouse, v.name AS vendor, tx.amountUSD AS amountUSD""",
    "1B": """MATCH (p:@T:Person)-[:DIRECTOR_OF]->(t:Target), (p)-[:FILED]->(d:Disclosure {attestsNoConflict:true}),
                   (p)-[:RELATED_TO]-(r:Person)-[s:HOLDS_STAKE_IN]->(v:Company)-[:SUPPLIES_TO]->(t)
             WHERE NOT EXISTS { (d)-[:DECLARES]->(v) }
             RETURN p.name AS director, r.name AS relative, v.name AS supplier, s.pct AS stakePct""",
    "1C": """MATCH (p:@T:Person)-[:DIRECTOR_OF {type:'NON_EXECUTIVE'}]->(t:Target), (p)-[s:HOLDS_STAKE_IN]->(v:Company)-[:SUPPLIES_TO {tier:2}]->(t)
             WHERE NOT EXISTS { (p)-[:FILED]->(:Disclosure)-[:DECLARES]->(v) }
             OPTIONAL MATCH (tx:Transaction)-[:APPROVED_BY]->(p) WHERE (tx)-[:WITH_VENDOR]->(v)
             RETURN p.name AS director, v.name AS vendor, s.pct AS stakePct, collect(tx.amountUSD) AS approvedAmounts""",
    "2": """MATCH (d:@T:Deal)-[:TARGET]->(t), (c:Clause)-[:CLAUSE_OF]->(:Agreement)-[:AGREEMENT_OF]->(t)
            WHERE c.triggerType = 'EQUITY_TRANSFER' AND d.equityTransferPct > c.thresholdPct
            RETURN c.clauseType AS type, c.penaltyUSD AS penaltyUSD, c.minAnnualPurchaseUSD * c.durationMonths / 12 AS lockInUSD""",
    "2+": """MATCH (:@T:Benefit {type:'TERMINATION_FEE'})-[a:ACCRUES_TO]->(x:Person)
             RETURN x.name AS insider, a.sharePct AS pct ORDER BY pct DESC""",
    "3A": """MATCH (:@T:Deal)-[:ACQUIRER]->(acq)-[ms:HAS_MARKET_SHARE]->(m:Market)<-[:RESTRICTS_MARKET]-(c:Clause {clauseType:'HORIZONTAL_MARKET_CAP'})
             WHERE ms.pct > c.thresholdPct
             RETURN acq.name AS acquirer, ms.pct AS sharePct, c.thresholdPct AS capPct, c.id AS clause""",
    "3B": """MATCH (:@T:Deal)-[:ACQUIRER]->(acq)<-[:NAMES_COMPETITOR]-(c:Clause)-[:REVOKES]->(g:GovContract)
             RETURN g.title AS contract, g.valueUSD AS valueAtRiskUSD, acq.name AS namedCompetitor""",
    "4A": """MATCH (c:@T:Clause {clauseType:'SOLE_SOURCE_EXCLUSIVITY'})-[:COVERS_COMPONENT]->(k:Component)
             RETURN c.id AS clause, k.name AS component, c.durationMonths AS months, c.penaltyUSD AS penaltyUSD, c.survivesChangeOfControl AS survivesCoC""",
    "4B": """MATCH (d:@T:Deal), (c:Clause {clauseType:'AUTO_SLA_RENEWAL_IP_LOCKIN'})
             WHERE c.noticeDeadline < d.diligenceDate AND c.renewalDate <= d.expectedCloseDate
             RETURN c.id AS clause, c.noticeDeadline AS missedDeadline, c.renewalDate AS renewsOn, c.renewalTermMonths AS lockMonths""",
}
VERIFY = [("A isolation (leaks must be 0)", "iso", "GoldenA", "zero"), ("B isolation (leaks must be 0)", "iso", "GoldenB", "zero"),
          ("A  1A undisclosed related-party sole-source (4-hop)", "1A", "GoldenA", "rows"),
          ("A  1B governance attestation failure", "1B", "GoldenA", "rows"),
          ("A  1C dual-fiduciary director", "1C", "GoldenA", "rows"),
          ("A  2  triggered CoC clauses", "2", "GoldenA", "rows"),
          ("A  2+ insider look-through of CoC fee", "2+", "GoldenA", "rows"),
          ("A  negative control: no antitrust in A (3A)", "3A", "GoldenA", "none"),
          ("A  negative control: no exclusivity in A (4A)", "4A", "GoldenA", "none"),
          ("B  3A common-parent market cap breached", "3A", "GoldenB", "rows"),
          ("B  3B federal contract revocation", "3B", "GoldenB", "rows"),
          ("B  4A sole-source exclusivity survives CoC", "4A", "GoldenB", "rows"),
          ("B  4B auto-renew SLA past notice window", "4B", "GoldenB", "rows"),
          ("B  negative control: no related-party award (1A)", "1A", "GoldenB", "none"),
          ("B  negative control: no director conflicts (1B)", "1B", "GoldenB", "none"),
          ("B  negative control: no CoC triggers (2)", "2", "GoldenB", "none")]


def run_neo4j(a, tags):
    from neo4j import GraphDatabase
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not uri or not password:
        raise ValueError("Missing NEO4J_URI or NEO4J_PASSWORD. Please check your .env file or environment variables.")

    drv = GraphDatabase.driver(uri, auth=(user, password))
    with drv, drv.session(database=database) as s:
        if a.wipe_golden:
            for t in tags:
                s.run(f"MATCH (n:{t}) DETACH DELETE n").consume()
            print("removed existing:", ", ".join(tags))
        for st in constraints():
            s.run(st).consume()
        for q, rows in node_batches() + rel_batches():
            s.run(q, rows=rows).consume()
        print(f"loaded {len(NODES)} nodes, {len(RELS)} relationships")
        if a.verify:
            for name, key, tag, expect in VERIFY:
                if tag not in tags:
                    continue
                recs = s.run(Q[key].replace("@T", tag)).data()
                if expect == "zero":
                    ok = bool(recs) and recs[0].get("leaks", -1) == 0
                elif expect == "rows":
                    ok = bool(recs)
                elif expect == "none":
                    ok = not recs
                else:
                    ok = False
                print(f"\n[{'OK' if ok else 'FAIL'}] {name}")
                for r in recs:
                    print("   ", r)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["A", "B"])
    ap.add_argument("--wipe-golden", action="store_true", help="delete existing nodes of the subgraph(s) being built")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--emit-cypher", metavar="FILE")
    ap.add_argument("--seed-risks", action="store_true")
    ap.add_argument("--truth", default="golden_ground_truth.json")
    a = ap.parse_args()
    truth, tags = [], []
    if a.only in (None, "A"):
        truth += build_a(a.seed_risks); tags.append("GoldenA")
    if a.only in (None, "B"):
        truth += build_b(a.seed_risks); tags.append("GoldenB")
    json.dump(truth, open(a.truth, "w"), indent=2)
    print(f"built {len(NODES)} nodes / {len(RELS)} relationships ({'+'.join(tags)}); ground truth -> {a.truth}")
    emit(a.emit_cypher) if a.emit_cypher else run_neo4j(a, tags)
