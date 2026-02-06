"""
Socket cleanup utilities for pytest.

This module provides cleanup functions to close leaked HTTP connections that
can prevent pytest-xdist workers from exiting cleanly (exit code 143).
"""

import atexit
import gc

# Track if cleanup has been registered with atexit
_atexit_registered = False


def cleanup_leaked_sockets():
    """
    Close any leaked HTTP/SSL connections.

    This targets a recurring issue where astroquery (particularly Gaia) leaves
    SSL sockets open, which prevents pytest-xdist workers from exiting cleanly,
    causing exit code 143 (SIGTERM).

    The cleanup strategy is multi-layered:
    1. Close astroquery.gaia.Gaia's internal connection handler
    2. Close all requests.Session objects (closes their connection pools)
    3. Close all urllib3 PoolManager and ConnectionPool objects directly
    4. Close any remaining raw sockets as a last resort
    5. Trigger garbage collection to release file descriptors
    """
    # Layer 0: Close Gaia's internal connection handler specifically
    # Gaia uses a TAP+ service with its own connection management
    try:
        from astroquery.gaia import Gaia
        # Gaia has a _Tap__connHandler that holds the connection
        if hasattr(Gaia, '_Tap__connHandler'):
            conn_handler = Gaia._Tap__connHandler
            if conn_handler is not None:
                # Try to close any session on the connection handler
                if hasattr(conn_handler, '_TapConn__postConnHandler'):
                    post_handler = conn_handler._TapConn__postConnHandler
                    if post_handler is not None and hasattr(post_handler, 'close'):
                        try:
                            post_handler.close()
                        except Exception:
                            pass
                if hasattr(conn_handler, '_TapConn__getConnHandler'):
                    get_handler = conn_handler._TapConn__getConnHandler
                    if get_handler is not None and hasattr(get_handler, 'close'):
                        try:
                            get_handler.close()
                        except Exception:
                            pass
    except ImportError:
        pass
    except Exception:
        pass

    # Layer 1: Close all requests.Session objects
    try:
        import requests
        for obj in gc.get_objects():
            try:
                if isinstance(obj, requests.Session):
                    obj.close()
            except (ReferenceError, TypeError, Exception):
                pass
    except ImportError:
        pass

    # Layer 2: Close urllib3 connection pools directly
    # This catches pools that may not be attached to a Session
    try:
        from urllib3 import PoolManager
        from urllib3.connectionpool import HTTPConnectionPool
        for obj in gc.get_objects():
            try:
                if isinstance(obj, PoolManager):
                    obj.clear()
                elif isinstance(obj, HTTPConnectionPool):
                    obj.close()
            except (ReferenceError, TypeError, Exception):
                pass
    except ImportError:
        pass

    # Layer 3: Close raw sockets that are still open
    # This is the nuclear option for any remaining leaked sockets
    try:
        import socket
        for obj in gc.get_objects():
            try:
                if isinstance(obj, socket.socket):
                    # Only close if socket appears to be open
                    if obj.fileno() != -1:
                        obj.close()
            except (ReferenceError, TypeError, OSError, Exception):
                pass
    except ImportError:
        pass

    # Final garbage collection to release file descriptors
    gc.collect()


def register_atexit_cleanup():
    """
    Register cleanup_leaked_sockets with atexit as a backup.

    This ensures sockets are cleaned up even if pytest hooks don't run
    or run too late. Safe to call multiple times.
    """
    global _atexit_registered
    if not _atexit_registered:
        atexit.register(cleanup_leaked_sockets)
        _atexit_registered = True


# Auto-register atexit handler when module is imported
register_atexit_cleanup()

