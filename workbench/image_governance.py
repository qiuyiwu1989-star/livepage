"""Reviewed representative expression selection; never alters source occurrences."""
import json
from pathlib import Path

def representative_override(root, atom_id):
    path=Path(root)/'data/representative-image-overrides.json'
    if not path.exists():return None
    return json.loads(path.read_text()).get('overrides',{}).get(atom_id)

def source_override(root, slide_id):
    path=Path(root)/'data/source-image-overrides.json'
    if not path.exists():return None
    return json.loads(path.read_text()).get('overrides',{}).get(slide_id)
