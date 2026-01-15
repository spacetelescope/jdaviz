.. _viewers:
.. rst-class:: section-icon-mdi-plus-box

*******
Viewers
*******

Jdaviz provides specialized viewers for different types of astronomical data.

.. toctree::
   :maxdepth: 1

   spectrum_1d
   spectrum_2d
   spectrum_3d
   image
   table
   scatter
   histogram
   extensions

Creating Viewers
================

By default, viewers are created automatically based on the data format you load:

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Automatically creates appropriate viewer
    jdaviz.load('spectrum.fits', format='1D Spectrum')

You can also create viewers programmatically:

.. code-block:: python

    # Create a new viewer
    viewer_creator = jdaviz.viewers['1D Spectrum']
    new_viewer = viewer_creator()

See the individual viewer pages for detailed usage information.

UI Access
---------

.. wireframe-demo::
   :demo: loaders,loaders:select-tab=Viewer
   :enable-only: loaders
   :demo-repeat: false

Data Menus
==========

Each viewer has a legend in the top-right indicating what layers are currently displayed. Clicking on the legend opens a data menu where you can:
- Toggle visibility of individual layers
- Remove layers from the viewer
- Rename viewers

For more information, see :ref:`data-menu`.

Plot Options
============

Changing viewer or layer options is done through the :ref:`Plot Options <settings-plot_options>` plugin in the settings sidebar.