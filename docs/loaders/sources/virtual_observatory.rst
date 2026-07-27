.. _loaders-source-vo:

.. rst-class:: section-icon-mdi-plus-box

:excl_platforms: mast

*********************************
Loading from Virtual Observatory
*********************************

The Virtual Observatory (VO) loader allows you to access data through VO protocols
using a simple cone search.

.. note::
    This feature is currently in development. Stay tuned for updates!

These protocols allow seamless access to astronomical data across multiple archives
using standardized interfaces.


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Source:virtual observatory", "delay": 1000, "caption": "Set source to virtual observatory"}, {"action": "highlight", "target": "#source-select", "delay": 1500}]

API Access
==========

.. code-block:: python

    import jdaviz as jd
    jd.show()

    # Using loaders API
    ldr = jd.loaders['virtual observatory']
    ldr.show()

    ldr.source = 'M4'
    ...
    ldr.query_archive()


Input Modes
===========

Like the :doc:`astroquery` loader, the VO loader can be pointed at coordinates via the
``Input`` selector (``ldr.input_select``): **Source** (manual name/coordinates),
**Viewer** (viewer center), or **Catalog**. In ``Catalog`` mode the selected VO
resource is queried once for every row of a loaded source catalog and the
results are stacked with a ``source_index`` column identifying the originating
source. Use ``ldr.catalog`` to pick the catalog and ``ldr.catalog_subset`` to
optionally restrict the query to a subset of rows. Coordinates can come from the
catalog's RA/Dec columns (``ldr.catalog_col_type = 'sky_coords'``) or from
resolving a retained name column (``ldr.catalog_col_type = 'source_name'`` with
``ldr.catalog_name_col``, see :doc:`astroquery` for more details.). As with :doc:`astroquery`,
``ldr.max_results`` bounds the per-source loop, stopping once that many stacked rows
have been collected.

.. code-block:: python

    ldr = jd.loaders['virtual observatory']
    ldr.input_select = 'Catalog'
    ldr.catalog = 'my_catalog'
    ldr.waveband = 'optical'
    ldr.resource = ...
    ldr.query_archive()


Since there are many options and the exposed options depend on previous selections, the best way to write a script to write a workflow loading from the virtual observatory is to enable :ref:`userapi-api_hints`,
and interactively do a search in the UI and reproduce in a notebook cell:

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 0}, {"action": "select-tab", "value": "Data", "delay": 0}, {"action": "select-dropdown", "value": "Source:virtual observatory", "delay": 0}, {"action": "api-toggle", "delay": 1500, "caption": "Toggle the API code hint"}]