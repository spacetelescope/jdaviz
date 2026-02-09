"""
Socket cleanup utilities for pytest.

This module provides cleanup functions to close leaked HTTP connections that
can prevent pytest-xdist workers from exiting cleanly (exit code 143).
"""
import gc


def cleanup_leaked_sockets():
    """
    Close leaked HTTP/SSL connections that prevent clean pytest-xdist exit.

    Gaia's TAP+ service (and potentially other HTTP clients) can leave SSL
    sockets open, which prevents pytest from exiting cleanly (whether xdist or not),
    causing exit code 143 (SIGTERM).

    This function closes HTTPSConnection objects found via gc, which is the
    actual source of leaked sockets. We target HTTPSConnection (and
    HTTPConnection) rather than raw sockets because closing the connection
    object properly tears down the SSL layer and socket.

    Notes
    -----
    The order of operations is critical on Python 3.13+:

    1. First, iterate gc.get_objects() and close all HTTP(S) connections
    2. Then run gc.collect() to finalize the now-closed objects

    If we call gc.collect() first, the finalizer runs on unclosed sockets,
    triggering unraisable exceptions. By closing connections explicitly first,
    the finalizer has nothing to do.
    """
    try:
        import http.client
        import ssl
    except ImportError:
        gc.collect()
        return

    for obj in gc.get_objects():
        try:
            if isinstance(obj, (http.client.HTTPSConnection,
                                http.client.HTTPConnection)):
                # Close the connection - this properly tears down socket + SSL
                try:
                    obj.close()
                except (OSError, ssl.SSLError):
                    # Underlying socket/SSL close failed; ignore and continue.
                    pass
        except (TypeError, ReferenceError, AttributeError):
            # Object may have been collected or is a weird type that raises
            # on isinstance checks; ignore these specific cases only.
            pass

    # Final gc to release any file descriptors
    gc.collect()
