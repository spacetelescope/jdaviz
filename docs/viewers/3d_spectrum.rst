.. _viewers-spectrum_3d:
.. rst-class:: section-icon-mdi-plus-box

************
3D Spectrum
************

3D Spectrum viewers show data loaded with `format = 3D Spectrum`. 
Much of the functionality is available both from the application GUI and from the Jupyter notebook using API calls. 


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-tab", "value": "Viewer", "delay": 1500, "caption": "Select the Viewer tab"}, {"action": "select-dropdown", "value": "Viewer Type:3D Spectrum", "delay": 1500, "caption": "Set viewer type to 3D Spectrum"}]