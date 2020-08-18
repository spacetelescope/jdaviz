
.. image:: ../logos/mosviz.svg
   :width: 400

######
Mosviz
######

MOSviz is a quick-look analysis and visualization tool for multi-object spectroscopy (MOS). It is designed to work with pipeline output: spectra and associated images, or just with spectra. MOSviz is created to work with data from any telescope/instrument, but is built with the micro-shutter array (MSA) on the JWST/NIRSpec spectrograph and the JWST/NIRCam imager in mind. As such, MOSviz has some features specific to NIRSpec and NIRCam data.

The NIRSpec micro-shutter array (MSA) will produce ~100 spectra per pointing. Many users will perform surveys with the MSA that will result in data sets many spectra. This tool allows users to inspect the locations of astronomical sources within shutters, the location of background apertures in the observed field, the quality of the 2D spectra, and the quality of the 1D extracted spectra. It also often involves simple interactive measurements of quantities such as wavelengths, velocities, line fluxes, widths.

**Using MosViz**

.. toctree::
  :maxdepth: 2

  import_data
  navigation
  displayspectra
  plugins
  notebook
