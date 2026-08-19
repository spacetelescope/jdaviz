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

.. guidestar-demo:: _static/jdaviz-wireframe.html
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


Clear Cache (standalone application only)
=========================================

In the standalone application, files downloaded directly from MAST (Mikulski Archive for Space Telescopes) are saved in 
``$HOME/.cache/.jdaviz``. 

Empty folders are automatically deleted from this cache when you close the Jdaviz application. 

To save disk storage, when you close the Jdaviz application, Jdaviz will automatically delete files if they were downloaded 
more than 4 weeks before the current application session. You must move these files if you do not want them deleted. 

If you wish to delete the whole cache, click on the ``Cache`` dropdown in the Jdaviz application taskbar and select ``Empty Jdaviz Cache``. 

.. note::
   The files at HTTPS and HTTP URLs are downloaded via ``astropy`` and saved in ``$HOME/.cache/.astropy``. 
   Any files downloaded via ``astropy``, even outside Jdaviz are saved there; therefore, we do not automatically or 
   manually clear this cache. 
   See `astropy.utils.data <https://docs.astropy.org/en/stable/utils/data.html>`_  for details on this cache.

.. note::
   Downloading from URL in a local Jupyter session (jupyter notebook/lab or via command line) 
   will save the files in the current working directory of the session. 