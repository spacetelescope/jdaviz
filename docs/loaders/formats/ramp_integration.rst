.. _loaders-format-ramp-integration:
.. rst-class:: section-icon-mdi-plus-box

:data-types: ramp-integration

***********************
Ramp Integration Format
***********************

Load extracted ramp integration profiles.

Overview
========

The Ramp Integration format is used for loading 1D integration profiles extracted
from JWST ramp data. These profiles show how the accumulated signal varies across
groups (reads) for a specific spatial extraction, useful for analyzing ramp fitting
and cosmic ray detection.

Usage
=====

.. code-block:: python

    import jdaviz as jd
    import numpy as np
    from astropy.nddata import NDDataArray

    jd.show()

    # Load an integration profile
    integration_data = np.array([100, 205, 310, 415])  # counts per group
    jd.load(integration_data, format='Ramp Integration',
            data_label='Extracted Integration')

Data Requirements
=================

The data should be a 1D or 3D array representing accumulated signal as a function
of group/read number:

Array Structure
---------------

- **1D array**: Direct sequence of values for each group (n_groups,)
- **3D array**: Collapsed spatial array (1, 1, n_groups) where the first two
  dimensions are spatial (reduced to 1×1) and the third is the group axis

The data can be provided as:

- Plain numpy array (``np.ndarray``)
- Astropy NDDataArray (``astropy.nddata.NDDataArray``) with optional metadata and units

When loading as a plain array, it will be automatically wrapped in an NDDataArray
for compatibility with the viewer.

Supported File Formats
======================

Ramp Integration data is typically not loaded from files but generated from:

- The Ramp Extraction plugin
- Programmatic extraction from ramp cubes
- Python numpy arrays or NDDataArray objects

The format accepts in-memory Python objects rather than file-based data.

Typical Workflow
================

Ramp integration profiles are usually created by spatially collapsing ramp data:

.. code-block:: python

    ramp_ext = jd.plugins['Ramp Extraction']
    ramp_ext.function = 'median'  # or 'mean', 'sum', etc.

    # Extract and export the integration profile
    integration = ramp_ext.extract()

The resulting integration profile can then be analyzed to examine:

- Signal accumulation linearity
- Jump detection artifacts
- Cosmic ray impacts
- Saturation effects

UI Access
=========

.. wireframe-demo::
   :demo: loaders,loaders@1000:select-dropdown=Format:Ramp Integration,loaders:highlight=#format-select
   :enable-only: loaders
   :demo-repeat: false

See Also
========

- :ref:`loaders-format-ramp` - Loading full ramp cubes
