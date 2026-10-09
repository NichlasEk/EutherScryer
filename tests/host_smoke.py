"""Run the integrated native EutherVerse bundle against a filtered cached map."""
import json
import os
import pathlib
from playwright.sync_api import sync_playwright
world=json.loads(pathlib.Path('.local/integrated/topology.json').read_text())
with sync_playwright() as p:
    browser=p.firefox.launch(headless=True,executable_path=os.environ.get('FIREFOX_EXECUTABLE'),firefox_user_prefs={'webgl.force-enabled':True})
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];writes=[];authorized=True
    page.on('pageerror',lambda error:errors.append(str(error)))
    def api(route):
        path=route.request.url.split('5194')[-1]
        if route.request.method!='GET':writes.append(path)
        if path=='/api/auth/status':data={'authenticated':authorized,'user':'test-owner','permissions':{'canServerMap':authorized},'csrfToken':'simulation'}
        elif path=='/api/admin/euthernet/map':data=world
        elif path.endswith('/commands'):data={'commands':[]}
        elif path.endswith('/audit'):data={'entries':[]}
        elif path.endswith('/ask'):data={'source':'scryer-inventory'}
        else:route.fulfill(status=404,body='unavailable');return
        route.fulfill(status=200,content_type='application/json',body=json.dumps(data))
    page.route('**/api/**',api)
    page.goto('http://127.0.0.1:5194/')
    page.wait_for_function('window.scryerHostTest?.agent?.inhabitant.engine.world.nodes.length > 0')
    page.wait_for_function('window.scryerHostTest.agent.inhabitant.engine.state.observations.length > 0',timeout=60000)
    page.evaluate("window.scryerHostTest.aim('scryer:inhabitant')")
    page.wait_for_timeout(200)
    page.keyboard.press('e')
    assert page.locator('#ev-target').inner_text()=='EutherScryer'
    assert page.locator('#ev-action-restart').is_disabled()
    page.keyboard.press('f')
    page.locator('#ev-custodian-overlay').wait_for(state='visible')
    assert 'EutherScryer' in page.locator('#ev-custodian-title').inner_text()
    page.locator('#ev-custodian-question').fill('What are you looking at?')
    page.locator('#ev-custodian-form button').click()
    page.wait_for_timeout(700)
    page.wait_for_function("document.querySelector('#ev-custodian-answer').textContent.includes('Verified inventory fact')")
    page.screenshot(path='.local/scryer-integrated.png')
    page.locator('#ev-custodian-leave').click()
    page.evaluate("window.scryerHostTest.aim('eutherbooks')")
    page.wait_for_timeout(200);page.keyboard.press('f')
    page.wait_for_function("window.scryerHostTest.room === 'eutherbooks'")
    assert page.evaluate("window.scryerHostTest.nodes.includes('qwen-desk')")
    assert not page.evaluate('window.scryerHostTest.agent.inhabitant.root.visible')
    page.keyboard.press('Escape')
    page.wait_for_function("window.scryerHostTest.room === 'city'")
    assert page.evaluate("window.scryerHostTest.nodes.includes('scryer:inhabitant')")
    # Revoked auth is handled before further conversation, independently of LLM.
    authorized=False
    result=page.evaluate("window.scryerHostTest.agent.ask('What if?')")
    assert result=='Observation access unavailable.'
    assert not page.evaluate('window.scryerHostTest.agent.inhabitant.engine.authorized')
    assert writes==['/api/admin/euthernet/ask'],writes
    assert not errors,errors
    print(json.dumps({'native_renderer':'PASS','cached_nodes':len(world['nodes']),'approach_E_F_dialog':'PASS','librarian_coexistence':'PASS','authorization_revocation':'PASS','writes':writes,'errors':errors}))
    browser.close()
