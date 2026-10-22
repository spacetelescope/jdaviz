.. _export-viewers:
.. rst-class:: section-icon-mdi-content-save

*******
Viewers
*******

Allows exporting the current view in a Viewer as an image.  

.. note::
   The image size will be the exact size and state of the viewer (i.e. as if you took a screenshot of the viewer).  
   Confirm the viewer height and width before exporting.  

The image can be saved as either a ``.png`` or ``.svg``. 


API Access
==========

.. code-block:: python

   plg = jdaviz.plugins['Export']
   plg.viewer = 'Viewer Name'
   plg.viewer_format = 'png'
   plg.filename = 'my-viewer'
   plg.export()


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"save"}]
   :steps-json: [{"action": "show-sidebar", "value": "save", "delay": 1500, "caption": "Open the export sidebar"}]