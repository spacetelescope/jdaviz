.. _viewers-spectrum_3d:
.. rst-class:: section-icon-mdi-plus-box

************
3D Spectrum
************

Documentation coming soon.

Spatial subsets created in an Image viewer are not added to 3D Spectrum viewers
or offered as apertures or backgrounds for 3D Spectral Extraction. Create a
spatial subset in the 3D Spectrum viewer to apply it to a cube.

UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-tab", "value": "Viewer", "delay": 1500, "caption": "Select the Viewer tab"}, {"action": "select-dropdown", "value": "Viewer Type:3D Spectrum", "delay": 1500, "caption": "Set viewer type to 3D Spectrum"}]