"""Render the original long-form bus lesson without any cloud calls."""
import json
from pathlib import Path

from render_proof import ROOT, measured

spec = json.loads((ROOT / 'examples' / 'bus-read-long.json').read_text(encoding='utf-8'))
manifest, measurements = measured(spec, 'bus-long', ROOT / 'examples' / 'render-cache-long')
assert 600 <= manifest['duration_seconds'] <= 1200, 'Actual lesson must be 10–20 minutes'
assert len(manifest['scenes']) == 12, 'All twelve original teaching scenes must survive assembly'
assert manifest['scenes'][0]['start_seconds'] == 0
for left, right in zip(manifest['scenes'], manifest['scenes'][1:]):
    assert abs(left['end_seconds'] - right['start_seconds']) < 0.05
assert all(cue['end_seconds'] > cue['start_seconds'] for cue in manifest['cues'])
out = ROOT / 'artifacts' / 'long-render-results.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(measurements, indent=2), encoding='utf-8')
print(json.dumps(measurements, indent=2))
