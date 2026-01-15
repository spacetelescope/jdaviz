.. _plugins-spectral_extraction_3d:

************************
3D Spectral Extraction
************************

.. plugin-availability::

Extract 1D spectra from 3D spectral cubes.

Description
===========

The 3D Spectral Extraction plugin collapses the spatial dimensions of a spectral
cube to produce a 1D spectrum. This is useful for extracting integrated spectra
over spatial regions or collapsing entire cubes.

**Key Features:**

* Extract 1D spectra from cubes
* Multiple extraction functions (Sum, Mean, Min, Max)
* Spatial region (aperture) support
* Wavelength-dependent apertures (cone extraction)
* Uncertainty propagation
* Background spectrum extraction

Details
=======

Extraction Functions
--------------------

The plugin supports several collapse operations:

* **Sum**: Total flux across spatial region (most common)
* **Mean**: Average flux per pixel
* **Min**: Minimum flux value
* **Max**: Maximum flux value

Sum is typically used for total flux, while Mean gives flux per unit area.

Spatial Regions (Apertures)
---------------------------

You can extract spectra from:

* **Entire cube**: All spatial pixels (no aperture)
* **Spatial subset**: Defined region of interest

Apertures can be circular, elliptical, rectangular, or any drawn subset.

Wavelength-Dependent Apertures
-------------------------------

For circular subsets with spatial axes in angular units, you can enable
**wavelength-dependent apertures** to create a cone that scales with wavelength:

$\text{radius}(\lambda) = \text{radius}_0 \times (\lambda / \lambda_0)$

where $\lambda_0$ is the reference wavelength (current slice by default).
This is useful for matching PSF size variations with wavelength.

Aperture Masking Methods
-------------------------

The plugin supports different aperture masking methods (see `photutils aperture documentation <https://photutils.readthedocs.io/en/stable/aperture.html#aperture-and-pixel-overlap>`_):

* **Center**: Use only pixels whose centers fall within the aperture
* **Exact**: Calculate exact overlap between aperture and pixels (slower)
* **Subpixel**: Subdivide pixels for approximate overlap calculation

Exact method provides most accurate results but is computationally expensive.
For most cases, center or subpixel methods are sufficient.

Note: Exact masking with Min/Max functions is not supported.

Uncertainty Propagation
-----------------------

When uncertainty data is available in the cube, uncertainties are automatically
propagated to the extracted 1D spectrum following standard error propagation rules.
For spatial sum, uncertainties add in quadrature. For mean, uncertainties are
scaled appropriately.

Background Extraction
---------------------

An optional background spectrum can be extracted from a separate spatial region
and scaled relative to the source aperture area. This is useful for background
subtraction in subsequent analysis.

UI Access
=========

.. wireframe-demo::
   :demo: plugins,plugins@1000:open-panel
   :enable-only: plugins
   :plugin-name: 3D Spectral Extraction
   :plugin-panel-opened: false
   :demo-repeat: false

Opening the Plugin
------------------

**Cubeviz:**
  Click the :guilabel:`3D Spectral Extraction` icon in the plugin toolbar.

Workflow
--------

1. **Load cube** into Cubeviz
2. **(Optional) Draw spatial region** for aperture
3. **Select dataset** from :guilabel:`Data` dropdown
4. **Select function** from :guilabel:`Function` dropdown
5. **Select aperture** from :guilabel:`Aperture` dropdown (or use :guilabel:`Entire Cube`)
6. **(Optional) For circular apertures**:

   * Enable :guilabel:`Wavelength dependent` if desired
   * Click :guilabel:`Adopt Current Slice` to set reference wavelength

7. **Select aperture masking method** from :guilabel:`Aperture masking method` dropdown
8. **Set output options**:

   * Output data label
   * Viewer to add spectrum to

9. Click :guilabel:`Extract` to create 1D spectrum

Background Extraction
---------------------

To extract a background spectrum:

1. Define a background region (separate subset)
2. Select background region from :guilabel:`Background` dropdown
3. Click :guilabel:`Extract Background` button

The background spectrum is scaled by the aperture area ratio and can be subtracted
from the source spectrum.

Results
-------

The extracted spectrum is:

* Added to the spectrum viewer
* Available in the data dropdown menus
* Can be analyzed with spectroscopic plugins (line analysis, model fitting, etc.)

API Access
==========

Accessing the Plugin
--------------------

.. code-block:: python

    from jdaviz import Cubeviz

    cubeviz = Cubeviz()
    cubeviz.show()
    cubeviz.load('cube.fits', format='3D Spectrum')

    # Access plugin
    plg = cubeviz.plugins['3D Spectral Extraction']

Basic Extraction
----------------

.. code-block:: python

    # Extract from entire cube
    plg.dataset = 'cube[FLUX]'
    plg.function = 'Sum'

    spectrum = plg.extract(add_data=True)

Aperture Extraction
-------------------

.. code-block:: python

    # Extract from spatial subset
    plg.aperture = 'Subset 1'
    plg.function = 'Sum'

    spectrum = plg.extract(add_data=True)

Wavelength-Dependent Aperture
-----------------------------

.. code-block:: python

    # Enable cone extraction
    plg.aperture = 'Subset 1'  # Must be circular
    plg.wavelength_dependent = True
    plg.reference_wavelength = 5000  # Angstroms

    spectrum = plg.extract(add_data=True)

Aperture Masking Method
-----------------------

.. code-block:: python

    # Use exact masking for highest accuracy
    plg.aperture_method = 'Exact'

    spectrum = plg.extract(add_data=True)

Background Subtraction
----------------------

.. code-block:: python

    # Extract source spectrum
    plg.aperture = 'Subset 1'
    source_spec = plg.extract(add_data=True)

    # Extract background spectrum
    plg.background = 'Subset 2'
    bg_spec = plg.extract_bg_spectrum(add_data=True)

    # Background is auto-scaled by aperture area ratio
    # Subtract in subsequent analysis

Custom Output
-------------

.. code-block:: python

    # Control output
    extraction.add_results.label = 'source_spectrum'
    extraction.add_results.viewer = 'spectrum-viewer'

    # Or get without adding
    spectrum = extraction.extract(add_data=False)

    # Access data
    wavelength = spectrum.spectral_axis
    flux = spectrum.flux
    uncertainty = spectrum.uncertainty

Batch Extraction
----------------

.. code-block:: python

    # Extract from multiple apertures
    apertures = ['Subset 1', 'Subset 2', 'Subset 3']

    for i, ap in enumerate(apertures, 1):
        plg.aperture = ap
        plg.add_results.label = f'spectrum_{i}'
        plg.extract(add_data=True)

.. plugin-api-refs::
   :module: jdaviz.configs.cubeviz.plugins.spectral_extraction.spectral_extraction
   :class: SpectralExtraction3D

Example Notebooks
=================

* :gh-notebook:`CubevizExample.ipynb <CubevizExample>` - Includes extraction examples

See Also
========

* :ref:`spectral-extraction` - Detailed Cubeviz extraction documentation
* :ref:`collapse` - Create 2D images from cubes
* :ref:`moment-maps` - Alternative spectral integration method
