from pathlib import Path

path = Path('.github/scripts/apply_v05163.py')
text = path.read_text(encoding='utf-8')
old = '''if "{username,password,password2}" not in block:\n    block, count = re.subn(r"\\{username\\s*,\\s*password\\}", "{username,password,password2}", block, count=1)\n    if count != 1:\n        raise RuntimeError("Registration request payload was not found")\n'''
new = '''payload_call = block.find("JSON.stringify(", call_local)\nif payload_call < 0:\n    raise RuntimeError("Registration JSON payload was not found")\npayload_open = block.find("{", payload_call)\npayload_close = block.find("}", payload_open)\nif payload_open < 0 or payload_close < 0:\n    raise RuntimeError("Registration JSON object was not found")\npayload = block[payload_open + 1:payload_close]\nif "password2" not in payload:\n    payload = payload.rstrip() + ("," if payload.strip() else "") + "password2"\n    block = block[:payload_open + 1] + payload + block[payload_close:]\n'''
if old not in text:
    raise RuntimeError('Expected registration payload patch block was not found')
text = text.replace(old, new, 1)
old_test = "        self.assertIn('{username,password,password2}',app)"
new_test = "        self.assertIn('password,password2',app)"
if old_test not in text:
    raise RuntimeError('Expected generated registration payload assertion was not found')
path.write_text(text.replace(old_test, new_test, 1), encoding='utf-8')
