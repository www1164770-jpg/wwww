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

# Track depth and print when it changes significantly or at key points
depth = 0
stack = []  # track open div line numbers

for i, l in enumerate(lines[:template_end]):
    opens = len(re.findall(r'<div[\s>]', l))
    closes = len(re.findall(r'</div>', l))
    for _ in range(opens):
        stack.append(i+1)
    for _ in range(closes):
        if stack:
            stack.pop()
    depth += opens - closes

print(f'Unclosed <div> tags still open at end of template:')
for line_num in stack:
    print(f'  Line {line_num}: {lines[line_num-1].rstrip()}')
