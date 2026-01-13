.. _plugins-catalog_search:

**************

Catalog Search

**************

.. plugin-availability::

Query astronomical catalogs and overlay sources on images.

Description
===========

The Catalog Search plugin queries online astronomical catalogs (e.g., Gaia, 2MASS,
SDSS) and displays sources as markers on image viewers. This helps identify known
objects and cross-match with observations.

**Key Features:**

* Query multiple catalog services
* Cone search around image center
* Configurable search radius
* Marker overlay on images
* Export catalog results
* Source table display

**Available in:** Imviz

Details
=======

The plugin uses Virtual Observatory (VO) services to query catalogs. Search
radius can be adjusted, and results are displayed both as markers on the image
and in a sortable table.

UI Access
=========

Click the :guilabel:`Catalog Search` icon in the plugin toolbar to:

1. Select catalog (Gaia, 2MASS, SDSS, etc.)
2. Set search radius
3. Click :guilabel:`Search` to query catalog
4. View results as markers and table

API Access
==========

.. code-block:: python

    plg = imviz.plugins['Catalog Search']
    plg.catalog = 'Gaia DR3'
    plg.radius = 30  # arcseconds
    plg.search()

    # Export results
    table = plg.export_table()

.. plugin-api-refs::
   :module: jdaviz.configs.imviz.plugins.catalogs.catalogs
   :class: Catalogs

See Also
========

* :ref:`imviz-catalogs` - Detailed Imviz catalog documentation
