.. _loaders-source-astroquery:

.. rst-class:: section-icon-mdi-plus-box

:excl_platforms: mast


***************************
Loading from Astroquery
***************************

The Astroquery loader allows you to query and load data directly from astronomical archives.

.. note::
  Astroquery works by finding data whose footprint overlaps *at all* within the given search radius 
  around source coordinates using :class:`astroquery.mast.MastMissionsClass`. This occurs because
  :class:`astroquery.mast.MastMissionsClass` searches for observations  whose footprint contains the source coordinates 
  or within a given radius from the source. 
  
  The ``ra`` and ``dec`` you input are the central coordinates of that footprint, but that footprint could match the input radius 
  at the corner of the observation such that ``ra`` and ``dec`` are further away than the input radius. 
  Conversely, if the footprint is centered on the input source coordinates, then you can have astroquery matches 
  even within a vanishingly small radius.

  This is specific to :class:`astroquery.mast.MastMissionsClass`; virtual observatory services do not show this quirk.


Usage
=============

Query data from:

* MAST (Mikulski Archive for Space Telescopes)

  * JWST
  * HST 

* SDSS (Sloan Digital Sky Survey)
* Gaia

.. Check back for updates or `follow our GitHub repository <https://github.com/spacetelescope/jdaviz>`_
.. for announcements.

API Access
==========

.. code-block:: python

    import jdaviz as jd
    jd.show()

    # Using loaders API
    ldr = jd.loaders['astroquery']
    ldr.show()

    ldr.search_input = 'Source'
    ldr.source = 'M4'
    lr.coordframe = 'icrs'
    ldr.radius = 1 
    ldr.radius_unit = 'deg'

    ldr.telescope = 'JWST'
    ldr.max_results = 1000
    ldr.query_archive()


Input Modes
===========

The archive can be pointed at coordinates in one of three ways via the
``Input`` selector (``ldr.search_input``):

- **Source**: enter a source name or ``"[RA] [Dec]"`` coordinates manually.
- **Viewer**: use the center of a selected image viewer (optionally following
  pans/zooms).
- **Catalog**: run the cone search once for *every* row of a loaded
  source catalog and stack the results. This mode only appears once a catalog
  has been loaded into the app.

In ``Catalog`` mode, select the catalog with ``ldr.catalog`` and optionally
restrict the query to a subset of rows with ``ldr.catalog_subset``. Coordinates
can be taken two ways, controlled by ``ldr.catalog_col_type``:

- ``"sky_coords"`` (default): use the RA/Dec columns assigned when the catalog
  was loaded.
- ``"source_name"``: resolve a column of source names row-by-row via
  ``SkyCoord.from_name`` (one network request per row — slow for large
  catalogs). Select the column with ``ldr.catalog_name_col``. If not provided,
  the default choice is the user specified source ID column. If the source ID column
  is not a string, the default will be the first string column in the catalog.

The stacked results include a ``source_index`` column identifying which queried
source each returned row corresponds to. ``ldr.max_results`` caps the total
number of stacked rows and also stops the per-source loop early once that many
results have been collected, so it bounds how much querying is done rather than
truncating the final table.

.. code-block:: python

    ldr = jd.loaders['astroquery']
    ldr.search_input = 'Catalog'
    ldr.catalog = 'my_catalog'
    ldr.telescope = 'JWST'
    ldr.query_archive()


Since there are many options and the exposed options depend on previous selections, the best way 
to write a script to write a workflow loading from astroquery is to enable :ref:`userapi-api_hints`,
and interactively do a search in the UI and reproduce in a notebook cell:

.. .. guidestar-demo:: _static/jdaviz-wireframe.html
..    :js: jdaviz-wireframe-actions.js
..    :css: jdaviz-wireframe.css
..    :repeat: false
..    :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 0}, {"action": "select-dropdown", "value": "Source:astroquery", "delay": 0}, {"action": "highlight", "target": "#source-select", "delay": 0}, {"action": "pause", "delay": 1000}, {"action": "api-toggle", "delay": 1500, "caption": "Toggle the API code hint"}]

UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Source:astroquery", "delay": 1500, "caption": "Set source to astroquery"}]
