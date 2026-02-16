"""
Socket cleanup utilities for pytest.

This module provides cleanup functions to close leaked HTTP connections that
can prevent pytest-xdist workers from exiting cleanly (exit code 143).
"""
import gc
import sys


def cleanup_leaked_sockets():
    """
    Close leaked HTTP/SSL connections that prevent clean pytest-xdist exit.

    Gaia's TAP+ service (and potentially other HTTP clients) can leave SSL
    sockets open, which prevents pytest from exiting cleanly (whether xdist or not).

    This function closes HTTPSConnection objects found via gc, which is the
    actual source of leaked sockets. We target HTTPSConnection (and
    HTTPConnection) rather than raw sockets because closing the connection
    object properly tears down the SSL layer and socket.

    Notes
    -----
    The order of operations differs by Python version. This is due to changes
    in how unraisable exceptions from finalizers are handled in Python 3.13+.
     - Python 3.13+: We close connections BEFORE gc.collect() to prevent
       unraisable exceptions from finalizers. This allows us to clean up
       connections without triggering warnings.
     - Python < 3.13: We need gc.collect() first to make objects visible,
       then close them, then collect again to finalize.
    """
    try:
        import http.client
        import ssl
    except ImportError:
        gc.collect()
        return

    is_py313_plus = sys.version_info >= (3, 13)

    if is_py313_plus:
        # Python 3.13+: Close connections BEFORE gc.collect() to prevent
        # unraisable exceptions from finalizers.
        _close_http_connections(http.client, ssl)
        gc.collect()
    else:
        # Python < 3.13: Need gc.collect() first to make objects visible,
        # then close them, then collect again to finalize.
        gc.collect()
        _close_http_connections(http.client, ssl)
        gc.collect()


def _close_http_connections(http_client, ssl):
    """
    Close all HTTP(S) connections found in gc.get_objects().

    Parameters
    ----------
    http_client : module
        The http.client module.
    ssl : module
        The ssl module.
    """
    for obj in gc.get_objects():
        try:
            if isinstance(obj, (http_client.HTTPSConnection,
                                http_client.HTTPConnection)):
                try:
                    obj.close()
                except (OSError, ssl.SSLError):
                    # Close failed; ignore and continue.
                    pass
        except (TypeError, ReferenceError, AttributeError):
            # Object may have been collected or is a weird type; ignore.
            pass
