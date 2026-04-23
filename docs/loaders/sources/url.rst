.. _loaders-source-url:

.. rst-class:: section-icon-mdi-plus-box

:excl_platforms: mast

*******************
Loading from URL
*******************

The URL loader allows you to load data directly from remote URLs.

Supported Protocols
===================

The URL loader supports:

- HTTP and HTTPS URLs
- FTP URLs
- Data URLs

The file at the URL should be in one of the supported formats (FITS, ASDF, etc.).

See :ref:`loaders-formats` for information on available data formats.

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Source:url", "delay": 1000, "caption": "Set source to url"}, {"action": "highlight", "target": "#source-select", "delay": 1500}]

API Access
==========

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