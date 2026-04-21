.. _plugins-gaussian_smooth:
.. rst-class:: section-icon-mdi-tune-variant

***************
Gaussian Smooth
***************
.. plugin-availability::

Smooth spectra or cubes using a Gaussian kernel.

Description
===========

Gaussian Smooth convolves a Gaussian function (kernel) with a Spectrum data object
to smooth the data, reducing noise while preserving overall spectral features.
The convolution requires a Gaussian standard deviation value
(in pixels) which can be entered into the :guilabel:`Standard deviation`
field in the plugin. Smoothing can be applied along the spectral axis or spatial axes
(in the case of a spectral cube).

A new Spectrum object is generated and can be added to any spectrum viewers.
The object can also be selected and shown in the viewers via the
viewer data menus.

**Key Features:**

* Smooth 1D spectra or 3D cubes
* Configurable smoothing width (stddev)
* Spectral or spatial axis smoothing
* Uncertainty propagation
* Preview before applying

UI Access
=========

.. wireframe-demo::
   :demo: plugins,plugins@1000:open-panel
   :enable-only: plugins
   :plugin-name: Gaussian Smooth
   :demo-repeat: false

Click the :guilabel:`Gaussian Smooth` icon in the plugin toolbar to open.

API Access
==========

.. code-block:: python

    plg = jd.plugins['Gaussian Smooth']
    plg.dataset = 'spectrum'
    plg.stddev = 3.0  # Standard deviation in pixels
    plg.smooth()

.. plugin-api-refs::
   :module: jdaviz.configs.default.plugins.gaussian_smooth.gaussian_smooth
   :class: GaussianSmooth
