.. _export:
.. rst-class:: section-icon-mdi-content-save

***************
Exporting Data
***************

Jdaviz allows you to export various data products created during your analysis:

.. toctree::
   :maxdepth: 1

   viewers
   datasets
   subsets
   plugin_tables
   plugin_plots


UI Access
=========

.. wireframe-demo::
   :demo: save
   :enable-only: save
   :demo-repeat: false

API Access
==========

.. code-block:: python

   plg = jdaviz.plugins['Export']
   plg.dataset = 'my-dataset'
   plg.dataset_format = 'FITS'
   plg.export()

Since there are many options and the exposed options depend on previous selections, the best way to explore API options is to enable :ref:`userapi-api_hints`:

.. wireframe-demo::
   :initial: save
   :demo: pause@1000,save:api-toggle
   :enable-only: save
   :demo-repeat: true


See Also
========

- :doc:`../save_state` - For general information on saving your work
