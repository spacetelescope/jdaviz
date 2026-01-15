:excl_platforms: mast

.. _loaders-source-vo:

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

.. wireframe-demo::
   :demo: loaders,loaders:select-tab=Data,loaders:select-dropdown=Source:VO
   :enable-only: loaders
   :demo-repeat: false

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

.. wireframe-demo::
   :initial: loaders,loaders:select-tab=Data,loaders:select-dropdown=Source:virtual observatory
   :demo: loaders:api-toggle
   :enable-only: loaders
   :demo-repeat: true