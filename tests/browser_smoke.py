"""Firefox-only interactive simulation regression. Run with demo server on 5193."""

import json
import os
import pathlib
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.firefox.launch(
        headless=True,
        executable_path=os.environ.get("FIREFOX_EXECUTABLE"),
        firefox_user_prefs={"webgl.force-enabled": True},
    )
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:5193/")
    page.wait_for_function("window.scryerDemo", timeout=20000)
    page.wait_for_function(
        "window.scryerDemo.inhabitant.engine.state.ghosts.length === 1", timeout=45000
    )
    page.screenshot(path=".local/scryer-desktop.png")
    page.keyboard.press("f")
    assert "Hypothesis:" in page.locator("#answer").inner_text()
    saved = page.evaluate("window.scryerDemo.inhabitant.engine.serialize()")
    page.evaluate("window.scryerDemo.inhabitant.save()")
    page.reload()
    page.wait_for_function("window.scryerDemo")
    assert page.evaluate("window.scryerDemo.inhabitant.engine.state.ghosts.length") == 1
    page.get_by_role("button", name="Simulate EutherVault status change").click()
    assert page.evaluate(
        "window.scryerDemo.inhabitant.engine.pending.includes('euthervault')"
    )
    page.get_by_role("button", name="Pause", exact=True).click()
    before = page.evaluate(
        "JSON.stringify(window.scryerDemo.inhabitant.engine.state.position)"
    )
    page.wait_for_timeout(250)
    assert before == page.evaluate(
        "JSON.stringify(window.scryerDemo.inhabitant.engine.state.position)"
    )
    page.get_by_role("button", name="Resume", exact=True).click()
    page.get_by_role("button", name="Disable", exact=True).click()
    assert not page.evaluate("window.scryerDemo.inhabitant.root.visible")
    page.get_by_role("button", name="Enable", exact=True).click()
    page.get_by_role("textbox", name="Ask Scryer").fill("Can you restart services?")
    page.get_by_role("button", name="Ask", exact=True).click()
    page.wait_for_function(
        "document.querySelector('#answer').textContent.includes('no execution capability')"
    )
    page.emulate_media(reduced_motion="reduce")
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=".local/scryer-mobile.png")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert not errors, errors
    print(
        json.dumps(
            {
                "firefox": "PASS",
                "ghosts": 1,
                "restore": "PASS",
                "simulated_event": "PASS",
                "pause_disable": "PASS",
                "conversation": "PASS",
                "mobile": "PASS",
                "page_errors": errors,
            }
        )
    )
    browser.close()
