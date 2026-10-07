import os
import subprocess
import sys
from unittest.mock import Mock

import pytest

import jdaviz
from jdaviz.core.template_mixin import show_widget

# Run in a subprocess: importing the Solara server (as the CLI does) patches
# ipywidgets and IPython globally, which would leak into the other tests.
CLI_POPOUT_SCRIPT = '''
import solara.server.starlette  # noqa: F401
from solara.server.kernel import Kernel
from solara.server.kernel_context import VirtualKernelContext
import ipywidgets as w
from ipypopout import PopoutButton
from jdaviz.core.template_mixin import show_widget


class Widget:
    popout_button = PopoutButton(w.Label())
    state = type('State', (), {'in_notebook': True})()


with VirtualKernelContext(id='test', session_id='test', kernel=Kernel()):
    show_widget(Widget, loc='popout', title='Test')
print('in_notebook', Widget.state.in_notebook)
'''


def test_cli_popout():
    env = {k: v for k, v in os.environ.items() if k != 'JDAVIZ_SKIP_DISPLAY'}
    # Make the child import the same jdaviz as this process, rather than
    # whatever install the interpreter resolves (e.g. another checkout).
    root = os.path.dirname(os.path.dirname(jdaviz.__file__))
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [root, env.get('PYTHONPATH')]))
    result = subprocess.run([sys.executable, '-c', CLI_POPOUT_SCRIPT],
                            capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    assert 'in_notebook False' in result.stdout


def test_fake_ipython_without_context(monkeypatch):
    monkeypatch.delenv('JDAVIZ_SKIP_DISPLAY', raising=False)
    monkeypatch.setattr('IPython.get_ipython', lambda: type('FakeIPython', (), {})())

    with pytest.raises(RuntimeError, match=r'unsupported shell \(FakeIPython\)'):
        show_widget(Mock(), loc='popout', title='Test')
