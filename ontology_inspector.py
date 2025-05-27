import pickle
from collections import defaultdict
from pathlib import Path
from rdflib import Graph, URIRef
from rdflib.namespace import RDFS, SKOS

class NCItInspector:
    def __init__(self, owl_path="./ncit/Cancer_Thesaurus.owl"):
        self.g = Graph()
        self.g.parse(owl_path)
        
    def build_and_save_indexes(self, output_path="ncit_indexes.pkl"):
        """Build and save all required indexes"""
        print("Building indexes...")
        
        # Entity index {name: [C12345, ...]}
        entity_index = defaultdict(list)
        for s, _, o in self.g.triples((None, RDFS.label | SKOS.altLabel, None)):
            entity_index[str(o).lower()].append(str(s).split("#C")[-1])
        
        # Relationship index {(C12345,C67890): [A1, P107]}
        rel_index = defaultdict(set)
        predicate_labels = {}
        
        for s, p, o in self.g:
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                s_id = str(s).split("#C")[-1]
                o_id = str(o).split("#C")[-1]
                p_code = str(p).split("#")[-1]
                rel_index[(s_id, o_id)].add(p_code)
                
                # Store predicate labels
                if p_code not in predicate_labels:
                    label = next(self.g.objects(p, RDFS.label), "")
                    predicate_labels[p_code] = str(label)

        # Save all indexes
        with open(output_path, 'wb') as f:
            pickle.dump({
                'entity_index': dict(entity_index),
                'rel_index': dict(rel_index),
                'predicate_labels': predicate_labels
            }, f)
        
        print(f"Saved indexes to {output_path}")

if __name__ == "__main__":
    inspector = NCItInspector()
    inspector.build_and_save_indexes()