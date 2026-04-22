.. _loaders-format-line-list:
.. rst-class:: section-icon-mdi-plus-box

:data-types: line-list

****************
Line List Format
****************

Load custom spectral line lists for identification and analysis.

Overview
========

The Line List format is used for importing custom lists of spectral lines that can
be overlaid on spectroscopic data for line identification and analysis. Line lists
specify the rest wavelengths of emission or absorption features and their labels.

.. warning::

   The Line Lists functionality is still under active development. For more information see
   :ref:`line-lists` in the plugins documentation.

Usage
=====

.. code-block:: python

    import jdaviz as jd
    from astropy.table import QTable
    from astropy import units as u

    # Create a line list table
    line_table = QTable({
        'linename': ['H-alpha', 'H-beta', 'O-III'],
        'rest': [6562.8, 4861.3, 5006.8] * u.AA
    })

    # Load the line list
    jd.load(line_table, format='Line List', line_list_label='Balmer Lines')

Data Requirements
=================

The data must be an ``astropy.table.QTable`` with the following structure:

Required Columns
----------------

- **linename**: Names/labels for each spectral line (string column)
- **rest**: Rest wavelengths of the lines, with astropy units attached (Quantity column)

The rest wavelengths must:

- Be positive values
- Have units (e.g., Angstroms, nanometers, GHz)
- Be in the rest frame (observed wavelength accounting will be handled by the tool)

Supported File Formats
======================

- ECSV files with the required columns
- Python ``astropy.table.QTable`` objects created in memory

When loading from a file, ensure the file can be read by ``astropy.table.QTable.read``
and contains the required columns with proper units.

Data Validation
===============

The Line List importer validates:

1. Input is a QTable
2. Required columns ('linename' and 'rest') are present
3. Rest column has astropy units
4. All rest values are positive
5. Line list name doesn't conflict with existing loaded lists

Line List Label
===============

Each imported line list requires a unique label:

.. code-block:: python

    jd.load(line_table, format='Line List', line_list_label='My Lines')

If no label is provided, the default label 'Imported' will be used. The label
cannot duplicate an already-loaded line list name.

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action":"show-sidebar","value":"loaders","delay":1500},{"action":"select-dropdown","value":"Format:Line List","delay":1000},{"action":"highlight","target":"#format-select","delay":1500}]

See Also
========

- :ref:`line-lists` - Managing and using line lists in analysis
