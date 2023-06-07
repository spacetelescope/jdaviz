.. _jdaviz_instrument_table:

**********
JWST Modes
**********

This tool is designed with instrument modes from the James Webb Space Telescope (JWST) in mind, but
the tool should be flexible enough to read in data from many astronomical telescopes.  The table below
summarizes Jdaviz file support specific to JWST instrument modes.

NIRSpec
=======

.. list-table:: JWST/NIRSpec Instrument Modes in Jdaviz
   :widths: 15 10 15 20
   :header-rows: 1

   * - Template Mode
     - File Type
     - Pipeline Level
     - Primary Configuration
   * - MOS
     - S2D
     - 2b,3
     - Mosviz
   * -
     - X1D
     - 2b,3
     - Specviz
   * - IFU
     - S3D
     - 2b,3
     - Cubeviz
   * -
     - X1D
     - 2b,3
     - Specviz
   * - FS
     - S2D
     - 2b,3
     - Specviz2d
   * -
     - X1D
     - 2b,3
     - Specviz
   * - BOTS
     - X1DINTS
     - --
     - No Support

NIRISS
======

.. list-table:: JWST/NIRISS Instrument Modes in Jdaviz
   :widths: 15 10 15 20
   :header-rows: 1

   * - Template Mode
     - File Type
     - Pipeline Level
     - Primary Configuration
   * - IMAGING
     - I2D
     - 2b,3
     - Imviz
   * - WFSS
     - X1D
     - 2b
     - Specviz
   * - AMI
     - AMINORM
     - --
     - No Support
   * - SOSS
     - X1DINTS
     - --
     - No Support

NIRCam
======

.. list-table:: JWST/NIRCam Instrument Modes in Jdaviz
   :widths: 15 10 15 20
   :header-rows: 1

   * - Template Mode
     - File Type
     - Pipeline Level
     - Primary Configuration
   * - Imaging
     - I2D
     - 2b,3
     - Imviz
   * - Coronagraphic Imaging
     - I2D
     - 2b,3
     - Imviz
   * - WFSS
     - X1D
     - 2b
     - Specviz
   * - Grism TSO
     - X1DINTS
     - --
     - No Support

MIRI
====

.. list-table:: JWST/MIRI Instrument Modes in Jdaviz
   :widths: 15 10 15 20
   :header-rows: 1

   * - Template Mode
     - File Type
     - Pipeline Level
     - Primary Configuration
   * - Imaging
     - I2D
     - 2b,3
     - Imviz
   * - Coronagraphic Imaging
     - I2D
     - 2b,3
     - Imviz
   * - LRS-slit
     - S2D
     - 2b,3
     - Specviz2d
   * -
     - X1D
     - 2b,3
     - Specviz
   * - LRS-slitless
     - X1DINTS
     - --
     - No Support
   * - MRS
     - S3D
     - 2b,3
     - Cubeviz
   * -
     - X1D
     - 2b, 3
     - Specviz
