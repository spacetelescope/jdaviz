:excl_platforms: mast

.. _loaders-source-astroquery:

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

.. wireframe-demo::
   :demo: loaders,loaders:select-dropdown=Source:astroquery
   :enable-only: loaders
   :demo-repeat: false

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


Since there are many options and the exposed options depend on previous selections, the best way to write a script to write a workflow loading from astroquery is to enable :ref:`userapi-api_hints`,
and interactively do a search in the UI and reproduce in a notebook cell:

.. wireframe-demo::
   :initial: loaders,loaders:select-tab=Data,loaders:select-dropdown=Source:astroquery
   :demo: loaders:api-toggle
   :enable-only: loaders
   :demo-repeat: true