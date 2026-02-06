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
    sockets open, which prevents pytest-xdist workers from exiting cleanly,
    causing exit code 143 (SIGTERM).

    This function closes HTTPSConnection objects found via gc, which is the
    actual source of leaked sockets. We target HTTPSConnection (and
    HTTPConnection) rather than raw sockets because closing the connection
    object properly tears down the SSL layer and socket.
    """
    # Import http.client to check for connection types
    try:
        import http.client
    except ImportError:
        gc.collect()
        return

    # Find and close any lingering HTTP(S) connections
    # These are the actual source of socket leaks from Gaia/astroquery
    gc.collect()  # First collect to get accurate object list

    for obj in gc.get_objects():
        try:
            if isinstance(obj, (http.client.HTTPSConnection,
                                http.client.HTTPConnection)):
                # Close the connection - this properly tears down socket + SSL
                try:
                    obj.close()
                except Exception:
                    pass
        except (TypeError, ReferenceError):
            # Object may have been collected or is a weird type
            pass

    # Final gc to release any file descriptors
    gc.collect()
