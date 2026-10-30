"""Tests d'interface : accessibilité (axe-core, WCAG 2.2 AA) + comportements
clavier / lecteur d'écran / zoom / CSP, sur la vraie Api et une fausse clé.

    cd tests/ui && npm ci && python -m playwright install chromium
    python tests/ui/run_ui.py            # code de sortie 1 au moindre échec

Gate du CI (.github/workflows/checks.yml) : aucune régression d'accessibilité
ne peut atteindre une release.
"""
import asyncio
import os
import sys
import tempfile

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fixture  # noqa: E402
import server   # noqa: E402

AXE_PATH = os.path.join(HERE, "node_modules", "axe-core", "axe.min.js")
AXE_TAGS = "['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']"
RESULTS = []


def check(name, cond, extra=""):
    RESULTS.append((bool(cond), name, extra))


async def axe(pg, state):
    await pg.add_script_tag(path=AXE_PATH)
    r = await pg.evaluate("axe.run(document, {runOnly:{type:'tag',values:%s}})" % AXE_TAGS)
    for v in r["violations"]:
        targets = [str(n["target"]) for n in v["nodes"][:3]]
        check("axe %s : %s" % (state, v["id"]), False, "%s %s" % (v["help"], targets))
    check("axe %s : 0 violation" % state, not r["violations"])


async def setup(pg, url, root):
    await pg.goto(url + "/index.html")
    await pg.wait_for_function("window.pywebview && document.readyState === 'complete'")
    await pg.evaluate("p => pywebview.api.__dialog(p)", os.path.join(root, "Music"))
    await pg.evaluate("pywebview.api.pick_music_folder()")
    await pg.evaluate("p => pywebview.api.__dialog(p)", root)
    await pg.evaluate("pywebview.api.pick_usb_root()")
    await pg.evaluate("pywebview.api.set_lang('fr')")
    await pg.evaluate("pywebview.api.set_update_check(false)")   # pas de réseau en test
    await pg.reload()
    await pg.wait_for_timeout(2500)


async def nav(pg, v):
    await pg.click('.nav-item[data-view="%s"]' % v)
    await pg.wait_for_timeout(500)


async def axe_pass(p, url, root):
    """Contexte sans CSP : axe est injecté comme script inline."""
    b = await p.chromium.launch()
    ctx = await b.new_context(viewport={"width": 1140, "height": 760}, bypass_csp=True, locale="fr-FR")
    await ctx.add_init_script(path=os.path.join(HERE, "bridge.js"))
    pg = await ctx.new_page()
    await setup(pg, url, root)
    if not await pg.evaluate("document.getElementById('vault-modal').open"):
        await pg.evaluate("showVaultPrompt('quit', false)")
    await axe(pg, "dialogue")
    await pg.keyboard.press("Escape")
    await axe(pg, "accueil")
    await nav(pg, "tags")
    await pg.click("#rv-scan")
    await pg.wait_for_selector("#review-main", state="visible", timeout=30000)
    await axe(pg, "tags")
    await pg.evaluate("p => pywebview.api.__dialog(p)", "")
    await nav(pg, "import")
    await pg.fill("#import-text", "Daft Punk - One More Time\nMistral Gagnant")
    await pg.click("#btn-compare")
    await pg.wait_for_timeout(3000)
    await axe(pg, "import")
    await nav(pg, "orphans")
    await pg.click("#btn-orphans")
    await pg.wait_for_timeout(2500)
    await axe(pg, "hors-playlist")
    await nav(pg, "dup")
    await pg.click("#btn-scan-dup")
    await pg.wait_for_timeout(4000)
    await axe(pg, "doublons")
    await nav(pg, "integ")
    await pg.click("#btn-scan-integ")
    await pg.wait_for_timeout(5000)
    await axe(pg, "intégrité")
    await nav(pg, "sync")
    await axe(pg, "synchro")
    await pg.click("#status-btn")
    await pg.wait_for_timeout(400)
    await axe(pg, "statut")
    check("axe : aucune erreur JS", not await pg.evaluate("window.__errors"), await pg.evaluate("window.__errors"))
    await b.close()


async def behaviour_pass(p, url, root, home):
    """Contexte AVEC la CSP de l'application : comportements + violations CSP."""
    b = await p.chromium.launch()
    ctx = await b.new_context(viewport={"width": 1140, "height": 760}, locale="fr-FR")
    await ctx.add_init_script(path=os.path.join(HERE, "bridge.js"))
    pg = await ctx.new_page()
    await setup(pg, url, root)
    is_open = "document.getElementById('vault-modal').open"
    if not await pg.evaluate(is_open):
        await pg.evaluate("showVaultPrompt('start', false)")
    check("dialogue modal natif", await pg.evaluate(is_open + " && document.getElementById('vault-modal').matches(':modal')"))
    check("focus sur l'action sûre", await pg.evaluate("document.activeElement.id") == "btn-vq-skip",
          await pg.evaluate("document.activeElement.id"))
    for _ in range(6):
        await pg.keyboard.press("Tab")
    check("Tab reste dans le dialogue", await pg.evaluate("document.getElementById('vault-modal').contains(document.activeElement)"))
    await pg.keyboard.press("Escape")
    check("Échap ferme le dialogue", not await pg.evaluate(is_open))
    check("lang = fr", await pg.evaluate("document.documentElement.lang") == "fr")
    await pg.evaluate("document.activeElement.blur()")
    await pg.keyboard.press("Tab")
    check("1er Tab = lien d'évitement", await pg.evaluate("document.activeElement.className") == "skip-link")
    await pg.keyboard.press("Enter")
    check("lien d'évitement → contenu", await pg.evaluate("document.activeElement.id") == "main")
    info = pg.locator("#view-home .info").first
    check("ⓘ = bouton nommé", await info.get_attribute("role") == "button"
          and (await info.get_attribute("aria-label") or "").startswith("Aide"))
    bb = await info.bounding_box()
    check("ⓘ cible ≥ 24 px", bb["width"] >= 24 and bb["height"] >= 24, bb)
    await info.click()
    await pg.mouse.move(1, 1)
    check("clic ouvre l'aide", await info.locator(".tip").is_visible())
    await pg.keyboard.press("Escape")
    check("Échap ferme l'aide", not await info.locator(".tip").is_visible())
    check("SVG décoratifs masqués", await pg.evaluate("document.querySelectorAll('svg:not([aria-hidden]):not([role])').length") == 0)
    await nav(pg, "dup")
    check("titre de fenêtre par onglet", (await pg.title()).startswith("Repérer les doublons"), await pg.title())
    check("aria-current", await pg.get_attribute('.nav-item[data-view="dup"]', "aria-current") == "page")
    check("un seul h1 visible", await pg.evaluate("[...document.querySelectorAll('h1')].filter(h => h.offsetParent).length") == 1)
    # raccourcis (WCAG 2.1.4)
    await nav(pg, "tags")
    await pg.click("#rv-scan")
    await pg.wait_for_selector("#review-main", state="visible", timeout=30000)
    cur = "rvCurrent() && rvCurrent().id"
    a = await pg.evaluate(cur)
    await pg.focus('.nav-item[data-view="tags"]')
    await pg.keyboard.press("ArrowRight")
    await pg.wait_for_timeout(300)
    check("raccourci ignoré hors de la carte", await pg.evaluate(cur) == a)
    await pg.focus("#rv-skip")
    await pg.keyboard.press("ArrowRight")
    await pg.wait_for_timeout(500)
    b2 = await pg.evaluate(cur)
    check("raccourci actif dans la carte", b2 != a, (a, b2))
    await pg.click("#rv-keys-toggle")
    await pg.wait_for_timeout(400)
    await pg.focus("#rv-skip")
    await pg.keyboard.press("ArrowRight")
    await pg.wait_for_timeout(400)
    check("raccourcis désactivables", await pg.evaluate(cur) == b2)
    with open(os.path.join(home, ".djhelper", "config.json"), encoding="utf-8") as f:
        check("choix des raccourcis mémorisé", '"kbd_shortcuts": false' in f.read())
    await pg.click("#rv-keys-toggle")
    await pg.wait_for_timeout(400)
    await pg.evaluate("toast('Analyse terminée 🎉')")
    await pg.wait_for_timeout(200)
    check("message annoncé sans emoji", (await pg.text_content("#sr-status")).strip() == "Analyse terminée",
          await pg.text_content("#sr-status"))
    await pg.evaluate("showProgress('dup-loading','Analyse…'); setProgress('dup-loading', 3, 4, 'Analyse…')")
    check("barre de progression lisible", await pg.get_attribute("#dup-loading .pbar", "aria-valuenow") == "75")
    await pg.evaluate("document.getElementById('dup-loading').style.display = 'none'")
    # zoom 200 % (1140x760 → 570x380)
    await pg.set_viewport_size({"width": 570, "height": 380})
    await nav(pg, "home")
    check("zoom 200 % : pas de défilement horizontal",
          await pg.evaluate("document.scrollingElement.scrollWidth <= innerWidth + 1"))
    for sel in ('.nav-item[data-view="sync"]', "#status-btn"):
        await pg.locator(sel).scroll_into_view_if_needed()
        check("zoom 200 %% : %s atteignable" % sel, await pg.evaluate(
            "s => { const r = document.querySelector(s).getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }", sel))
    await pg.set_viewport_size({"width": 1140, "height": 760})
    # anglais
    await pg.evaluate("pywebview.api.set_lang('en')")
    await pg.reload()
    await pg.wait_for_timeout(2500)
    if await pg.evaluate(is_open):
        await pg.keyboard.press("Escape")
    check("lang = en", await pg.evaluate("document.documentElement.lang") == "en")
    check("aide traduite", (await pg.locator("#view-home .info").first.get_attribute("aria-label")).startswith("Help"))
    # CSP : aucune violation pendant tout le parcours, puis un script inline est bien bloqué
    check("CSP : aucune violation en usage normal", not await pg.evaluate("window.__csp"), await pg.evaluate("window.__csp"))
    await pg.evaluate("const s = document.createElement('script'); s.textContent = 'window.__inl = 1'; document.body.appendChild(s)")
    check("CSP : script inline bloqué", not await pg.evaluate("window.__inl === 1"))
    check("aucune erreur JS", not await pg.evaluate("window.__errors"), await pg.evaluate("window.__errors"))
    await pg.evaluate("pywebview.api.set_lang('fr')")
    await b.close()


async def main():
    if not os.path.exists(AXE_PATH):
        sys.exit("axe-core absent : lancer « npm ci » dans tests/ui")
    work = tempfile.mkdtemp(prefix="djh-ui-")
    root = fixture.build(work)
    home = os.path.join(work, "home")
    url, srv = server.start(home)
    async with async_playwright() as p:
        await axe_pass(p, url, root)
        await behaviour_pass(p, url, root, home)
    srv.shutdown()
    bad = [r for r in RESULTS if not r[0]]
    for ok, name, extra in RESULTS:
        print(("OK  " if ok else "KO  ") + name + ((" — %s" % (extra,)) if (extra and not ok) else ""))
    print("\n%d vérifications, %d échec(s)" % (len(RESULTS), len(bad)))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    asyncio.run(main())
