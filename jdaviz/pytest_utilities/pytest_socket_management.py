import gc
import requests


def cleanup_leaked_sockets():
    """
    Close any leaked HTTP connections.

    This targets a recurring issue where astroquery (or others) can leave
    SSL sockets open, which prevents pytest (workers) from exiting cleanly,
    causing exit code 143 (SIGTERM).
    """
    # Find and close all requests.Session objects in memory.
    # This is the general solution - Session.close() properly closes all
    # underlying adapters and their urllib3 connection pools.
    for obj in gc.get_objects():
        try:
            if isinstance(obj, requests.Session):
                obj.close()
        except (ReferenceError, TypeError):
            # Object deleted during iteration or not comparable
            pass

    # Trigger garbage collection to release file descriptors
    gc.collect()
