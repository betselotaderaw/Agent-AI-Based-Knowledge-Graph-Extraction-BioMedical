import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv
from typing import List, Dict, Optional, Tuple, Set
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

# Load environment variables
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

SAMPLE_RELATIONSHIPS = [
    {"source": "pulmonary nocardiosis", "relation": "affects", "target": "respiratory"},
    {"source": "nocardiosis", "relation": "causes", "target": "infection"},
    {"source": "aerosol route", "relation": "associates_with", "target": "nocardia infection"},
    {"source": "molecular techniques", "relation": "diagnoses", "target": "nocardia infection"},
    {"source": "small nodule", "relation": "associates_with", "target": "nocardiosis"}
]

class EnhancedNeo4jGraph:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._ensure_constraints()
        print("✅ Successfully connected to Neo4j")

    def close(self):
        self.driver.close()

    def _ensure_constraints(self):
        with self.driver.session() as session:
            session.run("""
            CREATE CONSTRAINT unique_entity IF NOT EXISTS 
            FOR (e:Entity) REQUIRE e.name IS UNIQUE
            """)
            session.run("""
            CREATE CONSTRAINT unique_paper IF NOT EXISTS
            FOR (p:Paper) REQUIRE p.name IS UNIQUE
            """)

    def query(self, cypher: str, params: Optional[Dict] = None) -> List[Dict]:
        try:
            with self.driver.session() as session:
                result = session.run(cypher, params or {})
                return [dict(record) for record in result]
        except Exception as e:
            print(f"⚠️ Query error: {str(e)}")
            return []

# Initialize services
try:
    graph = EnhancedNeo4jGraph(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    llm = OllamaLLM(model="mistral:latest", temperature=0.3)
except Exception as e:
    print(f"❌ Initialization error: {str(e)}")
    exit(1)

def load_entity_labels() -> Dict[str, str]:
    try:
        with open("./output/cleaned_entities.json") as f:
            return {e['text'].lower(): e['label'] for e in json.load(f)}
    except Exception as e:
        print(f"⚠️ Error loading entity labels: {str(e)}")
        return {}

entity_labels = load_entity_labels()

def initialize_graph(relationships: List[Dict], paper_name: str = "BCR"):
    graph.query("""
    MERGE (p:Paper {name: $name})
    SET p.last_updated = datetime()
    """, {"name": paper_name})

    for rel in relationships:
        source = rel['source'].lower()
        target = rel['target'].lower()

        graph.query("""
        MERGE (a:Entity {name: $source})
        SET a.label = $source_label
        MERGE (a)-[:MENTIONED_IN]->(:Paper {name: $paper})

        MERGE (b:Entity {name: $target})
        SET b.label = $target_label
        MERGE (b)-[:MENTIONED_IN]->(:Paper {name: $paper})

        MERGE (a)-[r:RELATED_TO {type: $relation}]->(b)
        SET r.added_on = datetime()
        """, {
            "source": rel['source'],
            "target": rel['target'],
            "relation": rel['relation'],
            "paper": paper_name,
            "source_label": entity_labels.get(source, "unknown"),
            "target_label": entity_labels.get(target, "unknown")
        })

def get_graph_data(limit: int = 100) -> Tuple[List[Dict], Set[str], Set[str]]:
    query = """
    MATCH (a:Entity)-[r:RELATED_TO]->(b:Entity)
    OPTIONAL MATCH (a)-[:MENTIONED_IN]->(pa:Paper)
    OPTIONAL MATCH (b)-[:MENTIONED_IN]->(pb:Paper)
    RETURN DISTINCT a.name AS source, 
           COALESCE(a.label, 'unknown') AS source_label,
           type(r) AS relation, 
           b.name AS target, 
           COALESCE(b.label, 'unknown') AS target_label,
           [x IN collect(DISTINCT pa.name) WHERE x IS NOT NULL] + 
           [x IN collect(DISTINCT pb.name) WHERE x IS NOT NULL] AS papers
    LIMIT $limit
    """
    records = graph.query(query, {"limit": limit})

    entity_types = set()
    papers = set()

    for r in records:
        if r.get("source_label"):
            entity_types.add(r["source_label"])
        if r.get("target_label"):
            entity_types.add(r["target_label"])
        if r.get("papers"):
            papers.update(r["papers"])

    return records, papers, entity_types

def generate_context(relationships: List[Dict]) -> str:
    return "\n".join(
        f"{r['source']} ({r.get('source_label', '?')}) "
        f"--{r['relation']}--> "
        f"{r['target']} ({r.get('target_label', '?')}) "
        f"[source: {', '.join(sorted(set(r.get('papers', []))))}]"
        for r in relationships
    )

qa_prompt = PromptTemplate.from_template("""
You are a biomedical knowledge graph assistant with these capabilities:

Available Entity Types: {entity_types}

Knowledge Graph Relationships:
{graph_data}

Guidelines:
1. Be precise and cite sources when available
2. Use entity types when relevant
3. If unsure, say "I don't have information about this"

Question: {question}

Answer format:
<answer> [source: {papers}]
""")

def answer_question(question: str) -> str:
    try:
        relationships, papers, entity_types = get_graph_data()
        if not relationships:
            return "No graph data available"

        response = (qa_prompt | llm).invoke({
            "graph_data": generate_context(relationships),
            "papers": ", ".join(sorted(papers)) if papers else "multiple sources",
            "entity_types": ", ".join(sorted(entity_types)),
            "question": question
        })

        return response.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def main_loop():
    print("\n🔬 Biomedical Knowledge Graph QA System")
    print("Commands: 'exit', 'graph', 'types'")

    initialize_graph(SAMPLE_RELATIONSHIPS)

    while True:
        try:
            user_input = input("\nYour question/command: ").strip()

            if not user_input:
                continue

            if user_input.lower() == 'exit':
                break

            if user_input.lower() == 'graph':
                data, _, _ = get_graph_data(limit=10)
                print("\nCurrent Relationships:")
                for rel in data:
                    print(f"{rel['source']} --{rel['relation']}--> {rel['target']} [source: {', '.join(rel.get('papers', []))}]")
                continue

            if user_input.lower() == 'types':
                _, _, types = get_graph_data()
                print("\nEntity Types:")
                for t in sorted(types):
                    print(f"- {t}")
                continue

            answer = answer_question(user_input)
            print(f"\n💡 {answer}")

        except KeyboardInterrupt:
            print("\nExiting...")
            break

if __name__ == "__main__":
    try:
        main_loop()
    finally:
        graph.close()