import os
import random
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURATION & ENTITY COUNTS
# ==============================================================================
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://<instance-id>.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "<your-password>")

# Adjust entity scale here
NUM_COMPANIES = 100          # Controls overall company count
NUM_EXECUTIVES = 140         # Directors, C-suite, and beneficial owners
NUM_CLAUSES = 60             # Legal contract clauses
NUM_DOC_CHUNKS = 50          # Raw contract chunks for GraphRAG
NUM_CONFLICT_RINGS = 3       # Multi-hop hidden related-party traps
BATCH_SIZE = 500

JURISDICTIONS = ["Delaware, USA", "California, USA", "Nevada, USA", "Texas, USA", "Cayman Islands", "BVI", "Germany", "UK", "Luxembourg"]
INDUSTRIES = ["Aerospace & Defense", "Semiconductors", "Cloud Infrastructure", "Enterprise SaaS", "Logistics", "Biotech"]
CLAUSE_TYPES = ["Change of Control", "Anti-Trust / Regulatory", "Exclusivity & Non-Compete", "Liquidated Damages", "IP Escrow"]

# ==============================================================================
# SYNTHETIC DATA GENERATOR
# ==============================================================================
def generate_dataset():
    random.seed(42)

    # 1. Primary Focal Entities
    companies = [
        {"id": "COMP-001", "name": "Horizon Private Equity", "role": "Acquirer", "jurisdiction": "Delaware, USA", "valuation_usd": 12000000000},
        {"id": "COMP-002", "name": "TargetTech Inc.", "role": "Acquisition Target", "jurisdiction": "California, USA", "valuation_usd": 450000000}
    ]

    # Generate remaining background companies (Suppliers, Shells, Competitors)
    roles = ["Tier-1 Supplier", "Tier-2 Supplier", "Holding Entity", "Direct Competitor", "Vendor"]
    for i in range(3, NUM_COMPANIES + 1):
        companies.append({
            "id": f"COMP-{i:03d}",
            "name": f"Enterprise-{i} {random.choice(['Technologies', 'Holdings', 'Logistics', 'Solutions', 'Corp', 'Systems'])}",
            "role": random.choice(roles),
            "jurisdiction": random.choice(JURISDICTIONS),
            "valuation_usd": random.randint(10000000, 300000000)
        })

    # 2. Subsidiaries (~30% of companies have subsidiaries)
    subsidiaries = []
    owns_sub_edges = []
    for i in range(1, int(NUM_COMPANIES * 0.35) + 1):
        sub_id = f"SUB-{i:03d}"
        parent_comp = companies[i % len(companies)]
        subsidiaries.append({
            "id": sub_id,
            "name": f"{parent_comp['name']} Division {chr(65 + (i % 26))}",
            "jurisdiction": random.choice(JURISDICTIONS)
        })
        owns_sub_edges.append({
            "from_company": parent_comp["id"],
            "to_sub": sub_id,
            "percentage": 100.0
        })

    # 3. Executives & Spouses
    executives = [
        {"id": "EXEC-001", "name": "Marcus Vance", "title": "Board Director & VP Procurement", "role_type": "Director", "disclosed_conflicts": "None"},
        {"id": "EXEC-002", "name": "Elena Rostova-Vance", "title": "Managing Partner (Spouse)", "role_type": "Spouse / Related Party", "disclosed_conflicts": "None"},
        {"id": "EXEC-003", "name": "Sarah Chen", "title": "Chief Executive Officer", "role_type": "Executive", "disclosed_conflicts": "None"}
    ]
    for i in range(4, NUM_EXECUTIVES + 1):
        executives.append({
            "id": f"EXEC-{i:03d}",
            "name": f"Executive_{i} {random.choice(['Smith', 'Zhang', 'Patel', 'Mueller', 'Rossi', 'Kim', 'Johansson'])}",
            "title": random.choice(["Board Director", "CFO", "VP of Operations", "Non-Executive Director", "General Counsel"]),
            "role_type": "Director" if i % 2 == 0 else "Executive",
            "disclosed_conflicts": "None"
        })

    # 4. Document Chunks & Clauses
    doc_chunks = [
        {
            "id": "DOC-CHUNK-101",
            "source_doc": "Master_Supply_Agreement_Apex_2025.pdf",
            "page": 14,
            "text": "Section 14.2 (Change of Control Penalty): If TargetTech Inc. undergoes a Change of Control (>50% equity transfer), TargetTech must either guarantee minimum annual purchases of $18.5M from Apex MicroSystems or pay an immediate $15M liquidated termination penalty."
        },
        {
            "id": "DOC-CHUNK-102",
            "source_doc": "Cayman_Beneficial_Ownership_Registry_Extract.pdf",
            "page": 3,
            "text": "Beneficial Ownership Filing #CY-88412: Elena Rostova-Vance (spouse of TargetTech Director Marcus Vance) holds a 42% controlling equity stake in Vanguard Pacific Holdings, which holds a 65% majority stake in Apex MicroSystems LLC."
        },
        {
            "id": "DOC-CHUNK-103",
            "source_doc": "TargetTech_Federal_DoD_Contract_88A.pdf",
            "page": 22,
            "text": "Clause 9.4 (Anti-Trust & Common Parent Cap): TargetTech Federal Solutions cannot share common ownership with any parent firm holding >25% defense market share, under penalty of immediate contract revocation ($45M revenue impact)."
        }
    ]
    for i in range(4, NUM_DOC_CHUNKS + 1):
        doc_chunks.append({
            "id": f"DOC-CHUNK-{i:03d}",
            "source_doc": f"Commercial_Agreement_Exhibit_{i}.pdf",
            "page": random.randint(1, 45),
            "text": f"Standard commercial covenant Section {i}.4: Party agrees to standard indemnification and SLA performance targets of 99.9% uptime, subject to liquidated damages of ${random.randint(1, 10)}M."
        })

    clauses = [
        {"id": "CL-402", "title": "Change-of-Control Poison Pill", "clause_type": "Change of Control", "financial_exposure_usd": 15000000, "summary": "$15M penalty or mandatory vendor lock-in triggered by buyout."},
        {"id": "CL-819", "title": "DoD Anti-Trust Restriction", "clause_type": "Anti-Trust / Regulatory", "financial_exposure_usd": 45000000, "summary": "Revokes $45M defense contract if Acquirer holds >25% market share."},
        {"id": "CL-205", "title": "Board Attestation Breach", "clause_type": "Governance / Fraud", "financial_exposure_usd": 18500000, "summary": "False disclosure hiding spouse beneficial ownership in sole-source vendor."}
    ]
    for i in range(4, NUM_CLAUSES + 1):
        clauses.append({
            "id": f"CL-{i:03d}",
            "title": f"Covenant {i}: {random.choice(CLAUSE_TYPES)}",
            "clause_type": random.choice(CLAUSE_TYPES),
            "financial_exposure_usd": random.randint(500000, 20000000),
            "summary": f"Standard contractual liability governing performance, termination, and regulatory caps."
        })

    # 5. Risk Factors
    risk_factors = [
        {"id": "RISK-001", "category": "Undisclosed Related-Party Transaction", "severity": "CRITICAL", "description": "Director Marcus Vance approved an $18.5M sole-source contract with $15M penalty to Apex MicroSystems, secretly owned by his spouse."},
        {"id": "RISK-002", "category": "Anti-Trust & Regulatory Conflict", "severity": "HIGH", "description": "Buyout triggers revocation of $45M DoD contract due to Acquirer market share overlap."},
        {"id": "RISK-003", "category": "Governance Attestation Failure", "severity": "MEDIUM", "description": "Failure to report related-party supplier interests in annual director conflict disclosure."}
    ]

    # ==============================================================================
    # RELATIONSHIP BUILDERS (Core Graph Topology)
    # ==============================================================================
    director_edges = []
    supplies_edges = []
    holds_stake_edges = []
    restricted_by_edges = []
    extracted_from_edges = []

    # Focal M&A Deal
    holds_stake_edges.append({"from_id": "COMP-001", "to_id": "COMP-002", "percentage": 100.0, "status": "Proposed Buyout"})

    # --- SMOKING GUN CONFLICT RINGS ---
    # Ring 1: Marcus Vance -> Elena Rostova-Vance -> Vanguard Pacific (COMP-004) -> Apex (COMP-003) -> TargetTech (COMP-002)
    companies[2]["name"] = "Apex MicroSystems LLC"
    companies[2]["role"] = "Tier-1 Supplier"
    companies[3]["name"] = "Vanguard Pacific Holdings"
    companies[3]["role"] = "Holding Entity"
    companies[3]["jurisdiction"] = "Cayman Islands"

    director_edges.append({"exec_id": "EXEC-001", "comp_id": "COMP-002", "role": "Director & VP Procurement"})
    director_edges.append({"exec_id": "EXEC-001", "comp_id": "EXEC-002", "role": "Spouse / Related Party"})
    holds_stake_edges.append({"from_id": "EXEC-002", "to_id": "COMP-004", "percentage": 42.0, "status": "Beneficial Owner"})
    holds_stake_edges.append({"from_id": "COMP-004", "to_id": "COMP-003", "percentage": 65.0, "status": "Majority Stake"})
    supplies_edges.append({"from_id": "COMP-003", "to_id": "COMP-002", "annual_value_usd": 18500000, "criticality": "Sole-Source ASIC"})

    # Link Ring 1 to Clauses & RiskFactors & Raw Chunks
    restricted_by_edges.append({"from_id": "COMP-002", "to_id": "CL-402"})
    restricted_by_edges.append({"from_id": "COMP-003", "to_id": "CL-402"})
    restricted_by_edges.append({"from_id": "CL-402", "to_id": "RISK-001"})
    extracted_from_edges.append({"from_id": "CL-402", "to_id": "DOC-CHUNK-101"})
    extracted_from_edges.append({"from_id": "RISK-001", "to_id": "DOC-CHUNK-101"})
    extracted_from_edges.append({"from_id": "RISK-001", "to_id": "DOC-CHUNK-102"})

    # Ring 2 & 3: Additional hidden rings across random companies
    for r in range(2, NUM_CONFLICT_RINGS + 1):
        c_sup = companies[4 + r]["id"]
        c_hold = companies[8 + r]["id"]
        e_dir = executives[3 + r]["id"]
        e_sp = executives[7 + r]["id"]
        executives[7 + r]["role_type"] = "Spouse / Related Party"

        director_edges.append({"exec_id": e_dir, "comp_id": "COMP-002", "role": "Director"})
        director_edges.append({"exec_id": e_dir, "comp_id": e_sp, "role": "Spouse / Immediate Family"})
        holds_stake_edges.append({"from_id": e_sp, "to_id": c_hold, "percentage": 35.0, "status": "Beneficial Owner"})
        holds_stake_edges.append({"from_id": c_hold, "to_id": c_sup, "percentage": 51.0, "status": "Majority Stake"})
        supplies_edges.append({"from_id": c_sup, "to_id": "COMP-002", "annual_value_usd": 7500000, "criticality": "Critical Vendor"})

    # Background Graph Connectivity (Normal commercial noise across the 100 companies)
    for i in range(10, NUM_COMPANIES):
        # Assign 1-2 directors per company
        director_edges.append({
            "exec_id": executives[i % len(executives)]["id"],
            "comp_id": companies[i]["id"],
            "role": "Director"
        })
        # Supply chain edges (random vendor links)
        if i % 3 == 0:
            supplies_edges.append({
                "from_id": companies[i]["id"],
                "to_id": "COMP-002",
                "annual_value_usd": random.randint(1000000, 12000000),
                "criticality": "Standard Supplier"
            })
        elif i % 2 == 0:
            supplies_edges.append({
                "from_id": companies[i]["id"],
                "to_id": companies[(i + 3) % NUM_COMPANIES]["id"],
                "annual_value_usd": random.randint(500000, 6000000),
                "criticality": "Secondary Vendor"
            })

    # Link remaining clauses to companies & doc chunks
    for i in range(3, min(len(clauses), len(doc_chunks))):
        c_id = clauses[i]["id"]
        chunk_id = doc_chunks[i]["id"]
        comp_id = companies[i % len(companies)]["id"]
        restricted_by_edges.append({"from_id": comp_id, "to_id": c_id})
        extracted_from_edges.append({"from_id": c_id, "to_id": chunk_id})

    return {
        "companies": companies,
        "subsidiaries": subsidiaries,
        "executives": executives,
        "clauses": clauses,
        "doc_chunks": doc_chunks,
        "risk_factors": risk_factors,
        "owns_sub_edges": owns_sub_edges,
        "director_edges": director_edges,
        "supplies_edges": supplies_edges,
        "holds_stake_edges": holds_stake_edges,
        "restricted_by_edges": restricted_by_edges,
        "extracted_from_edges": extracted_from_edges
    }

# ==============================================================================
# NEO4J AURA LOADER
# ==============================================================================
def chunk_list(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

def run_cypher_batch(session, query, batch):
    session.run(query, {"batch": batch})

def seed_database():
    print(f"Connecting to Neo4j Aura: {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    dataset = generate_dataset()

    with driver.session() as session:
        print("Creating uniqueness constraints & indexes...")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE;")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Subsidiary) REQUIRE s.id IS UNIQUE;")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Executive) REQUIRE e.id IS UNIQUE;")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (cl:Clause) REQUIRE cl.id IS UNIQUE;")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:DocumentChunk) REQUIRE d.id IS UNIQUE;")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:RiskFactor) REQUIRE r.id IS UNIQUE;")

        print(f"Loading {len(dataset['companies'])} Companies...")
        for batch in chunk_list(dataset["companies"], BATCH_SIZE):
            run_cypher_batch(session, """
                UNWIND $batch AS row
                MERGE (c:Company {id: row.id})
                SET c.name = row.name, c.role = row.role, c.jurisdiction = row.jurisdiction, c.valuation_usd = row.valuation_usd
            """, batch)

        print(f"Loading {len(dataset['subsidiaries'])} Subsidiaries...")
        for batch in chunk_list(dataset["subsidiaries"], BATCH_SIZE):
            run_cypher_batch(session, """
                UNWIND $batch AS row
                MERGE (s:Subsidiary {id: row.id})
                SET s.name = row.name, s.jurisdiction = row.jurisdiction
            """, batch)

        print(f"Loading {len(dataset['executives'])} Executives & Related Parties...")
        for batch in chunk_list(dataset["executives"], BATCH_SIZE):
            run_cypher_batch(session, """
                UNWIND $batch AS row
                MERGE (e:Executive {id: row.id})
                SET e.name = row.name, e.title = row.title, e.role_type = row.role_type, e.disclosed_conflicts = row.disclosed_conflicts
            """, batch)

        print(f"Loading {len(dataset['clauses'])} Clauses...")
        for batch in chunk_list(dataset["clauses"], BATCH_SIZE):
            run_cypher_batch(session, """
                UNWIND $batch AS row
                MERGE (cl:Clause {id: row.id})
                SET cl.title = row.title, cl.clause_type = row.clause_type, cl.financial_exposure_usd = row.financial_exposure_usd, cl.summary = row.summary
            """, batch)

        print(f"Loading {len(dataset['doc_chunks'])} DocumentChunks...")
        for batch in chunk_list(dataset["doc_chunks"], BATCH_SIZE):
            run_cypher_batch(session, """
                UNWIND $batch AS row
                MERGE (d:DocumentChunk {id: row.id})
                SET d.source_doc = row.source_doc, d.page = row.page, d.text = row.text
            """, batch)

        print(f"Loading {len(dataset['risk_factors'])} RiskFactors...")
        for batch in chunk_list(dataset["risk_factors"], BATCH_SIZE):
            run_cypher_batch(session, """
                UNWIND $batch AS row
                MERGE (r:RiskFactor {id: row.id})
                SET r.category = row.category, r.severity = row.severity, r.description = row.description
            """, batch)

        print("Writing Graph Relationships...")
        # OWNS_SUBSIDIARY
        for batch in chunk_list(dataset["owns_sub_edges"], BATCH_SIZE):
            run_cypher_batch(session, """
                UNWIND $batch AS row
                MATCH (c:Company {id: row.from_company}), (s:Subsidiary {id: row.to_sub})
                MERGE (c)-[:OWNS_SUBSIDIARY {percentage: row.percentage}]->(s)
            """, batch)

        # DIRECTOR_OF
        for batch in chunk_list(dataset["director_edges"], BATCH_SIZE):
            run_cypher_batch(session, """
                UNWIND $batch AS row
                MATCH (e:Executive {id: row.exec_id})
                OPTIONAL MATCH (c:Company {id: row.comp_id})
                OPTIONAL MATCH (sp:Executive {id: row.comp_id})
                FOREACH (_ IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (e)-[:DIRECTOR_OF {role: row.role}]->(c)
                )
                FOREACH (_ IN CASE WHEN sp IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (e)-[:DIRECTOR_OF {role: row.role}]->(sp)
                )
            """, batch)

        # SUPPLIES_TO
        for batch in chunk_list(dataset["supplies_edges"], BATCH_SIZE):
            run_cypher_batch(session, """
                UNWIND $batch AS row
                MATCH (s:Company {id: row.from_id}), (t:Company {id: row.to_id})
                MERGE (s)-[:SUPPLIES_TO {annual_value_usd: row.annual_value_usd, criticality: row.criticality}]->(t)
            """, batch)

        # HOLDS_STAKE_IN
        for batch in chunk_list(dataset["holds_stake_edges"], BATCH_SIZE):
            run_cypher_batch(session, """
                UNWIND $batch AS row
                MATCH (target:Company {id: row.to_id})
                OPTIONAL MATCH (from_comp:Company {id: row.from_id})
                OPTIONAL MATCH (from_exec:Executive {id: row.from_id})
                FOREACH (_ IN CASE WHEN from_comp IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (from_comp)-[:HOLDS_STAKE_IN {percentage: row.percentage, status: row.status}]->(target)
                )
                FOREACH (_ IN CASE WHEN from_exec IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (from_exec)-[:HOLDS_STAKE_IN {percentage: row.percentage, status: row.status}]->(target)
                )
            """, batch)

        # RESTRICTED_BY & EXTRACTED_FROM
        for batch in chunk_list(dataset["restricted_by_edges"], BATCH_SIZE):
            run_cypher_batch(session, """
                UNWIND $batch AS row
                MATCH (n {id: row.from_id}), (m {id: row.to_id})
                MERGE (n)-[:RESTRICTED_BY]->(m)
            """, batch)

        for batch in chunk_list(dataset["extracted_from_edges"], BATCH_SIZE):
            run_cypher_batch(session, """
                UNWIND $batch AS row
                MATCH (n {id: row.from_id}), (m:DocumentChunk {id: row.to_id})
                MERGE (n)-[:EXTRACTED_FROM]->(m)
            """, batch)

    driver.close()
    print("\nDealShield Knowledge Graph Seeded Successfully in Neo4j Aura Cloud!")

if __name__ == "__main__":
    seed_database()