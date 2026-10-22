.. _viewers:
.. rst-class:: section-icon-mdi-plus-box

*******
Viewers
*******

Jdaviz provides specialized viewers for different types of astronomical data.

.. toctree::
   :maxdepth: 1

   1d_spectrum
   2d_spectrum
   3d_spectrum
   image
   table
   scatter
   histogram
   extensions

.. _viewers-creation:

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

.. _viewers-creation-ui:

UI Access
---------

In the UI, viewers can be moved by clicking and dragging on the gray tab on the top left of each viewer.  
White dashed lines will appear as the viewer is dragged indicating where the viewer can be positioned in the app.
Unclick at the desired location.  

The viewer can be deleted by clicking on the ``x`` in the viewer tab.  This does **not** delete the data from the app.  
It only deletes the viewer. 

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-tab", "value": "Viewer", "delay": 1500, "caption": "Select the Viewer tab"}]

.. _viewers-datamenu:

Data Menus
==========

Each viewer has a legend in the top-right indicating what layers are currently displayed. Clicking on the legend opens a data menu where you can:

- Toggle visibility of individual layers
- Remove layers from the viewer or the app
- Rename viewers
- Add new layers 

For more information, see :ref:`data_menu`.

.. _viewers-focusmode:

Focus mode
==========
On the far right in the toolbar of each viewer, there is a ``focus mode`` button (indicated by |icon-focus|).
Clicking on this button expands the viewer to fill the application, 
and provides select plotting and visualization tools for each viewer.


.. _viewers-plotoptions:

Plot Options
============

Changing viewer or layer options is done through the :ref:`Plot Options <settings-plot_options>` plugin in the settings sidebar.