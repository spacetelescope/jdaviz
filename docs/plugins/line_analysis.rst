.. _plugins-line-analysis:
.. rst-class:: section-icon-mdi-tune-variant

*************
Line Analysis
*************

.. plugin-availability::

The Line Analysis plugin returns
`specutils analysis <https://specutils.readthedocs.io/en/stable/analysis.html>`_
for a single spectral line.
The line is selected via the :guilabel:`region` tool in
the spectrum viewer to select a spectral subset. Note that you can have
multiple subsets in Specviz, but the plugin will only show statistics for the
selected subset.

A linear continuum is fitted and subtracted (divided for the case of equivalenth width) before
computing the line statistics.  By default, the continuum is fitted to a region surrounding
the select line.  The width of this region can be adjusted, with a visual indicator shown
in the spectrum plot while the plugin is open.  The thick line shows the linear fit which
is then interpolated into the line region as shown by a thin line.  Alternatively, a custom
secondary region can be created and selected as the region to fit the linear continuum.

The properties returned include the line centroid, gaussian sigma width, gaussian FWHM,
total flux, and equivalent width. Uncertainties on the derived properties are also
returned. For more information on the algorithms used, refer to the `specutils documentation
<https://specutils.readthedocs.io/en/stable/analysis.html>`_.

The line flux results are automatically converted to Watts/meter2,
when appropriate.

From the API
------------

The Line Analysis plugin can be run from the API:

.. code-block:: python

    # Open line analysis plugin
    plugin_la = jd.plugins['Line Analysis']
    plugin_la.open_in_tray()
    # Input the appropriate spectrum and region
    plugin_la.dataset = 'my spectrum'
    plugin_la.spectral_subset = 'Subset 2'
    # Input the values for the continuum
    plugin_la.continuum = 'Subset 3'
    # Return line analysis results
    plugin_la.get_results()


UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action": "show-sidebar", "value": "plugins", "delay": 1500, "caption": "Open the plugin toolbar"}, {"action": "open-panel", "value": "Line Analysis", "delay": 1000, "caption": "Open the Line Analysis plugin"}]