"""Browser test for the viewer layout with real Imviz viewers.

The test serves ``docking_app.py`` with Solara and drives it with Playwright.
It is skipped unless ``pytest-playwright`` is installed; CI runs it in the
``browser`` tox environment.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

import pytest

# NOTE: Since this is an optional dependency, the regular test runs skip this module.
pytest.importorskip("pytest_playwright")

from playwright.sync_api import Page, expect


@pytest.fixture(scope='module')
def docking_server(tmp_path_factory):
    """Serve real widgets from a Solara subprocess on a free local port."""
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    url = f'http://127.0.0.1:{port}/'
    app = Path(__file__).with_name('docking_app.py')
    log_path = tmp_path_factory.mktemp('docking-server') / 'server.log'
    with log_path.open('w') as log:
        process = subprocess.Popen(
            [sys.executable, '-m', 'solara', 'run', str(app), '--host', '127.0.0.1',
             '--port', str(port), '--no-open', '--production'],
            stdout=log, stderr=subprocess.STDOUT,
            env={**os.environ, 'ASTROPY_ALLOW_INTERNET': 'False'},
        )
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail(f'Docking server exited:\n{log_path.read_text()}')
                try:
                    with urlopen(url, timeout=1):
                        break
                except (URLError, TimeoutError):
                    time.sleep(0.1)
            else:
                pytest.fail(f'Docking server did not start:\n{log_path.read_text()}')
            yield url
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def test_viewer_docking(page: Page, docking_server):
    """Dock, resize, cancel, maximize and close real viewers without remounting."""
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_viewport_size({'width': 1440, 'height': 1100})
    page.goto(docking_server)
    tab = page.locator('[data-viewer-tab-id="comparison"]')
    host = page.locator('.jdz-viewer-layout')
    expect(tab).to_be_visible(timeout=60000)
    expect(host.locator('.bqplot.figure')).to_have_count(2)
    page.evaluate('''() => {
        window.originalPlots = new Map(
            [...document.querySelectorAll('[data-viewer-id]')].map(element =>
                [element.dataset.viewerId, element.querySelector('.bqplot.figure')])
        );
    }''')

    def expect_plot_fills_figure(viewer_id, previous_width=None):
        # The layout sends no resize events; bqplot picks a new pane size up with
        # its own ResizeObserver and a 300 ms debounce. Imviz figures have zero
        # margins, so once redrawn the plot area equals the figure width.
        page.wait_for_function('''([id, previous]) => {
            const figure = document.querySelector(`[data-viewer-id="${id}"] .bqplot.figure`);
            const plot = +figure.querySelector('rect.plotarea_background').getAttribute('width');
            return figure.clientWidth !== previous && Math.abs(figure.clientWidth - plot) <= 1;
        }''', arg=[viewer_id, previous_width], timeout=3000)
        return page.evaluate(
            'id => document.querySelector(`[data-viewer-id="${id}"] .bqplot.figure`).clientWidth',
            viewer_id)

    def inspect():
        status = page.locator('#layout-status')
        previous = status.inner_text()
        page.locator('#inspect-layout').click()
        expect(status).not_to_have_text(previous)
        result = json.loads(status.inner_text())
        assert result['same_viewers'] and result['same_widgets']
        assert page.evaluate('''ids => ids.every(id => {
            const plot = originalPlots.get(id);
            return plot?.isConnected && document.querySelector(
                `[data-viewer-id="${id}"] .bqplot.figure`) === plot;
        })''', result['ids'])
        return result

    def drag_to(x, y):
        box = tab.bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        page.mouse.down()
        page.mouse.move(x, y, steps=12)
        expect(host.locator('.jdz-viewer-layout__drop')).to_be_visible()

    # Move the comparison viewer beside the entire remaining layout.
    comparison_width = expect_plot_fills_figure('comparison')
    area = host.bounding_box()
    drag_to(area['x'] + area['width'] - 2, area['y'] + area['height'] / 2)
    page.mouse.up()
    separator = host.locator('.jdz-viewer-layout__splitter[aria-orientation="vertical"]')
    expect(separator).to_have_count(1)
    assert inspect()['layout']['root']['type'] == 'row'
    expect_plot_fills_figure('comparison', comparison_width)

    before = inspect()['layout']
    separator.focus()
    page.keyboard.press('ArrowLeft')
    resized = inspect()['layout']
    assert resized != before

    drag_to(area['x'] + 2, area['y'] + area['height'] / 2)
    page.keyboard.press('Escape')
    page.mouse.up()
    expect(host.locator('.jdz-viewer-layout__drop')).to_have_count(0)
    assert inspect()['layout'] == resized

    pane = tab.locator('xpath=ancestor::section[1]')
    pane.get_by_role('button', name='Maximize viewer').click()
    assert inspect()['layout']['maximizedViewerId'] == 'comparison'
    pane.get_by_role('button', name='Restore viewer').click()
    assert inspect()['layout'] == resized

    main_width = expect_plot_fills_figure('imviz-0')
    pane.get_by_role('button', name='Close comparison', exact=True).click()
    expect(tab).to_have_count(0)
    expect_plot_fills_figure('imviz-0', main_width)
    final = inspect()
    assert final['ids'] == ['imviz-0']
    assert final['layout']['root']['viewers'] == ['imviz-0']
    assert not errors
