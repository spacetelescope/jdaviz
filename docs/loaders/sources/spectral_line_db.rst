.. _loaders-source-spectral-line-db:

.. rst-class:: section-icon-mdi-plus-box

*****************************
Spectral Line Database
*****************************

Search the built-in Spectral Line Database and stage a custom list of lines to be
loaded into jdaviz via the :ref:`loaders-format-line-list` importer.

Overview
========

The built-in database contains spectral lines drawn from multiple published line lists,
covering UV through far-IR wavelengths.  You build up an output line list by running one or more searches and
staging individual results; the accumulated set is then imported in one step.

UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Source:spectral line database", "delay": 1500, "caption": "Select the Spectral Line Database source"}]

API Access
==========

.. code-block:: python

    import jdaviz as jd
    jd.show()

    ldr = jd.loaders['spectral line database']

    # Set search filters
    ldr.wavelength_min = "6500"
    ldr.wavelength_max = "6600"
    ldr.wavelength_unit = "Angstrom"   # "Angstrom", "nm", or "um"
    ldr.element = "H"

    # Run the search — populates ldr.search_results
    ldr.search()

    # Stage individual results by name
    ldr.stage_line("H a")

    # or stage directly from the search results
    ldr.stage_line(*ldr.search_results[1:3])

    # Inspect what is staged
    print(ldr.staged_lines)

    # Remove a line by name
    ldr.unstage_line("H a")

    # When you are happy with the staged set, set the format and import
    ldr.format = "Spectral Lines"
    ldr.load()

Searching
=========

Results are filtered by any combination of:

+----------------------+-----------------------------------------------------+
| Attribute            | Description                                         |
+======================+=====================================================+
| ``wavelength_min``   | Lower wavelength bound (string, e.g. ``"6500"``)    |
+----------------------+-----------------------------------------------------+
| ``wavelength_max``   | Upper wavelength bound (string)                     |
+----------------------+-----------------------------------------------------+
| ``wavelength_unit``  | Unit for the bounds: ``"Angstrom"``, ``"nm"``,      |
|                      | ``"um"``                                            |
+----------------------+-----------------------------------------------------+
| ``element``          | Element or molecule tag (e.g. ``"H"``, ``"CO"``);   |
|                      | ``"(any)"`` disables the filter                     |
+----------------------+-----------------------------------------------------+
| ``name_contains``    | Case-insensitive substring match on the line name   |
+----------------------+-----------------------------------------------------+

Call ``ldr.search()`` after changing any filter to refresh ``ldr.search_results``.
Each entry in ``search_results`` is a dict with keys ``line_name``,
``rest_wavelength``, ``wavelength_unit``, and ``element``.

Staging Lines
=============

``stage_line(*args)`` and ``unstage_line(*args)`` each accept any mix of:

- A **string** — the line is looked up by name in the database.
- A **dict** — a row from ``search_results`` or ``staged_lines``, used directly
  with no database lookup.

.. code-block:: python

    # Stage by name
    ldr.stage_line("H-alpha")

    # Stage multiple names at once
    ldr.stage_line("H-alpha", "H-beta", "H-gamma")

    # Stage every result from the last search
    ldr.stage_line(*ldr.search_results)

    # Unstage by name
    ldr.unstage_line("H-alpha")

    # Unstage by dict (e.g. from staged_lines)
    ldr.unstage_line(ldr.staged_lines[-1])

    # Clear all staged lines
    ldr.clear_staged()

Lines already staged are silently ignored when ``stage_line`` is called again with
the same name.  Calls to ``unstage_line`` for lines that are not currently staged
are likewise ignored.

Output Format
=============

Once at least one line is staged, the **Spectral Lines** format becomes available in the
format selector.  The imported ``QTable`` has exactly two columns:

- ``linename`` — string labels from the database
- ``rest`` — rest wavelengths as an :class:`astropy.units.Quantity` in Ångströms

See Also
========

- :ref:`loaders-format-line-list` — the target format for staged lines
