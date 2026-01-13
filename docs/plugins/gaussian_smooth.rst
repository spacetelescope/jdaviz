.. _plugins-gaussian_smooth:

***************

Gaussian Smooth

***************

.. plugin-availability::

Smooth spectra or cubes using a Gaussian kernel.

Description
===========

The Gaussian Smooth plugin applies Gaussian smoothing to spectroscopic data,
reducing noise while preserving overall spectral features. Smoothing can be applied
along the spectral axis or spatial axes.

**Key Features:**

* Smooth 1D spectra or 3D cubes
* Configurable smoothing width (stddev)
* Spectral or spatial axis smoothing
* Uncertainty propagation
* Preview before applying

**Available in:** Specviz, Cubeviz

UI Access
=========

Click the :guilabel:`Gaussian Smooth` icon in the plugin toolbar to open.

API Access
==========

.. code-block:: python

    plg = app.plugins['Gaussian Smooth']
    plg.dataset = 'spectrum'
    plg.stddev = 3.0  # Standard deviation in pixels
    plg.smooth()

.. plugin-api-refs::
   :module: jdaviz.configs.default.plugins.gaussian_smooth.gaussian_smooth
   :class: GaussianSmooth

See Also
========

* :ref:`gaussian-smooth` - Detailed Specviz documentation on Gaussian smoothing
