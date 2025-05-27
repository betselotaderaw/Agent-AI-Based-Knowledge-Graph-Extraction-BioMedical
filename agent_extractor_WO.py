# ner_extractor.py
import json
import torch
import os
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from nltk.tokenize import sent_tokenize

# Configuration
MODEL_NAME = "d4data/biomedical-ner-all"
PDF_CLEANED_PATH = "./dataset/cleaned_papers/"
OUTPUT_PATH = "./output/"
SPECIFIC_FILE = "shua.txt"  # The cleaned text file corresponding to bcr.pdf

def initialize_pipeline():
    """Initialize the NER pipeline with proper settings"""
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)
    
    return pipeline(
        "ner",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="max",
        device="cuda:0" if torch.cuda.is_available() else -1
    )

def extract_text_from_cleaned_file(filename):
    """Read text from cleaned text file"""
    try:
        with open(os.path.join(PDF_CLEANED_PATH, filename), 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"⚠️ Error reading cleaned file: {e}")
        return ""

def process_text_chunk(nlp, text_chunk):
    """Process a text chunk with error handling"""
    try:
        return nlp(text_chunk)
    except Exception as e:
        print(f"⚠️ Error processing text chunk: {e}")
        return []

def extract_entities(nlp, text):
    """Robust entity extraction with proper text chunking"""
    if not text:
        return []
    
    try:
        sentences = sent_tokenize(text)
    except LookupError:
        print("❌ NLTK resources missing. Please run setup_nltk.py first.")
        return []
    
    entities = []
    
    for sent in sentences:
        tokens = tokenizer.tokenize(sent)
        if len(tokens) > 500:
            # Split long sentences into chunks
            words = sent.split()
            chunk_size = 400  # Conservative word count
            chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
            for chunk in chunks:
                entities.extend(process_text_chunk(nlp, chunk))
        else:
            entities.extend(process_text_chunk(nlp, sent))
    
    # Filter and format results
    return [
        {"label": ent["entity_group"], "text": ent["word"], "score": float(ent["score"])}
        for ent in entities if ent["score"] >= 0.7
    ]

def process_specific_file(nlp, filename):
    """Process a specific cleaned text file"""
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    
    print(f"🔍 Processing {filename}...")
    text = extract_text_from_cleaned_file(filename)
    entities = extract_entities(nlp, text)
    
    output_filename = 'extracted_entities.json'
    output_filepath = os.path.join(OUTPUT_PATH, output_filename)
    
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(entities, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Extracted {len(entities)} entities to {output_filename}")

if __name__ == "__main__":
    # Initialize pipeline
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    nlp = initialize_pipeline()
    
    # Process specific file
    process_specific_file(nlp, SPECIFIC_FILE)