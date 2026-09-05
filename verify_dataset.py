import pandas as pd
import os
import json

print('='*50)
print('DATASET VERIFICATION')
print('='*50)

files = {
    'Master enriched': 'dataset/final/master_enriched.parquet',
    'Training set': 'dataset/final/training_set.parquet',
    'Validation set': 'dataset/final/validation_set_REAL_ONLY.parquet',
}

for name, path in files.items():
    if os.path.exists(path):
        df = pd.read_parquet(path)
        size = os.path.getsize(path)/(1024*1024)
        print(f'{name}: {len(df):,} rows | {len(df.columns)} cols | {size:.1f} MB')
        print(f'  Columns sample: {list(df.columns)[:5]}')
    else:
        print(f'MISSING: {path}')

print()
print('='*50)
print('REFERENCE DATABASES')
print('='*50)

refs = {
    'Ports': 'dataset/reference/ports.json',
    'Routes': 'dataset/reference/routes.json',
    'Commodities': 'dataset/reference/commodities.json',
}

for name, path in refs.items():
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        print(f'{name}: {len(data)} records -- OK')
    else:
        print(f'MISSING: {path}')

print()
print('='*50)
print('RAW SAMPLE KEPT')
print('='*50)

raw_folder = 'dataset/raw/gdelt_master'
if os.path.exists(raw_folder):
    files_in_raw = os.listdir(raw_folder)
    print(f'Files kept: {files_in_raw}')
else:
    print('Raw folder not found')

print()
print('='*50)
print('AGENT FILES')
print('='*50)

agents = [
    'agents/supervisor_agent.py',
    'agents/route_optimization_agent.py',
    'agents/inventory_agent.py',
    'agents/financial_auditor_agent.py',
    'agents/langgraph_orchestrator.py',
]

for a in agents:
    status = 'OK' if os.path.exists(a) else 'MISSING'
    print(f'{a}: {status}')

print()
print('='*50)
print('EXPERIMENT FILES')
print('='*50)

exps = [
    'experiments/formal_evaluation.py',
    'experiments/brintrup_baseline.py',
    'experiments/paper_scenarios.py',
    'experiments/live_demo.py',
    'run_demo.py',
]

for e in exps:
    status = 'OK' if os.path.exists(e) else 'MISSING'
    print(f'{e}: {status}')

print()
print('='*50)
print('SCENARIOS AND NOTEBOOKS')
print('='*50)

others = [
    'dataset/scenarios/sample_scenarios.json',
    'notebooks/SupplyPulse_EDA.ipynb',
    'agents/pipeline_result.json',
]

for o in others:
    status = 'OK' if os.path.exists(o) else 'MISSING'
    print(f'{o}: {status}')

print()
print('ALL CHECKS COMPLETE')
