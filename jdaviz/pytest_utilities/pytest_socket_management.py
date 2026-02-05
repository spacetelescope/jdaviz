import requests.adapters


def cleanup_leaked_sockets():
    """
    Close any leaked SSL/HTTP connections from astroquery or other libraries.

    This targets a known issue where astroquery (particularly Gaia) can leave
    SSL sockets open, which prevents pytest-xdist workers from exiting cleanly,
    causing exit code 143 (SIGTERM).
    """
    # try:
    #     # Specifically close Gaia session if it exists
    #     # This is the most common source of lingering sockets
    #     try:
    #         from astroquery.gaia import Gaia
    #         if hasattr(Gaia, '_session') and Gaia._session is not None:
    #             try:
    #                 Gaia._session.close()
    #             except Exception:
    #                 pass
    #     except ImportError:
    #         pass

    # Close any lingering requests.Session objects (used by astroquery)
    try:
        # Check if _pool_cache exists before iterating
        if hasattr(requests.adapters.HTTPAdapter, '_pool_cache'):
            for adapter in requests.adapters.HTTPAdapter._pool_cache.values():
                try:
                    adapter.poolmanager.clear()
                except (AttributeError, Exception):
                    pass
    except (ImportError, AttributeError):
        pass
