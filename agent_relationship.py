import json
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
import PyPDF2
from pathlib import Path
import re

SPECIFIC_FILE = "shua.txt"

def read_pdf(file_path):
    """Read text content from a PDF file."""
    text = ""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        raise ValueError(f"Failed to read PDF file: {str(e)}")
    return text.strip()

# Initialize Ollama with Mistral (lower temperature for more precise outputs)
llm = OllamaLLM(model="llama3.3:latest", 
    stop=["<Think>", "</Think>", "<|im_end|>"]) #, temperature=0.3

# Enhanced prompt with spelling tolerance but same output format
relationship_extraction_prompt =  PromptTemplate.from_template("""
Analyze this biomedical text and extract precise relationships between entities with scientific rigor.
The text may contain technical terminology and entity names with minor variations - use contextual understanding to match them.

Return ONLY a valid JSON array following this exact schema:
[{{
  "source": "EntityName (normalized form)",
  "relation": "SpecificBiomedicalRelation",
  "target": "EntityName (normalized form)",
}}]

Text: {text}
Entities: {entities}

Focus on these biomedical relationship types (ordered by priority):
1. Molecular interactions: binds_to, inhibits, activates, phosphorylates, regulates_expression_of
2. Pharmacological: treats, contraindicates, metabolizes, potentiates, side_effect_of
3. Diagnostic: diagnoses, biomarker_for, prognostic_indicator_of
4. Pathological: causes, predisposes_to, complication_of, manifestation_of
5. Genetic: associated_with, variant_of, encodes, coexpressed_with
6. Anatomical: located_in, part_of, connected_to

Extraction rules:
Rules:
- Only extract relationships explicitly stated in the text
- For ambiguous cases, prefer more specific relationship types
- Split compound entities into separate relationships
- Try to find for every entities a relationships but never extract relationships not supported by the text 


Example Output:
[
  {{
    "source": "metformin",
    "relation": "inhibits",
    "target": "mTORC1"
   }},
  {{
    "source": "BRCA1",
    "relation": "associated_with",
    "target": "breast cancer",
    }}
]

Output ONLY the JSON array with no additional commentary:
""")

relationship_chain = relationship_extraction_prompt | llm

def extract_relationships(text, entities):
    """Extract relationships while maintaining original format."""
    try:
        response = relationship_chain.invoke({
            "text": text,  # Truncate very long papers
            "entities": json.dumps(entities)
        })
        print(response)
        # Extract JSON array from response
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON array found in response")
        
        relationships = json.loads(json_match.group(0))
        
        # Validate and maintain original format
        valid_relationships = []
        for rel in relationships:
            if all(key in rel for key in ["source", "relation", "target"]):
                valid_relationships.append({
                    "source": rel["source"],
                    "relation": rel["relation"],
                    "target": rel["target"]
                })
        return valid_relationships
        
    except Exception as e:
        print(f"Error in extraction: {str(e)}")
        return []
def read_text_file(file_path):
    """Read content from a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise ValueError(f"Failed to read text file: {str(e)}")

def main():
    output_dir = Path("./output")
    cleaned_papers_dir = Path("./dataset/cleaned_papers")  # Changed from research_papers
    
    # Load final entities (unchanged)
    entities_path = output_dir / "final_entities.json"
    try:
        with open(entities_path, "r") as f:
            entities = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load entities: {str(e)}")

    # Changed from reading PDF to reading TXT
    text_file_path = cleaned_papers_dir / SPECIFIC_FILE  # Hardcoded as before
    try:
        research_text = read_text_file(text_file_path)  # Using new text reader
    except Exception as e:
        raise ValueError(f"Failed to read text file: {str(e)}")

    # Rest of the code remains EXACTLY the same...
    relationships = extract_relationships(research_text, entities)
    
    output_path = output_dir / "extracted_relationships.json"
    with open(output_path, "w") as f:
        json.dump(relationships, f, indent=2)
    
    print(f"Successfully extracted {len(relationships)} relationships")

if __name__ == "__main__":
    main()