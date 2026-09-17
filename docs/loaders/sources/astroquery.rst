.. _loaders-source-astroquery:

.. rst-class:: section-icon-mdi-plus-box

:excl_platforms: mast


***************************
Loading from Astroquery
***************************

The Astroquery loader allows you to query and load data directly from astronomical archives.

.. note::
    This feature is currently in development. Stay tuned for updates!

Planned Usage
=============

Future support will include querying data from:

- MAST (Mikulski Archive for Space Telescopes)
- SDSS (Sloan Digital Sky Survey)
- Other archives supported by Astroquery

Check back for updates or `follow our GitHub repository <https://github.com/spacetelescope/jdaviz>`_
for announcements.

UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Source:astroquery", "delay": 1500, "caption": "Set source to astroquery"}]

API Access
==========

.. code-block:: python

    import jdaviz as jd
    jd.show()

    # Using loaders API
    ldr = jd.loaders['astroquery']
    ldr.show()

    ldr.source = 'M4'
    ...
    ldr.query_archive()


Input Modes
===========

The archive can be pointed at coordinates in one of three ways via the
``Input`` selector (``ldr.input_select``):

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
    ldr.input_select = 'Catalog'
    ldr.catalog = 'my_catalog'
    ldr.telescope = 'JWST'
    ldr.query_archive()


Since there are many options and the exposed options depend on previous selections, the best way to write a script to write a workflow loading from astroquery is to enable :ref:`userapi-api_hints`,
and interactively do a search in the UI and reproduce in a notebook cell:

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 0}, {"action": "select-dropdown", "value": "Source:astroquery", "delay": 0}, {"action": "highlight", "target": "#source-select", "delay": 0}, {"action": "pause", "delay": 1000}, {"action": "api-toggle", "delay": 1500, "caption": "Toggle the API code hint"}]