import os

files = [
    'agents/supervisor_agent.py',
    'agents/route_optimization_agent.py',
    'agents/inventory_agent.py',
    'agents/financial_auditor_agent.py',
]

for f in files:
    if os.path.exists(f):
        c = open(f, encoding='utf-8').read()
        # Add max_tokens after temperature=0.1
        old = 'temperature=0.1\n)'
        new = 'temperature=0.1,\n    max_tokens=600\n)'
        if old in c:
            c = c.replace(old, new)
            open(f, 'w', encoding='utf-8').write(c)
            print('Fixed:', f)
        elif 'max_tokens' in c:
            print('Already fixed:', f)
        else:
            print('Pattern not found:', f)
