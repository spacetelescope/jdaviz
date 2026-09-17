.. _loaders-format-spectral-lines:

.. rst-class:: section-icon-mdi-plus-box

:data-types: spectral-lines

*********************
Spectral Lines Format
*********************


Overview
========

The **Spectral Lines** format imports any :class:`astropy.table.Table` or
:class:`~astropy.table.QTable` as a spectral line dataset in the data
collection.  This will become the eventual replacement of the
:ref:`loaders-format-line-list` format and :ref:`line-lists` plugin.


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Format:Spectral Lines", "delay": 1000, "caption": "Set format to Spectral Lines"}]

API Access
==========

.. code-block:: python

    import jdaviz as jd
    from astropy.table import QTable
    import astropy.units as u

    jd.show()
    jd.app.state.dev_loaders = True   # required while under development

    # Any table with a spectral column works
    lines = QTable({
        "wavelength": [6562.8, 4861.3, 5006.8] * u.AA,
        "name": ["H-alpha", "H-beta", "O-III"],
        "flux":  [1.0, 0.5, 0.8],
    })

    ldr = jd.loaders['object']
    ldr.object = lines
    ldr.format = "Spectral Lines"

    # Customise before importing
    importer = ldr.importer
    importer.spectral_loc = "wavelength"   # column containing the spectral axis
    importer.medium = "Vacuum"             # "Vacuum" or "Air"
    importer.col_other = ["name", "flux"]  # extra columns to carry through

    ldr.load()

Data Requirements
=================

- Input must be an :class:`astropy.table.Table` or :class:`~astropy.table.QTable`.
- The table must have at least one column whose values can be cast to ``float``.
- The table must be non-empty.

Spectral Location Column
------------------------

The importer auto-detects the spectral column by first looking for a column
whose unit has physical type ``length``, ``frequency``, ``energy``, or
``wavenumber``, then falling back to pattern-matching on the column name
(``wavelength``, ``wave``, ``wl``, ``lambda``, ``frequency``, ``freq``,
``wavenumber``, ``energy``, etc.).

If the detected column already carries valid spectral units (e.g. ``u.AA``,
``u.GHz``), the unit selector is hidden; otherwise you must choose a unit from
the dropdown.

Importer Options
================

+-----------------------+------------------------------------------------------+
| Option                | Description                                          |
+=======================+======================================================+
| ``spectral_loc``      | Column name containing the spectral axis             |
+-----------------------+------------------------------------------------------+
| ``spectral_loc_unit`` | Unit to apply when the column has no units.          |
|                       | Choices include ``Angstrom``, ``nm``, ``um``,        |
|                       | ``mm``, ``m``, ``Hz``, ``kHz``, ``MHz``, ``GHz``,    |
|                       | ``THz``, ``eV``, ``keV``, ``1/cm``                   |
+-----------------------+------------------------------------------------------+
| ``medium``            | Wavelength medium: ``"Vacuum"`` or ``"Air"``         |
+-----------------------+------------------------------------------------------+
| ``col_other``         | Additional columns to include in the output          |
|                       | (list of column names; multi-select)                 |
+-----------------------+------------------------------------------------------+

See Also
========

- :ref:`loaders-source-spectral-line-db` — interactive source for querying the
  built-in emission-line database
