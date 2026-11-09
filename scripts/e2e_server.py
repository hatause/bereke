"""Disposable database for browser tests; never resets the student's progress."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='academy-e2e-') as folder:
    os.environ['DATABASE_URL']='sqlite:///'+(Path(folder)/'e2e.sqlite3').as_posix()
    for args in [['alembic','upgrade','head'],['app.seed']]:
        subprocess.run([sys.executable,'-m',*args],cwd=root/'backend',check=True)
    sys.path.insert(0,str(root/'backend'))
    import uvicorn
    uvicorn.run('app.main:app',host='127.0.0.1',port=8000)
