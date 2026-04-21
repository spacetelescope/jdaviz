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

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action":"show-sidebar","value":"loaders","delay":1500},{"action":"select-dropdown","value":"Source:virtual observatory","delay":1000},{"action":"highlight","target":"#source-select","delay":1500}]

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


Since there are many options and the exposed options depend on previous selections, the best way to write a script to write a workflow loading from astroquery is to enable :ref:`userapi-api_hints`,
and interactively do a search in the UI and reproduce in a notebook cell:

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action":"show-sidebar","value":"loaders","delay":0},{"action":"select-tab","value":"Data","delay":0},{"action":"select-dropdown","value":"Source:virtual observatory","delay":0},{"action":"api-toggle","delay":1500}]
