.. _export-subsets:
.. rst-class:: section-icon-mdi-content-save

*******
Subsets
*******

After subsets have been created or manipulated, it is possible to export those subsets: 

- back into your Jupyter notebook,
- as a file.

Supported Formats
=================

Subsets can be exported as:

- REG 
- FITS 
- ECSV 

Depending on the subset, it is exported as either:

- an astropy :class:`region <https://astropy-regions.readthedocs.io/en/stable/index.html>`_ (spatial),
- a :class:`specutils.spectra.SpectralRegion <https://specutils.readthedocs.io/en/stable/api/specutils.SpectralRegion.html>`_ (spectral)


API Access
==========

.. code-block:: python

   plg = jd.plugins['Export']
   plg.subset = 'Subset 1'
   plg.subset_format = 'reg'
   plg.filename = 'my-subset'
   plg.export()


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"save"}]
   :steps-json: [{"action": "show-sidebar", "value": "save", "delay": 1500, "caption": "Open the export sidebar"}]

Top-Level API Access
====================

To access subsets in a Jupyter notebook, you can export the region(s) by directly calling the `Subset Tools` plugin:

.. code-block:: python 
   regions = jd.plugins["Subset Tools"].get_regions()

This returns a dictionary where each subset is given as either an astropy :class:`region` or :class:`specutils.spectra.SpectralRegion`.
