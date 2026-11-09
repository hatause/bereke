"""Fail if source files are tracked or copied/imported into the frontend."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
failures=[]
private_prefixes=('sources/private/','data/','.local/')
result=subprocess.run(['git','ls-files','-z'],cwd=ROOT,capture_output=True,check=True)
tracked=result.stdout.decode('utf-8').split('\0')
for name in tracked:
    if name.startswith(private_prefixes) or Path(name).suffix.lower() in {'.pdf','.pptx','.xlsx','.sqlite3','.db'}:
        failures.append('Tracked private file: '+name)
for folder in ['frontend/src','frontend/public','frontend/dist']:
    for path in (ROOT/folder).rglob('*'):
        if not path.is_file(): continue
        if path.suffix.lower() in {'.pdf','.pptx','.xlsx','.sqlite3','.db'}:
            failures.append('Private artifact in frontend: '+str(path.relative_to(ROOT)))
        elif path.suffix in {'.ts','.tsx','.js','.html','.json'}:
            text=path.read_text(encoding='utf-8')
            for forbidden in ['sources/private/','reviewed_content.json','terms_from_excel.json','lessons_seed.json']:
                if forbidden in text: failures.append('Private content reference in '+str(path.relative_to(ROOT)))
for name in ['data/reviewed_content.json','.local/academy.sqlite3',*('sources/private/'+p.name for p in (ROOT/'sources/private').iterdir())]:
    if subprocess.run(['git','check-ignore','-q',name],cwd=ROOT).returncode != 0:
        failures.append('Not ignored: '+name)
if failures:
    raise SystemExit('\n'.join(failures))
print('PASS: private files ignored, none tracked; frontend source/build contains no private document files or imports.')
