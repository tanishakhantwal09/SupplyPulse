import os
import re

files = [
    'agents/supervisor_agent.py',
    'agents/route_optimization_agent.py',
    'agents/inventory_agent.py',
    'agents/financial_auditor_agent.py',
]

for f in files:
    if os.path.exists(f):
        c = open(f, encoding='utf-8').read()
        c = re.sub(r'max_tokens=\d+', 'max_tokens=400', c)
        open(f, 'w', encoding='utf-8').write(c)
        print(f'Fixed: {f} — max_tokens=400')
    else:
        print(f'Not found: {f}')
