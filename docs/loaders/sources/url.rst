.. _loaders-source-url:

:excl_platforms: mast

*******************
Loading from URL
*******************

The URL loader allows you to load data directly from remote URLs.

Usage
=====

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Using load() directly
    jdaviz.load('https://example.com/data.fits', format='1D Spectrum')

    # Using loaders API
    ldr = jdaviz.loaders['url']
    ldr.url = 'https://example.com/data.fits'
    ldr.format = '1D Spectrum'
    ldr.load()

Supported Protocols
===================

The URL loader supports:

- HTTP and HTTPS URLs
- FTP URLs
- Data URLs

The file at the URL should be in one of the supported formats (FITS, ASDF, etc.).

See :ref:`loaders-formats` for information on available data formats.
