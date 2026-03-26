import os
import shutil
from pathlib import Path

DATA = Path(__file__).parent / 'data'

for name in ['rag.db', 'vector_db', 'graph', 'keyword_index']:
    p = DATA / name
    if p.exists():
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        print(f'Deleted: {name}')

upload = DATA / 'upload'
if upload.exists():
    for f in upload.iterdir():
        if f.is_file():
            f.unlink()
        elif f.is_dir():
            shutil.rmtree(f)
    print('Cleared: upload')

for name in ['vector_db', 'graph', 'keyword_index', 'upload']:
    (DATA / name).mkdir(parents=True, exist_ok=True)

print('Done!')
