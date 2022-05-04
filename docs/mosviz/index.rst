
.. image:: ../logos/mosviz.svg
   :width: 400

.. _mosviz:

######
Mosviz
######

Mosviz is a quick-look analysis and visualization tool for multi-object spectroscopy (MOS). It is designed to work with pipeline output: spectra and associated images, or just with spectra. Mosviz is created to work with data from any telescope/instrument, but is built with the micro-shutter array (MSA) on the JWST/NIRSpec spectrograph and the JWST/NIRCam imager in mind. As such, Mosviz has some features specific to NIRSpec and NIRCam data.

The NIRSpec micro-shutter array (MSA) will produce ~100 spectra per pointing. Many users will perform surveys with the MSA that will result in data sets containing many spectra. This tool allows users to inspect the locations of astronomical sources within shutters, the location of background apertures in the observed field, the quality of the 2D spectra, and the quality of the 1D extracted spectra. It also often involves simple interactive measurements of quantities such as wavelengths, velocities, line fluxes, widths.

Quickstart
----------

To load a sample `NIRISS Nirspec Data Set <https://stsci.box.com/shared/static/ovyxi5eund92yoadvv01mynwt8t5n7jv.zip>`_ into ``Mosviz`` in the standalone app, unzip the downloaded zip file and run::

    jdaviz mosviz /path/to/mosviz_nirspec_data_0.3/level3


Or to load in a Jupyter notebook, see the :gh-notebook:`MosvizExample` or :gh-notebook:`MosvizNIRISSExample`.


Using Mosviz
------------

.. toctree::
  :maxdepth: 2

  import_data
  navigation
  displayspectra
  plugins
  redshift
  notebook
