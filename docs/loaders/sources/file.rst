.. _loaders-source-file:

.. rst-class:: section-icon-mdi-plus-box

:excl_platforms: mast

********************
Loading from File
********************

The file loader allows you to load data from local files on your system.

Usage
=====

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Using load() directly
    jdaviz.load('mydata.fits', format='1D Spectrum')

    # Using loaders API
    ldr = jdaviz.loaders['file']
    ldr.filename = 'mydata.fits'
    ldr.format = '1D Spectrum'
    ldr.load()

Supported File Types
====================

The file loader supports various astronomical data formats through the underlying libraries:

- FITS files (``.fits``, ``.fit``)
- ASDF files (``.asdf``)
- ECSV files (``.ecsv``)
- And more formats supported by ``astropy`` and ``specutils``

See :ref:`loaders-formats` for information on available data formats.

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action":"show-sidebar","value":"loaders","delay":1500},{"action":"select-dropdown","value":"Source:file","delay":1000},{"action":"highlight","target":"#source-select","delay":1500}]
