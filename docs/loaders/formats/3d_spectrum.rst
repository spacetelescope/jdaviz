.. _loaders-format-3d-spectrum:
.. rst-class:: section-icon-mdi-plus-box

:data-types: 3d

***************************
3D Spectrum Format
***************************

Load three-dimensional spectroscopic data cubes.

.. note::
    Only a single cube can be displayed in an instance of Jdaviz at a given time.
    To open a second cube, you must first initiate a second instance of Jdaviz.


Overview
========

The 3D Spectrum format is used for loading spectroscopic data cubes where flux varies
along three dimensions - typically two spatial dimensions and one spectral dimension.

Usage
=====

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Load a 3D spectrum cube
    jdaviz.load('cube.fits', format='3D Spectrum')

Data Requirements
=================

The data should be a 3D array where:

- Two axes represent spatial dimensions (X, Y positions on sky)
- One axis represents the spectral dimension (wavelength/frequency)
- Pixel values represent flux measurements

This format is commonly used for Integral Field Unit (IFU) spectroscopy data.

Supported File Formats
======================

- FITS files with 3D data cubes
- JWST MIRI and NIRSpec IFU data (s3d files)
- Other IFU instrument data cubes


Data Parsing
============

Cube data must be parsable as a
:class:`~specutils.Spectrum` object. :class:`~specutils.Spectrum` supports 3D cubes
and allows the Python-level interface and parsing tools to
be defined in ``specutils`` instead of being duplicated in Jdaviz.
:class:`~specutils.Spectrum` objects are very flexible in their capabilities, however,
and hence should address most astronomical spectrum use cases.
If you are creating your own data products, please read the page :ref:`configs_create_products`.

For the best experience, 3D Spectrum loaded into Jdaviz should contain valid WCS keywords. 
For more information on how Spectrum uses WCS, please go to the the `Spectrum defining WCS section <https://specutils.readthedocs.io/en/stable/spectrum.html#defining-wcs>`_.
To check if your FITS file contains valid WCS keywords, please use `Astropy WCS validate <astropy.wcs.validate>`.
For an example on loading a cube with valid WCS keywords, please see the :ref:`_3dcube-import` section below.

Loading data without WCS is also possible as long as they are compatible with :class:`~specutils.Spectrum`.
However, not all plugins will work with this data.

.. _3dcube-import:

Importing data
==============

By default, the Jdaviz importer will attempt to parse and find the Flux, Uncertainty, and 
Data Quality (DQ) cubes within the loaded file. When loading a file in via the UI, these will populate in
the Importer section when you load data. Here, you have the option to change the data labels, viewer names, and 
extension location of each data cube.  

In the API, these can be changed when loading a file using the loaders plugins:

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Load a 3D spectrum cube
    ldr = jdaviz.loaders['file']
    ldr.filepath = 'cube.fits'
    ldr.format = '3D Spectrum'

    ldr.importer.extension = '1: SCI'
    ldr.importer.data_label = '3D cube flux'
    ldr.importer.viewer.crete_new = '3D Spectrum'
    ldr.importer.viewer.new_label = '3D cube flux viewer'

    ldr.importer.unc_extension = '2: ERR'
    ldr.importer.unc_data_label = '3D cube uncertainty'
    ldr.importer.viewer.crete_new = '3D Spectrum'
    ldr.importer.viewer.new_label = '3D cube err viewer'

    ldr.importer.dq_extension = '3: DQ'
    ldr.importer.dq_data_label = '3D cube dq'
    ldr.importer.dq_add_to_flux_viewer = True

Additionally, Jdaviz can auto extract a 1D spectrum from the entire cube. 
Toggle the `Extract 1D Spectrum` toggle under the `Extracted Spectrum` section of the loader to turn on/off this feature.
In the API, it can be called:

.. code-block:: python
    
    ldr.importer.auto_extract = True 
    ldr.importer.function = 'Sum'
    ldr.importer.ext_dat_label = '3D cube extracted spectrum'
    ldr.importer.ext_viewer.create_new = '1D Spectrum'
    ldr.importer.ext_viewer.new_label = '3D cube extracted spectrum'

    ldr.load()

The indicators that the load machinery looks for in each HDU to populate the viewers are below 
(note that in all cases, header values are converted to lower case):

    - Flux viewer: ``hdu.name`` is in the set ``['flux', 'sci']``
    - Uncertainty viewer: ``hdu.header.keys()`` includes "errtype" or ``hdu.name``
      is in the set ``['ivar', 'err', 'var', 'uncert']``
    - Loaded but not displayed: ``hdu.data.dtype`` is `int`, `numpy.uint` or `numpy.uint32`, or
      ``hdu.name`` is in the set ``['mask', 'dq']``


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Format:3D Spectrum", "delay": 1000, "caption": "Set format to 3D Spectrum"}, {"action": "highlight", "target": "#format-select", "delay": 1500}]

See Also
========

.. - :doc:`../../cubeviz/displaycubes` - For information on displaying spectral cubes
- :doc:`../../plugins` - For extracting spectra from cubes and creating moment maps
