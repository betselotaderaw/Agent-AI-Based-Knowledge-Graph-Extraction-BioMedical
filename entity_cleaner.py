import json
import re
from collections import defaultdict

def clean_entities(input_file, cleaned_output, final_output, score_threshold=0.85):
    # Step 1: Load entities
    with open(input_file, 'r') as f:
        entities = json.load(f)

    # Cleaning pipeline
    cleaned = []
    seen = set()
    
    for entity in entities:
        # Remove Nonbiological_location and Lab_value entities
        if entity['label'] in ['Nonbiological_location', 'Lab_value', 'Date']:
            continue
            
        # Apply confidence threshold
        if entity['score'] < score_threshold:
            continue
            
        # Initial text cleaning
        text = entity['text'].strip()

        # Fix hyphenated words (replace " - " with "")
        text = re.sub(r'\s*-\s*', '', text)  # "non - rebreating" → "nonrebreating"
        
        # Remove special symbols (arrows, colons, etc.)
        text = re.sub(r'[\u25b6\u25b8\u25c0\u25c2:;]', '', text).strip()
        
        # Skip pure numbers/dates/ordinals
        if re.fullmatch(r'^[\d\s,.-]+(th|st|nd|rd)?$', text):
            continue
        
        # Skip single characters
        if len(text) == 1:
            continue
            
        # Skip "empty" entities after cleaning
        if not text or text in [':', 't', 'x']:  # Explicit unwanted cases
            continue
            
        # Handle number-prefixed entities
        text = re.sub(r'^\d+[\s-]', '', text).strip()  # "7 linezolid" → "linezolid"
        text = re.sub(r'\d+[sS]?\s', '', text)         # "16s rna gene" → "rna gene"
        
        # Final validation
        if not text or any(text.lower() == bad for bad in [': : 30', ':', 'x', 't']):
            continue
            
        # Case-insensitive deduplication (preserve original capitalization)
        key = (text.lower(), entity['label'])
        if key not in seen:
            seen.add(key)
            cleaned.append({
                'text': text,
                'label': entity['label'],
                'score': round(float(entity['score']), 4)
            })

    # Save outputs
    with open(cleaned_output, 'w') as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
    
    with open(final_output, 'w') as f:
        json.dump([e['text'] for e in cleaned], f, indent=2, ensure_ascii=False)

    # Statistics
    print(f"Original: {len(entities)} entities")
    print(f"Cleaned: {len(cleaned)} entities")
    print(f"Removed {len(entities) - len(cleaned)} invalid entries")

if __name__ == "__main__":
    clean_entities(
        input_file="output/extracted_entities.json",
        cleaned_output="output/cleaned_entities.json",
        final_output="output/final_entities.json",
        score_threshold=0.88
    )