.. _plugins-spectral_lines:
.. rst-class:: section-icon-mdi-tune-variant

**************
Spectral Lines
**************
.. plugin-availability::

Plot spectral lines from a loaded line list, grouped into components.

Description
===========

The Spectral Lines plugin loads a spectral line list and organizes lines into
one or more named "components". Each component tracks its own redshift, which is
applied to the lines to compute their observed wavelengths independently of other
components. These changes are reflected in the displayed observed wavelengths
for each line in both the plugin and in the associated data table.

.. warning::

   The Spectral Lines plugin is still under active development. The API is
   not yet fully exposed, line plotting functionality has not been implemented
   yet, and there are planned changes to the interface for loading lines.
   It is currently only available when developer mode for the plugin is
   enabled (``app.state.dev_spectral_lines_plugin = True``).

**Key Features:**

* Load a spectral line list via the Spectral Line Database loader
* Create, rename, and remove components
* Set an independent redshift per component
* View each line's name, rest wavelength, and observed wavelength

UI Access
=========

Click the :guilabel:`Spectral Lines` icon in the plugin toolbar to:

1. Select or create a component
2. Load spectral lines into the component
3. Set the redshift for the selected component
4. View and toggle the lines belonging to the component

API Access
==========

The public API for this plugin is in development.

.. plugin-api-refs::
   :module: jdaviz.configs.default.plugins.spectral_lines.spectral_lines
   :class: SpectralLines
