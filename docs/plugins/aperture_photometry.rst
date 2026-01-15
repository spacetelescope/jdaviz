.. _plugins-aperture_photometry:

********************
Aperture Photometry
********************

.. plugin-availability::

Perform photometry measurements within defined apertures.

Description
===========

The Aperture Photometry plugin performs simple aperture photometry for one or more objects
within interactively selected regions. It calculates flux, surface brightness, and various
statistics within the aperture, with optional background subtraction.

**Key Features:**

* Aperture photometry using drawn subsets
* Background subtraction (manual or from subset)
* Radial profile plotting and analysis
* Gaussian profile fitting
* Support for multiple datasets and apertures
* Unit conversion (flux to counts, magnitude)
* Export results to tables

Details
=======

Photometry Calculation
----------------------

The plugin uses `photutils <https://photutils.readthedocs.io>`_ to perform aperture
photometry. For each aperture, it calculates:

* **Flux statistics**: sum, mean, median, min, max, standard deviation
* **Aperture properties**: center position, area
* **Background**: subtracted value or calculated from background subset
* **Uncertainties**: propagated when available

For 3D data cubes (Cubeviz), photometry is performed on the current displayed slice.

Background Subtraction
----------------------

Background can be specified in two ways:

1. **Manual**: Enter a constant background value to subtract
2. **Subset**: Select a background region; median value computed automatically

The background value is subtracted from the aperture sum before computing final results.

Radial Profiles
---------------

The plugin can generate three types of radial profile plots:

* **Curve of Growth**: Cumulative flux as a function of radius
* **Radial Profile**: Azimuthally-averaged flux vs radius
* **Radial Profile (Raw)**: Individual pixel values vs radius

Optionally, a Gaussian model can be fit to radial profile data to characterize the
source PSF.

Unit Conversions
----------------

**Counts Conversion**:
If a counts conversion factor is provided, the plugin reports flux in both
original units and counts.

**Magnitude Conversion**:
If a flux scaling factor is provided, magnitude is calculated as:
$-2.5 * \text{log}(\text{flux} / \text{flux\_scaling})$

**Pixel Area**:
For surface brightness data (units like MJy/sr), pixel area in arcsec² must be
specified. This is auto-populated from metadata for JWST and HST images when available.

Limitations
-----------

* WCS distortions are ignored in aperture calculations
* Annulus regions cannot be used as apertures (but can be used for background)
* The displayed subset shape may not exactly match the aperture mask (photutils uses fractional pixels)
* For surface brightness units with varying pixel areas, convert to flux units first

UI Access
=========

.. wireframe-demo::
   :demo: plugins,plugins@1000:open-panel,plugins:select-data=Image 2
   :enable-only: plugins
   :plugin-name: Aperture Photometry
   :plugin-panel-opened: false
   :demo-repeat: false

Opening the Plugin
------------------

**Imviz/Cubeviz:**
  Click the :guilabel:`Aperture Photometry` icon in the plugin toolbar.

Workflow
--------

1. **Load data** into Imviz or Cubeviz
2. **Draw aperture region(s)** using subset tools (see :ref:`imviz-defining-spatial-regions` or :ref:`cubeviz-defining-spatial-regions`)
3. **Select dataset** from :guilabel:`Data` dropdown
4. **Select aperture** from :guilabel:`Aperture` dropdown
5. **Configure background** (optional):

   * For manual: Enter value in :guilabel:`Background value` field
   * For subset: Draw background region and select from :guilabel:`Background` dropdown

6. **Set additional parameters**:

   * :guilabel:`Pixel area` (auto-populated for JWST/HST when applicable)
   * :guilabel:`Counts conversion factor` (optional)
   * :guilabel:`Flux scaling` (optional, for magnitude calculation)

7. **Select plot type** from :guilabel:`Plot Type` dropdown
8. **Toggle Gaussian fitting** if desired
9. Click :guilabel:`Calculate` to perform photometry

Batch Processing
----------------

The plugin supports batch processing to compute photometry for multiple
dataset/aperture combinations. Enable :guilabel:`Multiselect` mode to:

* Select multiple datasets
* Select multiple apertures
* Calculate photometry for all combinations at once

Results are added to the table for each combination.

Results Display
---------------

After calculation:

* **Radial profile plot** appears (if plot type selected)
* **Photometry results** display below the Calculate button
* **Results table** populates with row for this measurement
* **Gaussian fit results** shown (if enabled)

API Access
==========

Accessing the Plugin
--------------------

.. code-block:: python

    from jdaviz import Imviz

    imviz = Imviz()
    imviz.show()
    imviz.load('image.fits', format='Image')

    # Access plugin
    plg = imviz.plugins['Aperture Photometry']

Basic Usage
-----------

.. code-block:: python

    # Set parameters
    plg.dataset = 'image[DATA]'
    plg.aperture = 'Subset 1'
    plg.background = 'Subset 2'  # Or use manual background

    # Calculate photometry
    results = plg.calculate_photometry()

    # Access results table
    table = plg.export_table()
    print(table)

Manual Background
-----------------

.. code-block:: python

    # Set manual background value
    plg.background_value = 100.5  # In data units
    plg.background = 'Manual'

    results = plg.calculate_photometry()

Batch Processing
----------------

.. code-block:: python

    # Enable multiselect
    plg.multiselect = True

    # Define batch options
    options = plg.unpack_batch_options(
        dataset=['image1[DATA]', 'image2[DATA]'],
        aperture=['Subset 1', 'Subset 2']
    )

    # Calculate for all combinations
    plg.calculate_batch_photometry(options=options)

    # Export all results
    table = plg.export_table()

Override Parameters
-------------------

.. code-block:: python

    # Override plugin values for single calculation
    results = plg.calculate_photometry(
        dataset='other_image[DATA]',
        aperture='Subset 3',
        background='Subset 4',
        pixel_area=0.0025,  # arcsec^2
        counts_factor=1.5,
        add_to_table=True
    )

Fit Radial Profile
------------------

.. code-block:: python

    # Access fitted model
    models = plg.fitted_models

    # Fit can be triggered via plot
    plg.current_plot_type = 'Radial Profile'
    plg.fit_radial_profile()

Exporting Results
-----------------

.. code-block:: python

    # Get results table
    table = plg.export_table()

    # Write to file
    table.write('photometry_results.ecsv', overwrite=True)

    # Access specific columns
    fluxes = table['sum']
    backgrounds = table['background']
    centers = table['xcenter'], table['ycenter']

.. plugin-api-refs::
   :module: jdaviz.configs.imviz.plugins.aper_phot_simple.aper_phot_simple
   :class: SimpleAperturePhotometry

Example Notebooks
=================

* :gh-notebook:`ImvizExample.ipynb <ImvizExample>` - Imviz photometry example
* :gh-notebook:`CubevizExample.ipynb <CubevizExample>` - Cubeviz photometry example

See Also
========

* :ref:`Imviz Aperture Photometry <aper-phot-simple>` - Detailed Imviz-specific documentation
* :ref:`Cubeviz Aperture Photometry <cubeviz-aper-phot>` - Cubeviz-specific documentation
* :ref:`imviz-defining-spatial-regions` - Creating subsets for apertures
* `Photutils documentation <https://photutils.readthedocs.io>`_ - Underlying photometry library
