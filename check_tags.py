import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR if (SCRIPT_DIR / "backend").is_dir() else SCRIPT_DIR.parent
HOME_VIEW = PROJECT_ROOT / "backend" / "frontend" / "src" / "views" / "Home.vue"
lines = HOME_VIEW.read_text(encoding="utf-8").splitlines(keepends=True)

template_end = 0
for i, l in enumerate(lines):
    if l.strip() == '</template>':
        template_end = i
        break

print(f'Template ends at line {template_end+1}')

open_count = 0
close_count = 0
depth = 0
for i, l in enumerate(lines[:template_end]):
    opens = len(re.findall(r'<div[\s>]', l))
    closes = len(re.findall(r'</div>', l))
    open_count += opens
    close_count += closes
    depth += opens - closes
    if depth < 0:
        print(f'Line {i+1}: depth={depth} | {l.rstrip()}')

print(f'Open <div>: {open_count}')
print(f'Close </div>: {close_count}')
print(f'Diff (open - close): {open_count - close_count}')

# Also show depth at each 50-line interval to find where imbalance starts
print('\n--- Depth tracking (every 50 lines) ---')
depth2 = 0
for i, l in enumerate(lines[:template_end]):
    opens = len(re.findall(r'<div[\s>]', l))
    closes = len(re.findall(r'</div>', l))
    depth2 += opens - closes
    if (i+1) % 50 == 0:
        print(f'Line {i+1}: depth={depth2}')
print(f'Final depth: {depth2}')
