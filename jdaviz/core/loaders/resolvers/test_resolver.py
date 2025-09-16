from jdaviz.app import Application
from jdaviz.core.loaders.resolvers.resolver import BaseResolver


# Create a minimal test class that mimics the resolver behavior
# without this we get an error when attempting to use BaseResolver directly
class TestBaseResolver(BaseResolver):
    template = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def test_server_is_remote_callback():
    # Create app instance
    app = Application()

    # Test the sync
    test_obj = TestBaseResolver(app=app)
    settings = app.state.settings

    # Check default
    assert settings.get('server_is_remote') is False
    assert settings.get('server_is_remote') == test_obj.server_is_remote

    settings['server_is_remote'] = True
    assert settings.get('server_is_remote') == test_obj.server_is_remote

    # Ensure setting test_obj.server_is_remote does not backpropagate
    # (this behavior could change)
    test_obj.server_is_remote = False
    assert settings.get('server_is_remote') != test_obj.server_is_remote
