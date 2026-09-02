#!/usr/bin/env python3
"""Apply the v0.5.65 interface-language consistency pass."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_VERSION = "0.5.64"
NEW_VERSION = "0.5.65"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def replace_all_checked(text: str, old: str, new: str, label: str, minimum: int = 1) -> str:
    count = text.count(old)
    if count < minimum:
        raise RuntimeError(f"{label}: expected at least {minimum} matches, found {count}")
    return text.replace(old, new)


# Keep the same visible language for the same Settings save-bar action.
settings = read("static/settings.js")
replacements = [
    ("toast('addressCopied')", "toast('Address copied')", "address copied feedback"),
    ("toast('Save The Client Before Opening Client Settings','error')", "toast('Save the client before opening client settings','error')", "client settings prerequisite"),
    ("n.custom_sound_name || 'No Custom Sound Uploaded'", "n.custom_sound_name || 'No custom sound uploaded'", "notification sound empty state"),
    ("toast('settingsSaved');", "toast('Settings saved');", "core settings feedback"),
    ("toast('Enter A GitHub Repository','error')", "toast('Enter a GitHub repository','error')", "updates validation"),
    ("toast('updateSourceSaved');", "toast('Settings saved');", "updates settings feedback"),
    ('<b>No Integrations Added</b>', '<b>No integrations added</b>', "integration empty state"),
    ('<option value=\"\">Choose Integration…</option>', '<option value=\"\">Choose integration…</option>', "integration chooser"),
    ("toast('Choose An Integration Type','error')", "toast('Choose an integration type','error')", "integration validation"),
    ("out.textContent='Testing Connection…';", "out.textContent='Testing connection…';", "integration testing state"),
    ("toast('integrationSaved');", "toast('Integration saved');", "integration saved feedback"),
    ("toast('integrationDeleted');", "toast('Integration deleted');", "integration deleted feedback"),
    ('<b>No Users Found</b>', '<b>No users found</b>', "user empty state"),
    ("const username=user.username||'New User';", "const username=user.username||'New user';", "new user label"),
    ("toast('Enter A Username','error')", "toast('Enter a username','error')", "user validation"),
    ("toast('Passwords Do Not Match','error')", "toast('Passwords do not match','error')", "password validation"),
    ("toast('userSaved');", "toast('User saved');", "user saved feedback"),
    ("toast('userDeleted');", "toast('User deleted');", "user deleted feedback"),
]
for old, new, label in replacements:
    settings = replace_once(settings, old, new, label)
settings = replace_once(settings, "      toast('clientSettingsSaved');\n", "", "duplicate client settings toast")
# Canonical source copy for dynamically generated Settings controls. Runtime
# sentence-case normalization remains as a compatibility layer for older UI.
for old, new, label in [
    ('<label>Display Name<input', '<label>Display name<input', "integration display name"),
    ('>Test Connection</button>', '>Test connection</button>', "integration test button"),
    ('>Not Tested Yet</div>', '>Not tested yet</div>', "integration initial status"),
    ('<span class=\"field-label\">User Group ', '<span class=\"field-label\">User group ', "user group label"),
    ('<label>First Name<input', '<label>First name<input', "first name label"),
    ('<label>Last Name<input', '<label>Last name<input', "last name label"),
    ('placeholder=\"Create Password\"', 'placeholder=\"Create password\"', "create password placeholder"),
    ('<span class=\"field-label\">Confirm Password ', '<span class=\"field-label\">Confirm password ', "confirm password label"),
    ('placeholder=\"Confirm Password\"', 'placeholder=\"Confirm password\"', "confirm password placeholder"),
]:
    settings = replace_once(settings, old, new, label)
write("static/settings.js", settings)

# Use sentence-case literals for common application feedback and avoid duplicate
# modal toasts when a persistent inline status already confirms the same result.
app = read("static/app.js")
app = replace_once(app, f"const FRONTEND_BUILD='{OLD_VERSION}';", f"const FRONTEND_BUILD='{NEW_VERSION}';", "frontend version")
app = replace_once(app, "toast('Administrator Access Is Required','error')", "toast('Administrator access is required','error')", "administrator feedback")
app = replace_all_checked(app, "toast('chooseSpecificServerFirst','error')", "toast('Choose a specific server first','error')", "specific server feedback", minimum=2)
app = replace_once(app, "throw new Error('chooseSpecificServerForAction')", "throw new Error('Choose a specific server for this action')", "specific server action error")
app = replace_once(app, "toast('actionSent');", "toast('Action sent');", "action feedback")
app = replace_once(app, "toast('torrentAdded');", "toast('Torrent added');", "torrent added feedback")
app = replace_once(app, ";status.textContent='Profile saved.';toast('profileSaved');", ";status.textContent='Profile saved.';", "duplicate profile toast")
app = replace_once(app, ";status.textContent='Password changed.';toast('passwordChanged');", ";status.textContent='Password changed.';", "duplicate password toast")
app = replace_once(app, ";status.textContent='Profile picture updated.';toast('profilePictureUpdated');", ";status.textContent='Profile picture updated.';", "duplicate avatar updated toast")
app = replace_once(app, ";status.textContent='Profile picture removed.';toast('profilePictureRemoved')", ";status.textContent='Profile picture removed.'", "duplicate avatar removed toast")
write("static/app.js", app)

# Frontend generation/version synchronization.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, f'VERSION = "{OLD_VERSION}"', f'VERSION = "{NEW_VERSION}"', "dashboard version")
write("dashboard.py", dashboard)

index = read("static/index.html")
index = replace_all_checked(index, OLD_VERSION, NEW_VERSION, "index asset version", minimum=5)
write("static/index.html", index)

sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v0564", "torrent-dashboard-v0565", "service worker cache version")
sw = replace_all_checked(sw, OLD_VERSION, NEW_VERSION, "service worker assets", minimum=4)
write("static/sw.js", sw)

# Durable interface-language rules. These are intentionally short and concrete:
# they describe observable product behavior rather than prescribing a framework.
write("DESIGN_LANGUAGE.md", """# Torrent Dashboard Design Language

Torrent Dashboard uses a single content language across desktop and responsive surfaces. These rules apply to static HTML, dynamically generated controls, dialogs, status messages, notifications, and toasts.

## Core rules

- Use **sentence case** for headings, labels, buttons, empty states, validation, and status text. Preserve product names and established acronyms such as Torrent Dashboard, qBitTorrent, GitHub, API, IP, URL, HTTPS, and SHA-256.
- Use the **same words for the same action and outcome**. A Save action in the core Settings save bar confirms with **“Settings saved”** regardless of which Settings page is active.
- Use feature-specific success copy only when the saved object is materially different from dashboard settings, such as **“User saved”** or **“Integration saved”**.
- Use **one success channel per interaction**. Page-level saves use a toast. Scoped dialogs that already keep a visible inline status do not also emit a duplicate success toast.
- Loading and in-progress states use an active verb plus an ellipsis, for example **“Saving client settings…”** or **“Checking for updates…”**.
- Toasts are short outcome statements without terminal punctuation. Persistent inline status and explanatory copy use complete sentences with punctuation.
- Validation and errors state what the user needs to do in plain language. Avoid internal field names, implementation terminology, camelCase tokens, and title-case error sentences.
- Destructive controls use a direct verb and object, and confirmations identify what will be deleted or removed.

## Settings feedback contract

The core Settings pages are General, Access, Clients, Updates, and Notifications. They share the same form save bar and the same successful outcome language:

> Settings saved

Updates may use a different backend endpoint, but that implementation detail must not change the user-facing confirmation.

Integrations and Users are record-management surfaces rather than core form pages. Their successful record operations remain scoped:

- Integration saved
- Integration deleted
- User saved
- User deleted

qBitTorrent client settings and account dialogs keep their result visible inside the dialog, so they do not duplicate successful completion with a toast.

## Source and validation

New user-facing copy should be authored in its final display form rather than relying on token-to-text conversion. The existing `uiText()` normalizer remains a compatibility layer for older surfaces and may be retired incrementally.

`release_tools/validate_ui_strings.py` enforces the high-value copy contracts that have caused drift before, including the core Settings save confirmation and known title-case legacy strings.
""")

# Documentation discovery should include the design-language contract.
validator = read("release_tools/validate_source.py")
validator = replace_once(
    validator,
    'for name in ("README.md", "ARCHITECTURE.md", "PROJECT_STATE.md", "CHANGELOG.md"):',
    'for name in ("README.md", "ARCHITECTURE.md", "DESIGN_LANGUAGE.md", "PROJECT_STATE.md", "CHANGELOG.md"): ',
    "design language required documentation",
)
write("release_tools/validate_source.py", validator)

ui_validator = read("release_tools/validate_ui_strings.py")
function_marker = "\ndef main():\n"
design_validator = r'''

def validate_design_language(app_js: str, settings_js: str):
    if settings_js.count("toast('Settings saved');") != 2:
        raise SystemExit("Core Settings pages must share the exact 'Settings saved' confirmation")

    forbidden_settings = (
        "updateSourceSaved",
        "settingsSaved",
        "clientSettingsSaved",
        "Save The Client Before Opening Client Settings",
        "Enter A GitHub Repository",
        "Choose An Integration Type",
        "Enter A Username",
        "Passwords Do Not Match",
        "No Integrations Added",
        "No Users Found",
        "Testing Connection…",
        "Not Tested Yet",
    )
    leaked = [value for value in forbidden_settings if value in settings_js]
    if leaked:
        raise SystemExit("Legacy Settings language remains: " + ", ".join(leaked))

    redundant_modal_toasts = (
        "toast('profileSaved')",
        "toast('passwordChanged')",
        "toast('profilePictureUpdated')",
        "toast('profilePictureRemoved')",
    )
    leaked = [value for value in redundant_modal_toasts if value in app_js]
    if leaked:
        raise SystemExit("Duplicate modal success toasts remain: " + ", ".join(leaked))

    required = (
        "toast('Address copied')",
        "toast('Integration saved')",
        "toast('Integration deleted')",
        "toast('User saved')",
        "toast('User deleted')",
        "toast('Administrator access is required','error')",
        "toast('Choose a specific server first','error')",
    )
    missing = [value for value in required if value not in app_js and value not in settings_js]
    if missing:
        raise SystemExit("Required canonical interface language is missing: " + ", ".join(missing))
'''
if function_marker not in ui_validator:
    raise RuntimeError("UI validator main marker missing")
ui_validator = ui_validator.replace(function_marker, design_validator + function_marker, 1)
ui_validator = replace_once(
    ui_validator,
    '    validate_javascript("static/settings.js", settings_js)\n',
    '    validate_javascript("static/settings.js", settings_js)\n    validate_design_language(app_js, settings_js)\n',
    "design language validator call",
)
write("release_tools/validate_ui_strings.py", ui_validator)

readme = read("README.md")
readme = replace_once(
    readme,
    "Architecture and module ownership are documented in [`ARCHITECTURE.md`](ARCHITECTURE.md). Current development handoff state is generated in [`PROJECT_STATE.md`](PROJECT_STATE.md). Backend domain modules isolate users/accounts, configuration lifecycle, configuration transactions, and integrations from the HTTP composition root.",
    "Architecture and module ownership are documented in [`ARCHITECTURE.md`](ARCHITECTURE.md), and user-facing content conventions are documented in [`DESIGN_LANGUAGE.md`](DESIGN_LANGUAGE.md). Current development handoff state is generated in [`PROJECT_STATE.md`](PROJECT_STATE.md). Backend domain modules isolate users/accounts, configuration lifecycle, configuration transactions, and integrations from the HTTP composition root.",
    "README design language link",
)
write("README.md", readme)

# Structured release source of truth.
release_path = ROOT / "release_notes" / "releases.json"
release_data = json.loads(release_path.read_text(encoding="utf-8"))
if any(str(item.get("version")) == NEW_VERSION for item in release_data.get("releases", [])):
    raise RuntimeError(f"release metadata for {NEW_VERSION} already exists")
project = release_data.setdefault("project", {})
principles = project.setdefault("principles", [])
principle = "Use the same user-facing language for the same action and outcome across every surface."
if principle not in principles:
    principles.append(principle)
release_data.setdefault("releases", []).append({
    "version": NEW_VERSION,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Interface language consistency",
    "summary": "Aligns Settings, account, and action feedback around one content-design contract so identical actions use identical language and scoped dialogs avoid redundant success notifications.",
    "highlights": [
        "Core Settings saves now confirm with the exact message 'Settings saved' on General, Access, Clients, Updates, and Notifications.",
        "Updates no longer exposes its backend-specific save path through a separate 'Update source saved' confirmation.",
        "Settings validation, empty states, dynamic labels, and common action feedback were normalized to sentence case while preserving proper product names and acronyms.",
        "Account and qBitTorrent client dialogs now rely on their persistent inline success status instead of duplicating the same outcome with a toast.",
        "Added DESIGN_LANGUAGE.md as the durable content-design contract for future UI work."
    ],
    "fixes": [
        "Saving the Updates page no longer uses different success language from the rest of the core Settings form.",
        "Removed several legacy title-case error and empty-state strings that could make adjacent surfaces feel like different products."
    ],
    "technical": [
        "release_tools/validate_ui_strings.py now enforces the shared Settings-save confirmation and rejects known legacy wording that caused drift.",
        "Changed Settings feedback is authored as explicit display copy instead of camelCase message tokens; uiText remains only as a compatibility layer for older surfaces.",
        "Release source validation now requires DESIGN_LANGUAGE.md alongside the architecture and generated handoff documentation."
    ],
    "validation": [
        "UI string validation checks the exact core Settings save contract, sentence-case replacements, and removal of redundant modal success toasts.",
        "Frontend build identity, service-worker cache generation, JavaScript syntax, backend behavioral tests, and generated release metadata remain part of the release gate."
    ],
    "known_issues": [
        "Some older application surfaces still use uiText token normalization internally even though their rendered copy is sentence case; these can be converted to explicit display strings incrementally without changing behavior."
    ],
    "architecture": [
        "DESIGN_LANGUAGE.md is the durable source for user-facing content conventions, while release_tools/validate_ui_strings.py enforces high-value regression contracts.",
        "Core Settings pages share one form-level save language even when an individual page uses a specialized backend endpoint.",
        "Scoped dialogs own their persistent inline status and do not duplicate successful completion in the global toast layer.",
        "Backend module boundaries from v0.5.64 remain unchanged."
    ],
    "decisions": [
        "Use the same words for the same action and result throughout the product.",
        "Use sentence case for interface copy except established product names and acronyms.",
        "Use one success feedback channel per interaction rather than stacking inline status and toast confirmations.",
        "Keep feature-specific success language for entity CRUD where the saved object is materially different from core dashboard settings."
    ],
    "next_steps": [
        {"priority": 1, "title": "Extract release and update provenance", "detail": "Move GitHub release parsing, installed release metadata, package-integrity normalization, and historical digest caching out of dashboard.py."},
        {"priority": 2, "title": "Extract qBitTorrent transport and normalization", "detail": "Move QBitClient, server normalization, proxy/preference translation, and Web API transport away from HTTP routing."},
        {"priority": 3, "title": "Expand request-level behavioral tests", "detail": "Add authorization, CSRF, setup, account-route, and settings-mutation coverage around extracted service boundaries."},
        {"priority": 4, "title": "Retire legacy UI copy tokens incrementally", "detail": "Replace older uiText token-derived user messages with explicit display copy when each surface is next modified, preserving the new design-language contract."}
    ]
})
release_path.write_text(json.dumps(release_data, indent=2) + "\n", encoding="utf-8")

# Regenerate the derived changelog and handoff state, then validate generation.
subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW_VERSION], cwd=ROOT, check=True)

print(f"Applied v{NEW_VERSION} design-language consistency pass")
