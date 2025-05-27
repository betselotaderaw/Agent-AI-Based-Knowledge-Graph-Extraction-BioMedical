import json
import pickle
from collections import defaultdict
from tqdm import tqdm

class NCItValidator:
    def __init__(self, index_path="ncit_indexes.pkl"):
        with open(index_path, 'rb') as f:
            data = pickle.load(f)
        
        self.entity_index = data['entity_index']
        self.rel_index = data['rel_index']
        self.predicate_labels = data.get('predicate_labels', {})
        
        print(f"Loaded {len(self.entity_index)} entities and {len(self.rel_index)} relationships")

    def resolve_entity(self, term):
        """Return list of NCIt IDs (C-numbers)"""
        return self.entity_index.get(term.lower(), [])

    def find_relationships(self, source_id, target_id, requested_relation=None):
        """Find all relationships between two entities"""
        relationships = []
        requested_relation = requested_relation.lower() if requested_relation else None
        
        # Check all relationships between these entities
        for (s, t), preds in self.rel_index.items():
            if s == source_id and t == target_id:
                for pred in preds:
                    pred_label = self.predicate_labels.get(pred, "").lower()
                    is_requested = (requested_relation and 
                                   (requested_relation == pred.lower() or 
                                    requested_relation in pred_label))
                    
                    relationships.append({
                        "code": pred,
                        "label": self.predicate_labels.get(pred, ""),
                        "is_requested_relation": is_requested
                    })
        
        return relationships

def validate(input_path, output_path):
    validator = NCItValidator()
    
    with open(input_path) as f:
        extractions = json.load(f)
    
    results = []
    for rel in tqdm(extractions, desc="Validating"):
        source_ids = validator.resolve_entity(rel['source'])
        target_ids = validator.resolve_entity(rel['target'])
        
        result = {
            "source": rel['source'],
            "target": rel['target'],
            "requested_relation": rel['relation'],
            "source_ids": source_ids,
            "target_ids": target_ids,
            "valid_entities": bool(source_ids and target_ids),
            "requested_relation_found": False,
            "all_relationships": []
        }
        
        if source_ids and target_ids:
            for src_id in source_ids:
                for tgt_id in target_ids:
                    relationships = validator.find_relationships(
                        src_id, tgt_id, rel['relation'])
                    
                    if relationships:
                        result['all_relationships'].extend([{
                            "source_id": src_id,
                            "target_id": tgt_id,
                            **r
                        } for r in relationships])
                        
                        # Check if requested relation exists
                        if any(r['is_requested_relation'] for r in relationships):
                            result['requested_relation_found'] = True
        
        results.append(result)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Saved results to {output_path}")

if __name__ == "__main__":
    validate(
        input_path="./output/extracted_relationships.json",
        output_path="./output/validated_relationships.json"
    )