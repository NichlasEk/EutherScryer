"""Run the integrated native EutherVerse bundle against a filtered cached map."""

import json
import os
import tempfile
import importlib.util
import pathlib
from playwright.sync_api import sync_playwright

spec = importlib.util.spec_from_file_location(
    "world", pathlib.Path(__file__).parents[1] / "backend/scryer_world.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
world = json.loads(pathlib.Path(".local/integrated/topology.json").read_text())
with tempfile.TemporaryDirectory() as directory, sync_playwright() as p:
    shared = module.ScryerWorld(directory, lambda: world)
    shared.start()
    browser = p.firefox.launch(
        headless=True,
        executable_path=os.environ.get("FIREFOX_EXECUTABLE"),
        firefox_user_prefs={"webgl.force-enabled": True},
    )
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    writes = []
    authorized = True
    page.on("pageerror", lambda error: errors.append(str(error)))

    def api(route):
        path = route.request.url.split("5194")[-1]
        if route.request.method != "GET":
            writes.append(path)
        if path == "/api/auth/status":
            data = {
                "authenticated": authorized,
                "user": "test-owner",
                "permissions": {"canServerMap": authorized},
                "csrfToken": "simulation",
                "isAdmin": True,
            }
        elif path == "/api/admin/euthernet/map":
            data = world
        elif path == "/api/admin/euthernet/scryer":
            data = shared.snapshot()
        elif path == "/api/admin/euthernet/scryer/control":
            body = route.request.post_data_json
            data = shared.control(body["command"], body.get("ghost_id"), body.get("data"))
        elif path.endswith("/commands"):
            data = {"commands": []}
        elif path.endswith("/audit"):
            data = {"entries": []}
        elif path.endswith("/ask"):
            data = {"source": "scryer-inventory"}
        else:
            route.fulfill(status=404, body="unavailable")
            return
        route.fulfill(
            status=200, content_type="application/json", body=json.dumps(data)
        )

    page.route("**/api/**", api)
    page.goto("http://127.0.0.1:5194/")
    page.wait_for_function(
        "window.scryerHostTest?.agent?.inhabitant.engine.world.nodes.length > 0"
    )
    page.wait_for_function(
        "window.scryerHostTest.agent.inhabitant.engine.state.observations.length > 0",
        timeout=60000,
    )
    layout = page.evaluate("window.scryerHostTest.positions")
    for node in shared.world["nodes"]:
        assert abs(layout[node["id"]]["x"] - node["x"]) < 1e-8
        assert abs(layout[node["id"]]["z"] - node["z"]) < 1e-8
    page.evaluate("window.scryerHostTest.aim('scryer:inhabitant')")
    page.wait_for_timeout(200)
    page.keyboard.press("e")
    assert page.locator("#ev-target").inner_text() == "EutherScryer"
    assert page.locator("#ev-action-restart").is_disabled()
    page.keyboard.press("f")
    page.locator("#ev-custodian-overlay").wait_for(state="visible")
    assert "EutherScryer" in page.locator("#ev-custodian-title").inner_text()
    page.locator("#ev-custodian-question").fill("What are you looking at?")
    page.locator("#ev-custodian-form button").click()
    page.wait_for_timeout(700)
    page.wait_for_function(
        "document.querySelector('#ev-custodian-answer').textContent.includes('Verified inventory fact')"
    )
    page.screenshot(path=".local/scryer-integrated.png")
    page.locator("#ev-custodian-leave").click()
    page.evaluate("window.scryerHostTest.aim('eutherbooks')")
    page.wait_for_timeout(200)
    page.keyboard.press("f")
    page.wait_for_function("window.scryerHostTest.room === 'eutherbooks'")
    assert page.evaluate("window.scryerHostTest.nodes.includes('qwen-desk')")
    assert not page.evaluate("window.scryerHostTest.agent.inhabitant.root.visible")
    page.keyboard.press("Escape")
    page.wait_for_function("window.scryerHostTest.room === 'city'")
    assert page.evaluate("window.scryerHostTest.nodes.includes('scryer:inhabitant')")
    # The actual user-facing focus button moves the camera, rather than a test-only aim.
    page.keyboard.press("m")
    page.get_by_role("button", name="Find Scryer", exact=True).click()
    page.wait_for_timeout(400)
    projected = page.evaluate("window.scryerHostTest.project('scryer:inhabitant')")
    assert abs(projected[0]) < 0.2 and abs(projected[1]) < 0.2, projected
    assert page.evaluate("window.scryerHostTest.distance('scryer:inhabitant')") > 7
    assert page.locator("#ev-target").inner_text() == "EutherScryer"
    page.wait_for_function("window.scryerHostTest.agent.inhabitant.engine.state.ghosts.some(g => g.node === 'server' && g.pattern === 'shared-host')", timeout=120000)
    page.get_by_role("button", name="Ideas ·").click()
    dialog = page.get_by_role("dialog", name="Scryer hypotheses and evidence")
    dialog.get_by_role("button", name="server · shared-host").click()
    dialog.get_by_role("button", name="Save idea", exact=True).click()
    dialog.get_by_role("button", name="Unsave idea", exact=True).wait_for()
    dialog.get_by_label("Investigation outcome").select_option("inconclusive")
    dialog.get_by_label("Investigation notes").fill("Checked documentation; no restore performed.")
    dialog.get_by_role("button", name="Record investigation", exact=True).click()
    page.wait_for_function("window.scryerHostTest.agent.inhabitant.engine.state.ghosts.some(g => g.review?.outcome === 'inconclusive')")
    page.screenshot(path=".local/scryer-ideas.png")
    dialog.get_by_role("button", name="Close", exact=True).click()
    page.reload()
    page.wait_for_function("window.scryerHostTest?.agent?.inhabitant.engine.state.ghosts.some(g => g.review?.saved && g.review?.note.includes('no restore'))")
    page.get_by_role("button", name="Ideas ·").click()
    dialog.get_by_role("button", name="server · shared-host").click()
    dialog.get_by_role("button", name="server", exact=True).click()
    assert page.locator("#ev-target").inner_text() != "EutherScryer"
    # Two browser contexts share one owner-controlled state, never local copies.
    page.get_by_role("button", name="Pause", exact=True).click()
    page.wait_for_function("window.scryerHostTest.agent.inhabitant.engine.state.paused")
    second = browser.new_page(viewport={"width": 1000, "height": 800})
    second.route("**/api/**", api)
    second.goto("http://127.0.0.1:5194/")
    second.wait_for_function(
        "window.scryerHostTest?.agent?.inhabitant.engine.state.paused"
    )
    assert second.evaluate(
        "window.scryerHostTest.agent.inhabitant.engine.state.position"
    ) == page.evaluate("window.scryerHostTest.agent.inhabitant.engine.state.position")
    assert second.evaluate(
        "window.scryerHostTest.agent.inhabitant.engine.state.observations"
    ) == page.evaluate(
        "window.scryerHostTest.agent.inhabitant.engine.state.observations"
    )
    second.close()
    # Revoked auth is handled before further conversation, independently of LLM.
    authorized = False
    result = page.evaluate("window.scryerHostTest.agent.ask('What if?')")
    assert result == "Observation access unavailable."
    assert not page.evaluate("window.scryerHostTest.agent.inhabitant.engine.authorized")
    assert writes.count("/api/admin/euthernet/ask") == 1
    assert writes.count("/api/admin/euthernet/scryer/control") == 3
    assert set(writes) == {"/api/admin/euthernet/ask", "/api/admin/euthernet/scryer/control"}
    assert not errors, errors
    print(
        json.dumps(
            {
                "native_renderer": "PASS",
                "cached_nodes": len(world["nodes"]),
                "approach_E_F_dialog": "PASS",
                "librarian_coexistence": "PASS",
                "shared_two_browsers": "PASS",
                "find_evidence_save_review_reload": "PASS",
                "native_coordinates": "PASS",
                "authorization_revocation": "PASS",
                "writes": writes,
                "errors": errors,
            }
        )
    )
    browser.close()
    shared.close()
