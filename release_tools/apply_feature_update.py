#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.20"
NEW = "0.5.21"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")


# Version.
dashboard = read("dashboard.py")
dashboard, count = re.subn(r'^VERSION\s*=\s*["\'][^"\']+["\']', f'VERSION = "{NEW}"', dashboard, count=1, flags=re.M)
assert count == 1
write("dashboard.py", dashboard)

# Keep descriptive page/card titles, but make Settings navigation concise and predictable.
html = read("static/index.html")
replacements = {
    '<button data-view="settings" data-settings-page="access" type="button">Dashboard Access</button>': '<button data-view="settings" data-settings-page="access" type="button">Access</button>',
    '<button data-view="settings" data-settings-page="clients" type="button">Download Clients</button>': '<button data-view="settings" data-settings-page="clients" type="button">Clients</button>',
    '<button data-view="settings" data-settings-page="users" type="button">User Management</button>': '<button data-view="settings" data-settings-page="users" type="button">Users</button>',
    '<option value="access">Dashboard Access</option>': '<option value="access">Access</option>',
    '<option value="clients">Download Clients</option>': '<option value="clients">Clients</option>',
    '<option value="users">User Management</option>': '<option value="users">Users</option>',
}
for old, new in replacements.items():
    assert old in html, old
    html = html.replace(old, new)
html = html.replace(OLD, NEW)
write("static/index.html", html)

# Service-worker cache/asset revisions.
sw = read("static/sw.js").replace(OLD, NEW).replace("torrent-dashboard-v0520", "torrent-dashboard-v0521")
write("static/sw.js", sw)

# Make concise Settings navigation part of the release contract.
validator = read("release_tools/validate_ui_strings.py")
needle = "    assert 'data-settings-page=\"updates\" type=\"button\">Updates</button>' in html\n"
assert needle in validator
insert = needle + (
    "    assert 'data-settings-page=\"access\" type=\"button\">Access</button>' in html\n"
    "    assert 'data-settings-page=\"clients\" type=\"button\">Clients</button>' in html\n"
    "    assert 'data-settings-page=\"users\" type=\"button\">Users</button>' in html\n"
    "    assert '<option value=\"access\">Access</option>' in html\n"
    "    assert '<option value=\"clients\">Clients</option>' in html\n"
    "    assert '<option value=\"users\">Users</option>' in html\n"
    "    assert 'data-settings-page=\"access\" type=\"button\">Dashboard Access</button>' not in html\n"
    "    assert 'data-settings-page=\"clients\" type=\"button\">Download Clients</button>' not in html\n"
    "    assert 'data-settings-page=\"users\" type=\"button\">User Management</button>' not in html\n"
)
validator = validator.replace(needle, insert, 1)
write("release_tools/validate_ui_strings.py", validator)

# Targeted final checks.
final_html = read("static/index.html")
assert '>Access</button>' in final_html
assert '>Clients</button>' in final_html
assert '>Users</button>' in final_html
assert '<div class="panel-title">Dashboard Access</div>' in final_html
assert '<div class="panel-title">User Management</div>' in final_html
assert 'VERSION = "0.5.21"' in read("dashboard.py")
assert '?v=0.5.21' in read("static/sw.js")
print("Staged Torrent Dashboard 0.5.21 concise settings navigation labels")
