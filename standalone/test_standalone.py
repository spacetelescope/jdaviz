import os
from pathlib import Path

import pytest
from playwright.sync_api import Page


def test_solara_basics(page: Page):
    page.goto("http://localhost:8765/", wait_until="commit")
    page.locator('text=Load Local File').wait_for()


@pytest.fixture
def visibility_probe(page):
    page.goto(os.environ.get('JDAVIZ_TEST_URL', 'http://localhost:8765/'))
    page.wait_for_function('!!window.Vue')
    source = (Path(__file__).parents[1] / 'jdaviz/components/tray_plugin.vue').read_text()
    script = source.split('<script>', 1)[1].split('</script>', 1)[0]
    app_source = (Path(__file__).parents[1] / 'jdaviz/app.vue').read_text()
    app_script = app_source.split('<script>', 1)[1].split('</script>', 1)[0]
    page.evaluate("""({script, appScript}) => {
        const component = new Function(script.replace('export default', 'return'))();
        const appComponent = new Function(appScript.replace('export default', 'return'))();
        component.render = () => Vue.h('div', {style: {width: '100px', height: '100px'}});
        const host = document.createElement('div');
        document.body.appendChild(host);
        const events = [];
        const props = Vue.reactive({scroll_to: false});
        const closedViews = [];
        const relay = {
            _visibilityWindow: window,
            visibility_id: 'test-app',
            plugin_view_closed: event => closedViews.push(event),
        };
        const onMessage = appComponent.methods.onPluginViewClosed.bind(relay);
        window.addEventListener('message', onMessage);
        const app = Vue.createApp({
            render: () => Vue.h(component, {
                ...props,
                'onPlugin-visibility': event => events.push(event),
                'onUpdate:scroll_to': value => { props.scroll_to = value; },
            }),
        });
        app.mount(host);
        const element = host.firstElementChild;
        const scrolls = [];
        element.scrollIntoView = options => scrolls.push(options);
        window.visibilityProbe = {
            app, host, element, events, props, scrolls, closedViews, component,
            cleanup: () => {
                if (host.firstElementChild) app.unmount();
                host.remove();
                window.removeEventListener('message', onMessage);
                delete window.visibilityProbe;
            },
        };
    }""", {'script': script, 'appScript': app_script})
    yield page
    page.evaluate('visibilityProbe.cleanup()')


def test_visibility_lifecycle(visibility_probe):
    page = visibility_probe
    page.wait_for_function('visibilityProbe.events.length === 1')
    view_id = page.evaluate('visibilityProbe.events[0].view_id')
    assert page.evaluate('visibilityProbe.events[0].visible') is True

    page.evaluate("visibilityProbe.host.style.display = 'none'")
    page.wait_for_function('visibilityProbe.events.length === 2')
    assert page.evaluate('visibilityProbe.events[1].visible') is False
    page.evaluate("visibilityProbe.host.style.display = ''")
    page.wait_for_function('visibilityProbe.events.length === 3')

    page.evaluate('visibilityProbe.host.remove()')
    page.wait_for_function('visibilityProbe.events.length === 4')
    assert page.evaluate('visibilityProbe.events[3].visible') is False
    page.evaluate('document.body.appendChild(visibilityProbe.host)')
    page.wait_for_function('visibilityProbe.events.length === 5')

    page.evaluate("visibilityProbe.host.style.visibility = 'hidden'")
    page.wait_for_function('visibilityProbe.events.length === 6')
    page.evaluate("visibilityProbe.host.style.visibility = ''")
    page.wait_for_function('visibilityProbe.events.length === 7')
    assert page.evaluate('visibilityProbe.events.every(e => e.view_id === '
                         'visibilityProbe.events[0].view_id)') is True
    assert page.evaluate('visibilityProbe.events[6].view_id') == view_id

    # Off-screen is still open; repeated resize/mutation callbacks must not send pings.
    page.evaluate("visibilityProbe.host.style.transform = 'translateY(100000px)'")
    page.wait_for_timeout(600)
    assert page.evaluate('visibilityProbe.events.length') == 7
    assert page.evaluate('visibilityProbe.events[6].visible') is True

    page.evaluate('visibilityProbe.app.unmount()')
    assert page.evaluate('visibilityProbe.events.length') == 8
    assert page.evaluate('visibilityProbe.events[7].visible') is False
    page.evaluate("visibilityProbe.host.style.display = 'none'")
    page.wait_for_timeout(100)
    assert page.evaluate('visibilityProbe.events.length') == 8


def test_visibility_popout_close_after_transport_disposal(visibility_probe):
    page = visibility_probe
    with page.expect_popup() as popup_info:
        page.evaluate("window.open(location.origin + '/lab', '_blank')")
    popup = popup_info.value
    popup.wait_for_load_state('domcontentloaded')
    popup.evaluate("""() => {
        const {Vue, visibilityProbe} = opener;
        const host = document.createElement('div');
        document.body.appendChild(host);
        let connected = true;
        // Match Solara: the connection is disposed before pagehide.
        window.addEventListener('beforeunload', () => { connected = false; });
        Vue.createApp({
            render: () => Vue.h(visibilityProbe.component, {
                visibility_context: {app_id: 'test-app', plugin_id: 'test-plugin'},
                'onPlugin-visibility': event => {
                    if (connected) visibilityProbe.events.push(event);
                },
            }),
        }).mount(host);
    }""")
    page.wait_for_function('visibilityProbe.events.length === 2')
    popup_id = page.evaluate('visibilityProbe.events[1].view_id')
    page.evaluate('visibilityProbe.app.unmount()')
    popup.close(run_before_unload=True)
    page.wait_for_function('visibilityProbe.closedViews.length === 1')
    assert page.evaluate('visibilityProbe.closedViews[0]') == {
        'type': 'jdaviz:plugin-view-closed',
        'app_id': 'test-app',
        'plugin_id': 'test-plugin',
        'view_id': popup_id,
    }


def test_visibility_restored_page_gets_new_id(visibility_probe):
    page = visibility_probe
    old_id = page.evaluate('visibilityProbe.events[0].view_id')
    page.evaluate("window.dispatchEvent(new Event('pagehide'))")
    assert page.evaluate('visibilityProbe.events[1].visible') is False
    page.evaluate("window.dispatchEvent(new Event('pageshow'))")
    assert page.evaluate('visibilityProbe.events[2].visible') is True
    assert page.evaluate('visibilityProbe.events[2].view_id') != old_id


def test_visibility_relay_filters_messages(visibility_probe):
    page = visibility_probe
    page.evaluate("""() => {
        const data = {
            type: 'jdaviz:plugin-view-closed', app_id: 'test-app',
            plugin_id: 'test-plugin', view_id: 'popout',
        };
        window.dispatchEvent(new MessageEvent('message', {data, origin: 'https://other.invalid'}));
        window.dispatchEvent(new MessageEvent('message', {
            data: {...data, app_id: 'other-app'}, origin: location.origin,
        }));
        window.dispatchEvent(new MessageEvent('message', {
            data: {...data, type: 'other-message'}, origin: location.origin,
        }));
    }""")
    assert page.evaluate('visibilityProbe.closedViews') == []


def test_visibility_scroll_request(visibility_probe):
    page = visibility_probe
    page.evaluate('visibilityProbe.props.scroll_to = true')
    page.wait_for_function('visibilityProbe.scrolls.length === 1')
    assert page.evaluate('visibilityProbe.props.scroll_to') is False
    page.evaluate("visibilityProbe.host.style.display = 'none'")
    page.wait_for_function('visibilityProbe.events.at(-1).visible === false')
    page.evaluate('visibilityProbe.props.scroll_to = true')
    page.wait_for_timeout(100)
    assert page.evaluate('visibilityProbe.scrolls.length') == 1
    page.evaluate("visibilityProbe.host.style.display = ''")
    page.wait_for_function('visibilityProbe.scrolls.length === 2')
    assert page.evaluate('visibilityProbe.props.scroll_to') is False
