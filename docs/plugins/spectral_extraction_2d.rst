.. _plugins-spectral_extraction_2d:

************************
2D Spectral Extraction
************************

Extract 1D spectra from 2D spectroscopic data.

Description
===========

The 2D Spectral Extraction plugin extracts 1D spectra from 2D spectroscopic
data by summing or averaging across the spatial direction.

**Key Features:**

* Extract 1D from 2D spectra
* Configurable extraction aperture
* Background subtraction
* Trace following
* Uncertainty propagation

**Available in:** Specviz2d

UI Access
=========

Click the :guilabel:`Spectral Extraction` icon in the plugin toolbar to:

1. Define extraction aperture
2. Set background regions
3. Configure extraction parameters
4. Extract 1D spectrum

API Access
==========

.. code-block:: python

    plg = specviz2d.plugins['Spectral Extraction']
    plg.aperture_width = 5  # pixels
    plg.extract()

.. plugin-api-refs::
   :module: jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction
   :class: SpectralExtraction2D

See Also
========

* :ref:`specviz2d-plugins` - Specviz2d extraction documentation
