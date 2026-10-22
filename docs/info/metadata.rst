.. _info-metadata:
.. rst-class:: section-icon-mdi-information-outline

********
Metadata
********


This plugin allows viewing of any metadata associated with the selected data.

If the data is loaded from multi-extension FITS that contains a primary header,
you will also see a :guilabel:`Show primary header` toggle, when enabled, would
display just the primary header metadata.


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"info"}]
   :steps-json: [{"action": "show-sidebar", "value": "info", "delay": 1500, "caption": "Open the info sidebar"}, {"action": "select-tab", "value": "Metadata", "delay": 1500, "caption": "Select the Metadata tab"}]

API Access
==========


.. code-block:: python

   plg = jdaviz.plugins['Metadata']
   plg.dataset = 'DataSet Name'
   plg.metadata
