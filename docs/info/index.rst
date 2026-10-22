.. _info:
.. rst-class:: section-icon-mdi-information-outline

************************
Data Information Tools
************************

Jdaviz provides tools to inspect and interact with your data:

.. toctree::
   :maxdepth: 1

   metadata 

- View FITS headers and other metadata associated with your loaded datasets.


.. toctree::
   :maxdepth: 1

    markers

- Place markers on images and spectra to mark points of interest and extract
  information at specific locations.


.. toctree::
   :maxdepth: 1

    logger

- View system messages, warnings, and errors from Jdaviz operations.


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"info"}]
   :steps-json: [{"action": "show-sidebar", "value": "info", "delay": 1500, "caption": "Open the info sidebar"}]