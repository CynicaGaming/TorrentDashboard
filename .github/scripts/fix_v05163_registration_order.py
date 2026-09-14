from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

app_path = ROOT / 'static' / 'app.js'
app = app_path.read_text(encoding='utf-8')
old = "const password=$('#registerPass')?.value||'';\n  if(password!==password2){const el=$('#registerError');if(el)el.textContent='Passwords do not match';return;}\n  const password2=$('#registerPass2')?.value||'';if(password.length<8)"
new = "const password=$('#registerPass')?.value||'',password2=$('#registerPass2')?.value||'';if(password!==password2){const el=$('#registerError');if(el)el.textContent='Passwords do not match';return;}if(password.length<8)"
if old not in app:
    raise RuntimeError('Expected registration password declaration order was not found')
app_path.write_text(app.replace(old, new, 1), encoding='utf-8')

test_path = ROOT / 'tests' / 'test_registration_ui.py'
test = test_path.read_text(encoding='utf-8')
marker = "        self.assertIn(\"$('#registerPass2')\",app)\n"
assertion = "        self.assertIn(\"const password=$('#registerPass')?.value||'',password2=$('#registerPass2')?.value||'';\",app)\n"
if marker not in test:
    raise RuntimeError('Registration confirmation test marker was not found')
if assertion not in test:
    test = test.replace(marker, marker + assertion, 1)
test_path.write_text(test, encoding='utf-8')
