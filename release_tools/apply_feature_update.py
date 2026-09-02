from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def replace_once(path, old, new):
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one match in {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main():
    dashboard = ROOT / "dashboard.py"
    index = ROOT / "static" / "index.html"
    app_js = ROOT / "static" / "app.js"
    app_css = ROOT / "static" / "app.css"
    sw = ROOT / "static" / "sw.js"

    replace_once(dashboard, 'VERSION = "0.5.37"', 'VERSION = "0.5.38"')

    html = index.read_text(encoding="utf-8")
    if 'v=0.5.37' not in html:
        raise RuntimeError("Expected v0.5.37 static asset references")
    html = html.replace('v=0.5.37', 'v=0.5.38')
    old_brand = '<div class="brand"><div class="brand-mark">⇣</div><div><strong id="brandTitle">Torrent Dashboard</strong><small>qBitTorrent Control</small></div></div>'
    new_brand = '<button class="brand brand-home" id="homeBrand" type="button" aria-label="Go to dashboard"><span class="brand-mark" aria-hidden="true">⇣</span><span class="brand-copy"><strong id="brandTitle">Torrent Dashboard</strong><small id="brandAddress">—</small></span></button>'
    if html.count(old_brand) != 1:
        raise RuntimeError("Expected current sidebar brand markup")
    html = html.replace(old_brand, new_brand, 1)
    index.write_text(html, encoding="utf-8")

    replace_once(
        app_js,
        "$('#brandTitle').textContent=state.me.title;document.title=state.me.title;$('#version').textContent=`v${state.me.version}`;",
        "$('#brandTitle').textContent=state.me.title;$('#brandAddress').textContent=state.me.lan_ip||'Local';document.title=state.me.title;$('#version').textContent=`v${state.me.version}`;",
    )
    replace_once(
        app_js,
        "function bindUI(){if(bound)return;bound=true;\n  $$('.nav-root,.settings-subnav button,.mobile-nav button').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));",
        "function bindUI(){if(bound)return;bound=true;\n  $('#homeBrand').addEventListener('click',()=>setView('dashboard'));\n  $$('.nav-root,.settings-subnav button,.mobile-nav button').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));",
    )

    css = app_css.read_text(encoding="utf-8")
    marker = '.brand{display:flex;gap:11px;align-items:center;padding:3px 7px 24px}'
    if marker not in css:
        raise RuntimeError("Expected sidebar brand CSS")
    css = css.replace(marker, '.brand{display:flex;gap:11px;align-items:center;padding:3px 7px 24px}', 1)
    insert_after = '.brand-mark{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:linear-gradient(145deg,#1e2a37,#111820);border:1px solid #304051;color:#dbe9ff;font-size:18px;box-shadow:var(--shadow)}'
    addition = '.brand-home{width:100%;border:0;background:transparent;color:inherit;text-align:left;padding:7px;margin:0 0 14px;border-radius:12px}.brand-home:hover{background:var(--panel2)}.brand-home:focus-visible{background:var(--panel2);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 16%,transparent)}.brand-copy{display:block;min-width:0;flex:1}.brand-home strong,.brand-home small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}'
    if css.count(insert_after) != 1:
        raise RuntimeError("Expected brand mark CSS")
    css = css.replace(insert_after, insert_after + addition, 1)
    app_css.write_text(css, encoding="utf-8")

    sw_text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v0537" not in sw_text or "v=0.5.37" not in sw_text:
        raise RuntimeError("Expected v0.5.37 service worker cache")
    sw_text = sw_text.replace("torrent-dashboard-v0537", "torrent-dashboard-v0538").replace("v=0.5.37", "v=0.5.38")
    sw.write_text(sw_text, encoding="utf-8")

    # Feature-specific checks before the release workflow performs its broader validation.
    rendered = index.read_text(encoding="utf-8")
    js = app_js.read_text(encoding="utf-8")
    assert 'id="homeBrand"' in rendered
    assert 'id="brandAddress"' in rendered
    assert 'qBitTorrent Control' not in rendered
    assert "state.me.lan_ip||'Local'" in js
    assert "$('#homeBrand').addEventListener('click',()=>setView('dashboard'))" in js


if __name__ == "__main__":
    main()
