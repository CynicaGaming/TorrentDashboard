#!/usr/bin/env python3
import re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BAD={'config.json','config.example.json','IMPLEMENTATION_STATUS.md','.env'}
PREFIX=('data/','.venv/','venv/','dist/','build/')
PATTERNS={
 'GitHub token':re.compile(r'\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{30,})\b'),
 'AWS access key':re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
 'private key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'Discord webhook':re.compile(r'https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\d{5,}/[A-Za-z0-9._-]{20,}'),
 'Slack webhook':re.compile(r'https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+'),
 'qBitTorrent API key':re.compile(r'\bqbt_[A-Za-z0-9]{28}\b'),
}
TEXT={'.py','.js','.css','.html','.md','.json','.yml','.yaml','.toml','.ini','.cfg','.txt','.bat','.ps1','.sh','.webmanifest'}
files=[x.decode() for x in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0') if x]
fail=[]
for rel in files:
    rel=rel.replace('\\','/')
    if rel in BAD or any(rel.startswith(p) for p in PREFIX): fail.append('disallowed tracked path: '+rel); continue
    p=ROOT/rel
    if p.name!='.gitignore' and p.suffix.lower() not in TEXT: continue
    try: text=p.read_text(encoding='utf-8')
    except UnicodeDecodeError: continue
    for label,rx in PATTERNS.items():
        if rx.search(text): fail.append(f'{label} pattern found in {rel}')
if fail: raise SystemExit('Public repository hygiene check failed:\n- '+'\n- '.join(sorted(set(fail))))
print(f'Public repository hygiene check passed ({len(files)} tracked files scanned)')
