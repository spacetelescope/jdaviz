4.4 (unreleased)
================

New Features
------------

Cubeviz
^^^^^^^

Imviz
^^^^^

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

API Changes
-----------

Cubeviz
^^^^^^^

Imviz
^^^^^

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

Bug Fixes
---------

Cubeviz
^^^^^^^

Imviz
^^^^^

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

Other Changes and Additions
---------------------------

4.3.1 (unreleased)
==================

Bug Fixes
---------

Cubeviz
^^^^^^^
- Fixed issue with initial model components not using spectral y axis unit. [#3715]

Imviz
^^^^^

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

4.3 (2025-05-28)
================

New Features
------------

- The Markers plugin now includes a Distance Tool to interactively measure pixel, on-sky, and axis-separated
  (dx, dy) distances in any viewer. The tool features a real-time preview line that follows the cursor. [#3609, #3694]

- The Plot Options plugin now highlights the tab for the active (top-most) data layer
  in the selected viewer. [#3514]

- Added an STC-S string region parser to the Footprints plugin. [#3479]

- General (work-in-progress) centralized app-instance available at top package-level. [#3475, #3526, #3522, #3531, #3555, #3577, #3675, #3682, #3684]

- Added a results history table to the Line Analysis plugin.  Results are no longer updated in realtime with changes to inputs,
  but rather when clicking the button or calling ``get_results``, at which point an entry is added to the results history table
  by default. [#3557]

- User API access to ``simplify_subset()`` method in the Subset Tools plugin. [#3601]

- Hitting the "Enter" key while changing a value in the Subset Tools plugin will make a call to accept the changes (equivalent to clicking the "Update" button). [#3600]

- Hitting the "Enter" key while renaming a subset or footprint will accept the changes, hitting "Escape" will cancel. [#3600]

- Added ``subset_label`` keyword argument to ``import_region`` method of Subset Tools plugin
  to name the resulting subset(s). [#3616]

- Ability to import subsets from the Subset Tools plugin UI. [#3639]

- Aperture Photometry public API exposed, added API hints to plugin. [#3617]

- Allow custom resolutions when exporting viewers to png or mp4. [#3478]

Cubeviz
^^^^^^^

- Ability to ingest and export ``SkyRegion`` objects. [#3502]

- Add sonified layer for each cube created by the Sonify Data plugin. [#3430, #3660]

- Sonified data can now be added to any image viewer after initial sonification. [#3690]

- Renamed ``Spectral Extraction`` plugin to ``3D Spectral Extraction``. [#3691]

Imviz
^^^^^

- ``load_data`` is deprecated in favor of ``load`` method and loaders infrastructure.  Default data-labels
  from ``load_data`` may change in some cases, with the actual extension name used in place of ``[DATA]``
  and the version number included along with the extension.  [#3662, #3709, #3713]

- Loading data is now done through the loaders menu in the right sidebar.  The "import data" button is
  deprecated and will open the new sidebar.  [#3662, #3709]

- Added ability to load remote data from a S3 URI to Imviz. [#3500]

- Footprints plugin now supports selecting the closest overlay
  to a clicked point in the image viewer. [#3525, #3539, #3546, #3554]

- Improve performance by using FITS WCS for reference data layers when linked by WCS, rather than GWCS [#3483, #3535]

- The Export plugin now supports saving spatial subsets as STC-S strings, including CircleSkyRegion and EllipseSkyRegion,
  which are exported as ``CIRCLE`` and ``ELLIPSE`` STC-S shapes, respectively. [#3591, #3595]

- Improve performance by using FITS WCS for reference data layers when linked by WCS, rather than GWCS. [#3483, #3535, #3540, #3687]

Specviz
^^^^^^^

- ``load_data`` is deprecated in favor of ``load`` method and loaders infrastructure. [#3473]

- Loading data is now done through the loaders menu in the right sidebar.  The "import data" button is
  deprecated and will open the new sidebar.  [#3473]

Specviz2d
^^^^^^^^^

- ``load_data`` is deprecated in favor of ``load`` method and loaders infrastructure. [#3473]

- Loading data is now done through the loaders menu in the right sidebar.  The "import data" button is
  deprecated and will open the new sidebar.  [#3473]

- New plugin to vizualize the cross-dispersion profile [#3552]

- Renamed ``Spectral Extraction`` plugin to ``2D Spectral Extraction``. [#3691]

API Changes
-----------

- Allow ``get_regions`` and ``get_subsets`` to take a data label and have a subset apply to the wcs of that data.
  By setting a value for ``wrt_data``, the user is requesting a region type that is the opposite of the current link
  type, (i.e. ``SkyRegion`` when linked by pixel or ``PixelRegion`` when linked by wcs.) Also deprecate the
  ``return_sky_region`` kwarg and leave a deprecation warning to use ``wrt_data`` instead. [#3527]

Cubeviz
^^^^^^^

- Radial profile and curve of growth in Aperture Photometry plugin are now consistent
  with ``photutils.profiles``. [#3510]

- BEHAVIOR CHANGE: Change ``import_region`` method to default to creating a new subset when run.
  Also allow editing a subset using the ``edit_subset`` argument. [#3523]

Imviz
^^^^^

- Radial profile and curve of growth in Aperture Photometry plugin are now consistent
  with ``photutils.profiles``. [#3510]

- Catalog Search: When catalog is imported from file, its original column names are
  preserved on export. [#3519]

- User API for Catalog Search plugin (including ``catalog``,  ``max_sources``,``search``,
  ``table``, and ``table_selected``) is now public. [#3529]

Bug Fixes
---------

- Improve performance when adding/removing subsets by avoiding circular callbacks. [#3628]

- Disable export and raise vue error message upon selection of unsupported subset format. [#3635]

- Fixed issue in ``compute_scale`` to handle the case when the wcs forward
  transform does not use units, which was previously causing issues when
  aligning by WCS. [#3658]

- Fixed API hints for viewers in the data-menu. [#3695]

Cubeviz
^^^^^^^

- Significantly improved the performance of Cubeviz when creating several subsets in the
  image viewer. [#3626]

- Broadcast snackbar message to user when sonification of a data cube completes. [#3647]

- Fixes exporting an image viewer as a movie by starting the movie at the specified slice
  and returning to the correct slice after exporting. [#3710]

Imviz
^^^^^

- Catalog Search: Fixed a bug where the plugin modifies the input table if
  ``import_catalog`` is used on a table instance (not from file). [#3519]

- Fix dropdowns for overlay not showing in UI. [#3640]

- Prevent image wrapping in Imviz with Roman L2 images with GWCS. [#2887]

- Fix get_zoom_limits when WCS linked and out of image bounds. [#3654]

Specviz2d
^^^^^^^^^

- Fixed an issue with default angle unit being set in unit conversion plugin, which fixed
  a bug when background data from the spectral extraction plugin is added to the viewer. [#3661]

- Fixed a bug loading array traces into Specviz2d. [#3697]

Other Changes and Additions
---------------------------

- Bumped minimum version of ``photutils`` to v2.2 and Python to 3.11. [#3510]

- Bumped minimum version of ``specutils`` to 2.0. [#2922]

- Added ``strauss``, ``qtpy``, ``PySide6`` and ``roman_datamodels`` to the list of optional
  dependencies installed with the ``[all]`` extra dependencies flag
  (i.e., ``pip install jdaviz[all]``). [#3556]

- Auto-update sonification label upon adding sonification to viewer. [#3430, #3656]

4.2.3 (2025-06-16)
==================

Bug Fixes
---------

- Exporting as SVG now behaves the same as exporting PNG and respects
  specified output directory. [#3592]

- Improve the "no matching importers" message and suppress it
  until a target is selected. [#3593]

- Pinned specutils<2.0 until our compatibility fix is merged. [#3605]

- Hide rename button in editable dropdowns in multiselect mode. [#3623]

Cubeviz
^^^^^^^

- Use validator on spectral subset layer visibility in flux/uncertainty viewers when slice indicator
  is within the spectral subset bounds. [#3571]

- Broadcast snackbar message to user when Collapse plugin fails to perform the collapse. [#3604]

Other changes and Additions
---------------------------

- Updated minimum version of echo to 0.11, as it significantly improves the performance of CubeViz. [#3627]

4.2.2 (2025-05-12)
==================

Bug Fixes
---------

- Fixed viewer layout to persist when changing jupyter/browser tabs. [#3551]

- Fixed bug where subsets applied with remove / andNot mode when wcs linked were not able to return sky regions. [#3547]

- Fixed bug on MOSVIZ where an exception was raised when loading JWST S2D file from a directory.

- Improved error messaging when passing invalid URL to ``load``. [#3580]

Cubeviz
^^^^^^^
- Replace file and fix label in example notebook. [#3537]

Imviz
^^^^^

- Fixes changing alignment after creating additional image viewers. [#3553]

- Fix bug where markers from catalog plugin were unable to be added to viewer after orientation
  change, specifically for case when GWCS data uses Lon/Lat. [#3576]

Mosviz
^^^^^^

Specviz
^^^^^^^

- Fix bug where converting spectral units multiple times caused spectrum viewer limits
  to stop resetting to correct x-limits. [#3518]

Specviz2d
^^^^^^^^^
- Improved initial guess for trace for automatic extraction. May change results
  for automatic extraction for data with nonfinite values. [#3512]

- Replace file in example notebook. [#3537]

- Fix bug preventing deletion of 2D spectrum data. [#3541]

4.2.1 (2025-03-24)
==================

Bug Fixes
---------

- Significantly improved performance for panning and zooming with large datasets. [#3513]

4.2 (2025-03-17)
================

New Features
------------

- Added API and UI for renaming subsets to Subset Tools plugin. [#3356, #3392]

- Added API for updating subsets to Subset Tools plugin. [#3484]

- Viewer data-menus are now found in the legend on the right of the viewer. [#3281]

- Added 'select_rows' method to plugin tables to enable changing
  curent selection by indicies or slice. Also added 'select_all' and 'select_none'
  methods to change active selection to all table items or clear all selected
  items without clearing the table. [#3381]

- Plugin API methods and attributes are now searchable from the plugin tray (and visible when API hints are enabled). [#3384]

- Snackbar history logger has been moved from an overlay to a separate tab in the right sidebar tray. [#3466]

Cubeviz
^^^^^^^

- Enhancements for the cube sonification plugin. [#3377, #3387]

Imviz
^^^^^

- Catalog Search now supports importing Astropy table object via ``import_catalog`` method. [#3425]

- Enhance the Catalog Search plugin to support additional columns when loading catalog data from files. [#3359]

- Catalog Search ``clear_table`` now removes all associated markers from the viewer. [#3359]

- Catalog Search now shows a table of selected entries and allows selecting/deselecting via a tool in the image viewer. [#3429]

- Virtual Observatory plugin to query resources and download data products. [#2872, #3470]

Specviz2d
^^^^^^^^^

- Implement the Unit Conversion plugin in Specviz2D. [#3253]

API Changes
-----------

- ``jdaviz.test()`` is no longer available. Use ``pytest --pyargs jdaviz <options>``
  directly if you wish to test your copy of ``jdaviz``. [#3451]

- ``**kwargs`` from ``viz.plugins['Subset Tools'].import_region(..., **kwargs)`` is removed, ``region_format=None``
  is now explicitly supported. The default value for ``max_num_regions`` option
  is now 20 instead of ``None`` (load everything). [#3453, #3474]

Cubeviz
^^^^^^^

- ``cubeviz.load_regions()`` and ``cubeviz.load_regions_from_file()`` are deprecated.
  Use ``cubeviz.plugins['Subset Tools'].import_region()`` instead. [#3474]

- Cubeviz-specific helper-level methods are deprecated and will be removed in the future in favor of plugin APIs as configs are centralized. [#3388]

Imviz
^^^^^

- Orientation plugin: ``link_type`` and ``wcs_use_affine`` (previously deprecated) have now been removed. [#3385]

- ``imviz.load_regions()`` and ``imviz.load_regions_from_file()`` are deprecated.
  Use ``imviz.plugins['Subset Tools'].import_region()`` instead. [#3474]

- ``imviz.get_catalog_source_results()`` is deprecated.
  Use ``imviz.plugins['Catalog Search'].export_table()`` instead. [#3497]

- ``get_aperture_photometry_results`` helper-level method is deprecated and will be removed in the future in favor of plugin APIs as configs are centralized. [#3388]

Specviz
^^^^^^^

- Specviz-specific helper-level methods are deprecated and will be removed in the future in favor of plugin APIs as configs are centralized. [#3388]

Specviz2d
^^^^^^^^^

- Specviz2d-specific helper-level methods are deprecated and will be removed in the future in favor of plugin APIs as configs are centralized. [#3388]

Bug Fixes
---------

- Fix showing dataset dropdown in cubeviz's spectral extraction for flux-cube products from other plugins. [#3411]

- SDSS line list now in vacuum, and SDSS IV in air. Previously, they were incorrectly categorized.
  To keep categorization correct, SDSS IV list no longer carries wavelengths less than 2000 Angstrom. [#3458]

- Fixed some broken flux conversions that were dropping the factor of solid angle. [#3457]

- subset_tools.get_regions uses app.get_subsets under the hood, which fixes retrieving composite subsets when sky linked as
  well as an errant snackbar message when a mix of spectral/spatial subsets are present. [#3476]

Cubeviz
^^^^^^^

- Fixed copious warnings from spectrum-at-spaxel tool when data has INF. [#3368]

- Hide spectral subset layer visibility in flux/uncertainty viewers when slice indicator
  is within the spectral subset bounds. [#3437]

Imviz
^^^^^

- Improve performance of re-rendering during orientation change. [#3452]

- Fix incorrect matching between RA/Dec and pixel coordinates in Catalog search results. [#3464]

- Fixed "zoom to selected" in Catalog Search plugin when multiple sources are selected. [#3482]

Specviz
^^^^^^^

- Fixed traceback in model fitting due to units not being represented as strings. [#3412]

Specviz2d
^^^^^^^^^

- Fix subset linking/displaying between pixel/wavelength in Specviz2d viewers. [#2736]

- Fixes missing API entry for spectral extraction's export_bg_spectrum.  [#3447]

- Fixes default location of trace in spectral extraction when some columns are filled with all zeros or nans. [#3475]

Other Changes and Additions
---------------------------

- Bumped minimum version of ``photutils`` to v1.12.1. [#3432]

- Refactored flux conversion to use a single function for all plugin/viewer flux/surface brightness
  conversions. [#3457]

4.1.1 (2025-01-31)
==================

Bug Fixes
---------

- Fixes traceback from the data-menu that can be caused by a viewer rename. [#3383]

- Fixes data-menu visibility when app is scrolled out of view. [#3391]

- Fix Slice plugin for indexing through temporal slices. [#3235]

Cubeviz
^^^^^^^

Imviz
^^^^^

- Spatial subsets no longer show as having mixed visibility (in the legend and plot options tab) when aligned by WCS. [#3373]

- Fixed Gaia catalog search sometimes failing with invalid ``SOURCE_ID`` look-up. [#3400]

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

4.1 (2024-12-23)
================

New Features
------------

- New design for viewer legend and future data-menu. [#3220, #3254, #3263, #3264, #3271, #3272, #3274, #3289, #3310, #3370]

- Improve performance while importing multiple regions. [#3321]

- API method to toggle API hints. [#3336]

- Changing flux/SB display units no longer resets viewer zoom levels. [#3335]

Cubeviz
^^^^^^^

- Add Sonify Data plugin which uses the Strauss package to turn a data cube into sound. [#3269]

Imviz
^^^^^

- Orientation plugin API now exposes create_north_up_east_left and create_north_up_east_right methods. [#3308]

- Add Roman WFI and CGI footprints to the Footprints plugin. [#3322, #3345]

- Catalog Search plugin now exposes a maximum sources limit for all catalogs and resolves an edge case
  when loading a catalog from a file that only contains one source. [#3337]

- Catalog Search plugin ``zoom_to_selected`` is now in the public API. The default
  zoom level changed from a fixed 50 pixels to a zoom window that is a fraction of
  the image size (default 2%) to address and issue with zooming when using a small
  image or WCS linked. [#3369]

Specviz
^^^^^^^
- Specviz parser will now split a spectrum with a 2D flux array into multiple spectra on load
  (useful for certain SDSS file types). [#3229]

API Changes
-----------
- Removed API access to plugins that have passed the deprecation period: Links Control, Canvas Rotation, Export Plot. [#3270]

- Subset Tools plugin now exposes the ``subset``, ``combination_mode``, ``recenter_dataset``,
  ``recenter``, ``get_center``, and ``set_center`` in the user API. [#3293, #3304, #3325]

- Metadata plugin: ``metadata_plugin.metadata`` API has been deprecated; use
  ``metadata_plugin.meta`` instead, which will return a Python dictionary instead of
  list of tuples. [#3292]

- Add ``get_regions`` method to subset plugin to retrieve spatial/spectral subsets as
  ``regions`` or ``SpectralRegions``, deprecate ``get_interactive_regions`` and ``get_spectral_regions``. [#3340]

Bug Fixes
---------

- Fixed broken flux unit conversions in all plugins that respond to changes in flux unit changes. These cases
  occured when certain flux-to flux-conversions occured, as well as certain conversions between flux and surface
  brightness. This PR also fixed an issue with unit string formatting in the aperture photometry plugin. [#3228]

- Fixed broken histogram pan/zoom in Plot Options plugin. [#3361]

- Fixed bug with Plot Options select_all when data is float32. [#3366]

- Fixed an issue with back-to-back calls of set_limits and get_limits. [#3371]

Cubeviz
^^^^^^^
- Removed the deprecated ``save as fits`` option from the Collapse, Moment Maps, and Spectral Extraction plugins; use the Export plugin instead. [#3256]

- Fixed bugs where cube model fitting could fail if Jdaviz custom equivalencies were required. [#3343]

Other Changes and Additions
---------------------------

- Added a short description of each plugin in the side menu, visible before the plugin is opened. Removes redundant descriptions above link
  out to documentation when plugin is opened. Enable search on plugin description in addition to title. [#3268]

- Improved performance of ``app.get_subsets`` for the single-subset case. [#3363]

4.0.1 (2024-12-16)
==================

Bug Fixes
---------

- Improved performance and removed jittering for the matched box zoom tool. [#3215]

- Fixed Aperture Photometry radial profile fit crashing when NaN is present in
  aperture data for Cubeviz and Imviz. [#3246]

- Prevent PluginMarks from converting y-range so they maintain their position
  in the spectrum-viewer when spectral y units are converted. [#3242]

- Added ``nbclassic`` dependency to fix ``solara``-based popouts. [#3282]

- Fixed viewer widgets displaying improperly if initialized out of view in Jupyter Lab. [#3299]

- Fixed width of sliders in plugins to use full-width of plugin. [#3303]

- Raise an error when attempting to open in a popout or sidecar when not supported (i.e. within VSCode). [#3309]

Cubeviz
^^^^^^^

- Add missing styling to API hints entry for aperture_method in the spectral extraction plugin. [#3231]

- Fixed "spectrum at spaxel" tool so it no longer resets spectral axis zoom. [#3249]

- Fixed initializing a Gaussian1D model component when ``Cube Fit`` is toggled on. [#3295]

- Spectral extraction now correctly respects the loaded mask cube. [#3319, #3358]

Imviz
^^^^^

- Remove "From File.." option when running on an external server. [#3239]

- Button in the footprints plugin to change the link-type now redirects to the orientation plugin
  when the change fails due to the presence of subsets or markers. [#3276]

- Updates UI language in the orientation plugin to better match API. [#3276]

- Update Roman L2 example files in example notebook. [#3346]

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

4.0 (2024-10-17)
================

New Features
------------

- Added ability to load remote data from a URI or URL. [#2875, #2923]

- Added flux/surface brightness translation and surface brightness
  unit conversion in Cubeviz and Specviz. [#2781, #2940, #3088, #3111, #3113, #3129,
  #3139, #3149, #3155, #3178, #3185, #3187, #3190, #3156, #3200, #3192, #3206, #3211, #3216, #3219]

- Plugin tray is now open by default. [#2892]

- New "About" plugin to show Jdaviz version info. [#2886]

- Descriptions are shown in the color mode dropdown for image layers to help describe the use-cases
  for ``Colormap`` vs ``Color``. [#2894]

- The colormap menu for image layers now shows in-line previews of the colormaps. [#2900]

- Plugins can now expose in-UI API hints. [#3137, #3159]

- The standalone version of jdaviz now uses solara instead of voila, resulting in faster load times. [#2909]

- New configuration for ramp/Level 1 and rate image/Level 2 data products from Roman WFI and
  JWST [#3120, #3148, #3167, #3171, #3194]

- Unit columns are now visible by default in the results table in model fitting. [#3196]

Cubeviz
^^^^^^^

- Automatic spectral extraction now goes through the logic of the spectral extraction plugin for
  self-consistency.  This results in several breaking changes to data-labels and ``get_data``
  (the extracted spectra are now given dedicated data-labels instead of referring to them by
  the label of the flux cube) as well as to several plugins: model fitting, gaussian smooth,
  line analysis, and moment maps. [#2827]

- Background subtraction support within Spectral Extraction. [#2859]

- Aperture photometry plugin now listens to changes in display unit. [#3118]

Imviz
^^^^^

- Added a table with catalog search results. [#2915, #3101, #3099]

- "Imviz Line Profiles (XY)" plugin is renamed to "Image Profiles (XY)". [#3121]

- Added Gaia catalog to Catalog plugin. [#3090]

- Updated ``link_type`` to ``align_by`` and ``wcs_use_affine`` to ``wcs_fast_approximation`` in
  Orientation plugin API to better match UI text. [#3128]

Specviz
^^^^^^^

- Fixed ``viz.app.get_subsets()`` for XOR mode. [#3124]

Specviz2d
^^^^^^^^^

- Add option to use self-derived spatial profile for Horne extract in spectral extraction plugin. [#2845]

API Changes
-----------

- The ``Monochromatic`` option for ``color_mode`` in plot options is now renamed to ``Color``.
  ``Monochromatic`` will continue to work with a deprecation warning, but may be removed in a
  future release. [#2894]

- Plugin Table components now support row selection. [#2856]

Cubeviz
^^^^^^^

- ``get_data`` no longer supports ``function`` or ``spatial_subset`` as arguments.  To access
  an extracted 1D spectrum, use the Spectral Extraction plugin or the automatic extraction of
  spatial subsets, and refer to the data-label assigned to the resulting 1D spectrum. [#2827]

- Several plugins that take 1D spectra replace ``spatial_subset`` with referring to the 1D
  spectrum in ``dataset``.  This affects: model fitting, gaussian smooth, line analysis,
  and moment maps. [#2827]

- Removed deprecated ``cubeviz.select_slice()`` method. Use ``cubeviz.select_wavelength()``
  instead. [#2878]

- In the Slice plugin, the following deprecated properties were removed: ``wavelength`` (use ``value``),
  ``wavelength_unit`` (use ``value_unit``), ``show_wavelength`` (use ``show_value``),
  ``slice`` (use ``value``). [#2878]

- Spectral Extraction: renamed ``collapse_to_spectrum(...)`` to ``extract(...)``. [#2859]

- Generic FITS parsing now goes through ``specutils`` loaders first, if possible.
  If a ``specutils`` loader is used, uncertainty is converted to standard deviation type. [#3119]

- Custom Spectrum1D writer format ``jdaviz-cube`` is removed. Use ``wcs1d-fits`` from
  ``specutils`` instead. [#2094]

- Aperture Photometry plugin now uses TRFLSQFitter to fit radial profile because LevMarLSQFitter
  is no longer recommended by Astropy. [#3202]

Imviz
^^^^^

- Deprecated Rotate Canvas plugin was removed; use Orientation plugin instead. [#2878]

- Aperture Photometry plugin now uses TRFLSQFitter to fit radial profile because LevMarLSQFitter
  is no longer recommended by Astropy. [#3202]

Specviz
^^^^^^^

- In the Line Analysis plugin, deprecated ``width`` was removed (use ``continuum_width``). [#2878]

Bug Fixes
---------

- Markers table can now export to CSV but its columns had to be changed to accomodate this fix:
  world and pixel (previously containing SkyCoord and pixel location tuples, respectively) are now
  each two separate columns for world_ra/world_dec and pixel_x/pixel_y, respectively. [#3089]

- Stretch histogram in zoom limits no longer attempts unnecessary updates when zoom limits are changed. [#3151]

- Aperture Photometry plugin no longer allows negative counts conversion factor. [#3154]

- Fixed multiple select handling for batch mode aperture photometry in Cubeviz. [#3163]

Cubeviz
^^^^^^^

- Moment map plugin now reflects selected flux / surface brightness unit for moment zero. [#2877]

- Update the scale factor used to convert a spectrum between surface brightness and flux
  to use wavelength-dependent aperture area instead of the cone slice scale factor. [#2860]

- Handle display units when doing flux / surface brightness conversions. [#2910]

- Flux units are now correct for collapsed spectra when using the sum function
  when units are in per steradian. [#2873]

- Mouse over coordinates now responds to the selected surface brightness unit. [#2931]

- Fixed MaNGA cube loading. Uncertainty type is also handled properly now. [#3119]

- Fixed spectral axis value display in Markers plugin. Previously, it failed to display
  very small values, resulting in zeroes. [#3119]

- No longer incorrectly swap RA and Dec axes when loading Spectrum1D objects. [#3133]

- Fixed fitting a model to the entire cube when NaNs are present. [#3191]

Specviz2d
^^^^^^^^^

- Fixed Subset unit when it is created in 2D spectrum viewer. [#3201]

- Fix matched mouseover marker for 1d spectrum viewer when mouse is over 2d spectrum viewer. [#3203]

Other Changes and Additions
---------------------------

- Bump required specutils version to 1.16. Moment 0 calculation is now in units
  of flux*dx (rather than flux) [#3184]

3.10.4 (2024-10-29)
===================

Bug Fixes
---------

- Stretch histogram in zoom limits no longer attempts unnecessary updates when zoom limits are changed. [#3151]

Imviz
^^^^^

- Remove "From File.." option when running on an external server. [#3239]

Specviz2d
^^^^^^^^^

- Fix matched mouseover marker for 1d spectrum viewer when mouse is over 2d spectrum viewer. [#3203]

3.10.3 (2024-07-22)
===================

Bug Fixes
---------

- Display default filepath in Export plugin, re-enable API exporting, enable relative and absolute
  path exports from the UI. [#2896]

- Fixes exporting the stretch histogram from Plot Options before the Plot Options plugin is ever opened. [#2934]

- Previous zoom tool is optimized to only issue one zoom update to the viewer. [#2949]

- Fixes overwrite behavior for plugin plots, and properly closes overwrite warning overlay after confirmation. [#3094]

- Disable all non-image exporting when the server is not running locally, to avoid confusion with the file being saved on the server. [#3096]

Cubeviz
^^^^^^^

- Fixed a bug with filename handling for movie exports. [#2942]

Imviz
^^^^^

- Fix multiple footprints bug that prevented footprint updates on changes to the
  viewer orientation. [#2918]

- Exclude subset layers from the orientation options in the Orientation plugin. [#3097]

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

3.10.2 (2024-06-06)
===================

Bug Fixes
---------

- Update button in the subset plugin is now disabled when no subset is selected. [#2880]


3.10.1 (2024-05-14)
===================

Bug Fixes
---------

Cubeviz
^^^^^^^

- Fix Data Quality plugin bug that attempted to apply array compositing logic to
  spatial subsets. [#2854]

Imviz
^^^^^

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

- Prevent laggy behavior in trace previews for spectral extraction. [#2862]

3.10 (2024-05-03)
=================

New Features
------------

- The filename entry in the export plugin is now automatically populated based on the selection. [#2824]

- Adding Data Quality plugin for Imviz and Cubeviz. [#2767, #2817, #2844]

- Enable exporting spectral regions to ECSV files readable by ``astropy.table.QTable`` or
  ``specutils.SpectralRegion`` [#2843]

Cubeviz
^^^^^^^

- Enable spectral unit conversion in cubeviz. [#2758, #2803]

- Enable spectral extraction for composite subsets. [#2837]

API Changes
-----------

Cubeviz
^^^^^^^

- ERROR and DATA_QUALITY extension names are now recognized as
  uncertainty and mask, respectively. [#2840]

Bug Fixes
---------

Cubeviz
^^^^^^^

- Re-enable support for exporting spectrum-viewer. [#2825]


Specviz2d
^^^^^^^^^

- Loading a specific extension with ``ext`` keyword no longer crashes. [#2830]

Other Changes and Additions
---------------------------

- Bump required Python version to 3.10. [#2757]

- Line menu in Redshift from Centroid section of Line Analysis now shows values in current units. [#2816, #2831]

- Bump required specutils version to 1.15. [#2843]

3.9.1 (2024-04-19)
==================

- Fix mouseover display's top-layer logic to account for the visibility and contour toggles in
  the plot options plugin. [#2818]

Bug Fixes
---------

- Fix dropdown selection for table format in export plugin. [#2793]

- Standalone mode: stop jdaviz/voila processes when closing app. [#2791]

- Fixes compatibility with glue >= 1.19. [#2820]

Cubeviz
^^^^^^^

- Spectral extraction errors will show in snackbar. [#2807]

Imviz
^^^^^

- Fix bugs where API created footprints did not overlay and only last
  footprint displayed if added before linking. [#2790, #2797]

- Improved behavior when orientations are created or selected without having data loaded in the viewer. [#2789]

- Fixed a bug in the Orientation plugin where a WCS orientation could sometimes be flipped. [#2802]

Specviz
^^^^^^^

- H-Paschen-Brackett HI 5-4 line's rest wavelength is now correct. It was previously off by 0.5 micron. [#2819]

3.9 (2024-04-05)
================

New Features
------------
- Stretch bounds tool now enables dynamic adjustment of spline knots. [#2545, #2623]

- Stretch histogram shows a spinner when the histogram data is updating. [#2644]

- Spectrum and image viewer bounds can now be set through the Plot Options UI. [#2604, #2649]

- Opacity for spatial subsets is now adjustable from within Plot Options. [#2663]

- Live-preview of aperture selection in plugins. [#2664, #2684]

- "Export Plot" plugin is now replaced with the more general "Export" plugin. [#2722, #2782]

- "Export" plugin supports exporting plugin tables, plugin plots, data, and
  non-composite spatial subsets.[#2755, #2774, #2760, #2772, #2770, #2780, #2784]

- Opening a plugin in the tray (from the API or the toolbar buttons) now scrolls to that plugin.
  [#2768]

Cubeviz
^^^^^^^

- Calculated moments can now be output in velocity units. [#2584, #2588, #2665, #2697]

- Added functionality to Collapse and Spectral Extraction plugins to save results to FITS file. [#2586]

- Moment map plugin now supports linear per-spaxel continuum subtraction. [#2587]

- Single-pixel subset tool now shows spectrum-at-spaxel on hover. [#2647]

- Spectral extraction plugin re-organized into subsections to be more consistent with specviz2d. [#2676]

- Add conical aperture support to cubeviz in the spectral extraction plugin. [#2679]

- New aperture photometry plugin that can perform aperture photometry on selected cube slice. [#2666]

- Live previews in spectral extraction plugin. [#2733]

- Slice plugin is refactored to rely on the spectral value instead of the slice index.  This removes
  both the slider and slice-index input. [#2715]

Imviz
^^^^^

- There is now option for image rotation in Orientation (was Links Control) plugin.
  This feature requires WCS linking. [#2179, #2673, #2699, #2734, #2759]

- Add "Random" colormap for visualizing image segmentation maps. [#2671]

- Enabling any matched zoom tool in a viewer disables other matched zoom tools in other viewers
  to avoid recursion. [#2764]

Specviz2d
^^^^^^^^^

- Spectral extraction plugin: highlighting of active header section. [#2676]

API Changes
-----------

- ``width`` argument in Line Analysis plugin is renamed to ``continuum_width`` and ``width``
  will be removed in a future release. [#2587]

- New API access to ``viz.data_labels``, ``viewer.data_labels_visible``, and
  ``viewer.data_labels_loaded``. [#2626]

Cubeviz
^^^^^^^

- ``spatial_subset`` in the spectral extraction plugin is now renamed to ``aperture`` and the deprecated name will
  be removed in a future release. [#2664]

- Slice plugin's ``wavelength``, ``wavelength_unit``, and ``show_wavelength`` are deprecated in favor
  of ``value``, ``value_unit``, and ``show_value``, respectively.  ``slice`` is also deprecated
  and should be replaced with accessing/setting ``value`` directly. [#2706, #2715]

- Disabled exporting spectrum-viewer to PNG in Cubeviz; pending investigation/bugfix. [#2777]

Imviz
^^^^^

- Links Control plugin is now called Orientation. [#2179]

- Linking by WCS will now always generate a hidden reference data layer
  without distortion. As a result, when WCS linked, the first loaded data
  is no longer the reference data. Additionally, if data is distorted,
  its distortion will show when linked by WCS. If there is also data without WCS,
  it can no longer be displayed when WCS linked. [#2179]

- ``imviz.link_data()`` inputs and behaviors are now consistent with the Orientation plugin. [#2179]

- Single-pixel tool is no longer available. To mark a single-pixel area, use Markers plugin. [#2710]

Bug Fixes
---------

- Fix redshifted line lists that were displaying at rest wavelengths, by assuming a global redshift. [#2726]

- Order of RGB preset colors now matches for less than and greater than 5 layers. [#2731]

Cubeviz
^^^^^^^

- Spectral extraction now ignores NaNs. [#2737]

Imviz
^^^^^

- Apertures that are selected and later modified to be invalid properly show a warning. [#2684]

- Histogram in Plot Options no longer stalls for a very large image. [#2735]

Specviz
^^^^^^^

- Check unit type (e.g., flux density, surface brightness, counts, etc) for generating
  display label for the y axis in spectral viewer. Previously it was hard coded
  to always display ``flux density`` no matter the input unit. [#2703]


3.8.2 (2024-02-23)
==================

Bug Fixes
---------

* Fix app top-bar alignment in popouts and when embedded in websites. [#2648]

* Viewer data-menu is no-longer synced between different instances of the app to avoid recursion
  between click events. [#2670]

* Fix data-menu cutoff in smaller viewers, ensuring full visibility regardless of viewer dimensions. [#2630, #2707]

Cubeviz
^^^^^^^
- Fixes Spectral Extraction's assumptions of one data per viewer, and flux data only in
  flux-viewer/uncertainty data only in uncert-viewer. [#2646]

- Fixed a bug where cube model fitting could fail (endless spinner) if input cube
  has invalid 3D WCS. [#2685]

3.8.1 (2023-12-21)
==================

Bug Fixes
---------

- Compatibility with glue-core 1.17. [#2591, #2595]

- Fix image layer visibility toggle in plot options. [#2595]

- Fixes viewer toolbar items losing ability to bring up right-click menu. [#2605]

Cubeviz
^^^^^^^

- Fixes ability to remove cube data from the app. [#2608]

- Fixes [SCI] data not showing in the spectrum viewer's data menu. [#2631]

Imviz
^^^^^

- Line Profile (XY) plugin no longer malfunctions when image contains NaN values. [#2594]

- Stretch histogram now represents mixed state for any of the inputs (when multiple viewers are
  selected) with an overlay appropriately. [#2606]

- Fixes viewer keys in ``viz.viewers`` for additionally created viewers. [#2624]

Mosviz
^^^^^^

Specviz
^^^^^^^

-  Fixed parser bug where an HDUList would load as SpectrumList, even though it was a Spectrum1D. [#2576]

Specviz2d
^^^^^^^^^

3.8 (2023-11-29)
================

New Features
------------

- Plots in plugins now include basic zoom/pan tools for Plot Options,
  Imviz Line Profiles, and Imviz's aperture photometry. [#2498]

- Histogram plot in Plot Options now includes tool to set stretch vmin and vmax. [#2513, #2556]

- The Plot Options plugin now include a 'spline' stretch feature. [#2525]

- User can now remove data from the app completely after removing it from viewers. [#2409, #2531]

- Colorbar now shown on top of the histogram in Plot Options for image viewers. [#2517]

- Reorder viewer and layer settings in Plot Options. [#2543, #2557]

- Add button in Plot Options to apply preset RBG options to visible layers when in Monochromatic mode. [#2558, #2568]

- Plugin "action" buttons disable and show icon indicating that an action is in progress. [#2560, #2571]

- Plugin APIs now include a ``close_in_tray()`` method. [#2562]

- Convert the layer select dropdown in Plot Options into a horizontal panel of buttons. [#2566, #2574, #2582]

Cubeviz
^^^^^^^

- Add circular annulus subset to toolbar. [#2438]

- Expose sky regions in get_subsets. If 'include_sky_region' is True, a sky Region will be returned (in addition to a pixel Region) for spatial subsets with parent data that was a WCS. [#2496]

Imviz
^^^^^

- Aperture photometry (previously "Imviz Simple Aperture Photometry") now supports batch mode. [#2465]

- Aperture photometry sum is now presented in scientific notation consistently. [#2530]

- Expose sky regions in get_subsets. If 'include_sky_region' is True, a sky Region will be returned (in addition to a pixel Region) for spatial subsets with parent data that was a WCS. [#2496]

Mosviz
^^^^^^

- Matched mouseover indicator to show same position in 1d and 2d spectral viewers. [#2575]

Specviz2d
^^^^^^^^^

- Matched mouseover indicator to show same position in 1d and 2d spectral viewers. [#2575]

API Changes
-----------

- Deprecated ``app.get_data_from_viewer`` is removed, use ``viz_helper.get_data`` instead. [#2578]

- Deprecated ``app.get_subsets_from_viewer`` is removed, use ``viz_helper.get_subsets`` instead. [#2578]

- User APIs now raise a warning when attempting to set a non-existing attribute to avoid confusion
  caused by typos, etc. [#2577]

- Viewer API now exposed via ``viz.viewers`` dictionary, currently containing APIs to set axes
  limits as well as astrowidgets API commands for Imviz. [#2563]

Imviz
^^^^^

- Deprecated ``do_link`` argument of ``imviz.load_data`` is removed, use ``batch_load`` context manager instead. [#2578]

Specviz
^^^^^^^

- Deprecated ``specviz.load_spectrum`` is removed, use ``specviz.load_data`` instead. [#2578]

Bug Fixes
---------

- Fix Plot Options stretch histogram's curve for non-gray colormaps. [#2537]

Imviz
^^^^^

- Plot options layer selection no longer gets stuck in some cases when deleting
  the currently selected viewer. [#2541]

Other Changes and Additions
---------------------------

- Better handling of non-finite uncertainties in model fitting. The 'filter_non_finite' flag (for the
  LevMarLSQFitter) now filters datapoints with non-finite weights. In Specviz, if a fully-finite spectrum
  with non-finite uncertainties is loaded, the uncertainties will be dropped so every datapoint isn't
  filtered. For other scenarios with non-finite uncertainties, there are appropriate warning messages
  displayed to alert users that data points are being filtered because of non-finite uncertainties (when
  flux is finite). [#2437]

- Add swatches to color picker. [#2494]

- Plot options now includes better support for scatter viewers, including toggling line visibility. [#2449]

3.7.1 (2023-10-25)
==================

Bug Fixes
---------

- Fixed bug which did not update all references to a viewer's ID when
  updating a viewer's reference name. [#2479]

- Deleting a subset while actively editing it now deselects the subset tool,
  preventing the appearance of "ghost" subsets. [#2497]

- Fixes a bug in plot options where switching from multi to single-select mode
  failed to properly update the selection. [#2505]

Cubeviz
^^^^^^^

- Fixed moment map losing WCS when being written out to FITS file. [#2431]

- Fixed parsing for VLT MUSE data cube so spectral axis unit is correctly converted. [#2504]

- Updated glue-core pin to fix the green layer that would appear if 2D data was added to
  image viewers while spectral subsets were defined. [#2527]

Imviz
^^^^^

Mosviz
^^^^^^

Specviz
^^^^^^^

- Spectrum that has incompatible flux unit with what is already loaded
  will no longer be loaded as ghost spectrum. It will now be rejected
  with an error message on the snackbar. [#2485]

Specviz2d
^^^^^^^^^

Other Changes and Additions
---------------------------

- Compatibility with Python 3.12. [#2473]

3.7 (2023-09-21)
================

New Features
------------

- Improved design of Launcher and pass filepath arg from cli when no config specified. [#2311, #2417]

- Subset Tools plugin now displays the parent data of a spatial (ROI) subset. [#2154]

- Data color cycler and marker color updates for increased accessibility. [#2453]

- Add support for ``MultiMaskSubsetState`` in ``viz.app.get_subsets()`` and in
  the Subset Plugin [#2462]

Cubeviz
^^^^^^^

- Add Spectral Extraction plugin for Cubeviz, which converts spectral cubes
  to 1D spectra with propagated uncertainties [#2039]

Imviz
^^^^^

- The stretch histogram within plot options can now be popped-out into its own window. [#2314]

- vmin/vmax step size in the plot options plugin is now dynamic based on the full range of the
  image. [#2388]

- Footprints plugin for plotting overlays of instrument footprints or custom regions in the image
  viewer. [#2341, #2377, #2413]

- Add a curve to stretch histograms in the Plot Options plugin representing the colormap
  stretch function. [#2390]

- The stretch histogram is now downsampled for large images for improved performance. [#2408]

- Add multiselect support to the subset plugin for recentering only. [#2430]

Mosviz
^^^^^^

- Plot options now includes the stretch histogram previously implemented for Imviz/Cubeviz. [#2407]

Specviz
^^^^^^^

- Improve visibility of live-collapsed spectra from spatial regions in Cubeviz [#2387]

Specviz2d
^^^^^^^^^

- Plot options now includes the stretch histogram previously implemented for Imviz/Cubeviz. [#2407]

API Changes
-----------

- Adjusted axis ticks and labels for spectrum viewers to be more readable.
  Axes on image viewers no longer show by default. [#2372]

Cubeviz
^^^^^^^

Imviz
^^^^^

- Fixed Subset Tools unable to re-center non-composite spatial subset on an image
  that is not the reference data when linked by WCS. [#2154]

- Fixed inaccurate results when aperture photometry is performed on non-reference data
  that are of a different pixel scale or are rotated w.r.t. the reference data when
  linked by WCS. [#2154]

- Fixed wrong angle translations between sky regions in ``regions`` and ``photutils``.
  They were previously off by 90 degrees. [#2154]

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

Bug Fixes
---------

- Circle tool to create a circular Subset no longer results in an ellipse
  under certain conditions. [#2332]

- Fixes turning off multiselect mode for a dropdown when no selections are currently made.
  Previously this resulted in a traceback, but now applies the default selection for
  single-select mode. [#2404]

- Fixes tracebacks from plugins opened in popout windows. [#2411]

- Fixes app not displaying properly in Notebook 7. [#2420]

Cubeviz
^^^^^^^

Imviz
^^^^^

Mosviz
^^^^^^

- Fixes slit overlay angle in cutout viewer. [#2434]

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

Other Changes and Additions
---------------------------

- Improved logic for handling active state of plugins. [#2386, #2450]

- API framework for batch aperture photometry. [#2401]


3.6.2 (2023-08-25)
==================

Bug Fixes
---------

- Explot Plot now throws exception if its "save_figure" method is called
  with a path that contains invalid directory. [#2339]

- Plugin dropdown elements with multiselect mode enabled will no longer reset
  the selection when the choices change if any of the previous entries are still
  valid. [#2344]

- Fixed Plot Options stretch histogram bug that raised an error when a spatial subset
  was selected in Imviz and Cubeviz. [#2393]

Cubeviz
^^^^^^^

- Fix laggy behavior with WCS-TAB cubes by always linking by pixel instead of WCS. [#2343]

- Fix matched zoom tool behavior. [#2359]

Imviz
^^^^^

- Improved ASDF parsing support for non-standard Roman-like data products. [#2351]

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

3.6.1 (2023-08-01)
==================

Bug Fixes
---------

Imviz
^^^^^

- Fixes possible extreme lag when opening the Plot Options plugin. [#2326]

- Fixes minor layout issues in the Plot Options plugin. [#2326]

- Fixes compass updating in popout/inline mode. [#2326]

3.6 (2023-07-28)
================

New Features
------------

- Introduce jdaviz.open to automatically detect the appropriate config and load data [#2221]

- Add Simplify button to subset plugin to make composite spectral subsets more user
  friendly. [#2237]

- Plots within plugins can now be popped-out into their own windows. [#2254]

- The ``specviz.load_spectrum`` method is deprecated; use ``specviz.load_data`` instead. [#2273]

- Add launcher to select and identify compatible configurations,
  and require --layout argument when launching standalone. [#2257, #2267]

- Viewer toolbar items hide themselves when they are not applicable. [#2284]

- Data menu single select will default to the first element. [#2298]

- Line Analysis "Redshift from Centroid" only visible when lines are loaded. [#2294]

- Add lines representing the stretch vmin and vmax to the plot options histogram. [#2301]

- Add option to set bin size in plot options plugin and API call to change histogram
  viewer limits. [#2309]


Cubeviz
^^^^^^^

- Added the ability to export cube slices to video. User will need to install
  ``opencv-python`` separately or use ``[all]`` specifier when installing Jdaviz. [#2264]

Imviz
^^^^^

- Added the ability to load DS9 region files (``.reg``) using the ``IMPORT DATA``
  button. However, this only works after loading at least one image into Imviz. [#2201]

- Added support for new ``CircularAnnulusROI`` subset from glue, including
  a new draw tool. [#2201, #2240]

Mosviz
^^^^^^

- Improved x-axis limit-matching between 2d and 1d spectrum viewers. [#2219]

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

- Re-enable support for displaying the 1d spectrum in wavelength/frequency space, with improved
  x-axis limit-matching. [#2219]

API Changes
-----------

- ``viz.app.get_data_from_viewer()`` is deprecated; use ``viz.get_data()``. [#2242]

- ``viz.app.get_subsets_from_viewer()`` is deprecated; use ``viz.app.get_subsets()``. [#2242]

- ``viz.get_data()`` now takes optional ``**kwargs``; e.g., you could pass in
  ``function="sum"`` to collapse a cube in Cubeviz. [#2242]

- Live-previews and keypress events that depend on the plugin being opened now work for inline
  and popout windows. [#2295]

Cubeviz
^^^^^^^

Imviz
^^^^^

- Simple Aperture Photometry plugin: Custom annulus background options are removed.
  Please draw/load annulus as you would with other region shapes, then select it
  in the plugin from Subset dropdown for the background. Using annulus region as
  aperture is not supported. [#2276, #2287]

Mosviz
^^^^^^

- Added new ``statistic`` keyword to ``mosviz.get_viewer("spectrum-2d-viewer").data()``
  to allow user to collapse 2D spectrum to 1D. [#2242]

Specviz
^^^^^^^

- Re-enabled unit conversion support. [#2127]

Specviz2d
^^^^^^^^^

Bug Fixes
---------

- Fixed wrong elliptical region translation in ``app.get_subsets()``. [#2244]

- Fixed ``cls`` input being ignored in ``viz.get_data()``. [#2242]

- Line analysis plugin's ``show_continuum_marks`` is deprecated, use ``plugin.as_active()``
  instead. [#2295]

Cubeviz
^^^^^^^

- Moment Map plugin now writes FITS file to working directory if no path provided
  in standalone mode. [#2264]

- Fixes detection of spatial vs spectral subsets for composite subsets.
  Also fixes the shadow mark that shows the intersection between spatial and spectral
  subsets. [#2207, #2266, #2291]

- Prevent Plot Options plugin from hanging when selecting a spectrum viewer in Cubeviz. [#2305]

Imviz
^^^^^

Mosviz
^^^^^^

Specviz
^^^^^^^

- Uncertainties in spectra given to Specviz will now work correctly when non-standard deviation type [#2283]

Specviz2d
^^^^^^^^^

Other Changes and Additions
---------------------------

- Gaussian smooth plugin excludes results from the gaussian smooth plugin from the input
  dataset dropdown. [#2239]

- CLI launchers no longer require data to be specified [#1960]

- Added direct launchers for each config (e.g. ``specviz``) [#1960]

- Replacing existing data from a plugin (e.g., refitting a model with the same label)
  now preserves the plot options of the data as previously displayed. [#2288]

3.5 (2023-05-25)
================

New Features
------------

- Model fitting results are logged in a table within the plugin. [#2093]

- Auto-identify a configuration/helper for a given data file. [#2124]

- Exact-text filtering for metadata plugin. [#2147]

- Update Subset Plugin to utilize ``get_subsets()``. [#2157]

- Histogram showing image values in stretch limits section of plot options plugin. [#2153]

- Vertical (y-range) zoom tool for all spectrum and spectrum-2d viewers.  This also modifies
  the icon of the horizontal (x-range) tool to be more consistent with the horizontal subset
  selection tool. [#2206, #2212]

- Allow Subset Plugin to edit composite subsets. [#2182]

- Support for Scatter plots/markers in plot options. [#2193]

Cubeviz
^^^^^^^

- ``get_data`` now supports ``function=True`` to adopt the collapse-function from the spectrum viewer.
  [#2117]

- ``get_data`` now supports applying a spectral mask to a collapse spatial subset. [#2199, #2214]


Imviz
^^^^^

- Table exposing past results in the aperture photometry plugin. [#1985, #2015]

- New canvas rotation plugin to rotate displayed image without affecting actual data. [#1983]

- Preliminary support for Roman ASDF data products. This requires
  ``roman-datamodels`` to be installed separately by the user. [#1822]

- Canvas Rotation plugin is now disabled for non-Chromium based browsers [#2192]

Mosviz
^^^^^^

- NIRSpec automatic loader now can take a single image as input, instead of requiring
  the number of cutouts to be the same as the number of 1D spectra. [#2146]

API Changes
-----------

- Add ``get_subsets()`` method to app level to centralize subset information
  retrieval. [#2087, #2116, #2138]

Imviz
^^^^^

- Saving a plot to a PNG (via the astrowidgets API or export plot plugin API) with a provided
  filename will no longer show the file dialog.  If the given file exists, it is silently
  overwritten. [#929]

Bug Fixes
---------

- Fixed a bug where Import Data button crashes under certain condition. [#2110]

Cubeviz
^^^^^^^

- Fixed get_model_parameters error when retrieving parameters for a cube fit. This
  also removed the "_3d" previously appended to model labels in the returned dict. [#2171]

Imviz
^^^^^

- Do not hide previous results in aperture photometry when there is a failure, but rather show
  the failure message within the plugin UI to indicate the shown results are "out of date". [#2112]

- More efficient parser for Roman data products in Imviz [#2176]

Mosviz
^^^^^^

- Fixed several data loader bugs for uncommon use cases. [#2146]

Other Changes and Additions
---------------------------

- move build configuration to ``pyproject.toml`` as defined in PEP621 [#1661]

- drop support for Python 3.8 [#2152]

3.4 (2023-03-22)
================

New Features
------------

- CLI launchers no longer require data to be specified. [#1890]

- Configurations that support multiple, simultaneous data files now allow
  multiple data products to be specified in the command line. [#1890]

- Ability to cycle through datasets to expose information during mouseover. [#1953]

- New markers plugin to log mouseover information to a table. [#1953]

Cubeviz
^^^^^^^

- Moment map output now has celestial WCS, when applicable. [#2009]

- Custom Spectrum1D writer for spectral cube generated by Cubeviz. [#2012]

Imviz
^^^^^

- Table exposing past results in the aperture photometry plugin. [#1985, #2015]

API Changes
-----------

- Add ``get_data()`` method to base helper class to centralize data retrieval. [#1984, #2106]

- Export plot plugin now exposes the ``viewer`` dropdown in the user API. [#2037]

- Replaced internal ``get_data_from_viewer()`` calls, ``specviz.get_spectra`` now returns
  spectra for all data+subset combinations. [#2072, #2106]

Cubeviz
^^^^^^^

- Removed deprecated ``CubeViz``; use ``Cubeviz``. [#2092]

Imviz
^^^^^

- ASDF-in-FITS parser for JWST images now uses ``stdatamodels``. [#2052]

- Removed deprecated ``load_static_regions_from_file`` and ``load_static_regions``;
  use ``load_regions_from_file`` and ``load_regions``. [#2092]

Mosviz
^^^^^^

- Removed deprecated ``MosViz``; use ``Mosviz``. [#2092]

Specviz
^^^^^^^

- Removed deprecated ``SpecViz``; use ``Specviz``. [#2092]


Bug Fixes
---------

Cubeviz
^^^^^^^

- Fixed a bug where sky coordinates reported to coordinates info panel
  might be wrong for "uncert" and "mask" data. This bug only happens when
  certain parsing conditions were met. When in doubt, always verify with
  info from "flux" data. [#2009]

Imviz
^^^^^

- Pressing "Home" button on empty additional viewer when images are linked
  by WCS no longer crashes. [#2082]


Other Changes and Additions
---------------------------

Mosviz
^^^^^^

- Removed subset selection from the Mosviz image viewer. [#2102]

3.3.1 (2023-03-09)
==================

Bug Fixes
---------

* Auto-label component no longer disables the automatic labeling behavior on any keypress, but only when changing the
  label [#2007].

* Loading valid data no longer emits JSON serialization warnings. [#2011]

* Fixed linking issue preventing smoothed spectrum from showing in Specviz2D. [#2023]

* Fixed redshift slider enabling/disabling when calling ``load_line_list``, ``plot_spectral_line``,
  ``plot_spectral_lines``, or ``erase_spectral_lines``. [#2055]

* Fixed detecting correct type of composite subsets in subset dropdowns in plugins. [#2058]

Cubeviz
^^^^^^^

* Calling ``cubeviz.specviz.y_limits(...)`` no longer emits irrelevant warning. [#2033]

* Fix initial slice of uncertainty viewer. [#2056]

Imviz
^^^^^

* Fixed aperture and background dropdowns validation for Simple Aperture Photometry
  plugin. [#2032]

* Line Profiles plugin no longer updates when "l" key is pressed while plugin is not opened. [#2073]

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

3.3 (2023-02-09)
================

New Features
------------

Cubeviz
^^^^^^^

- Improved mouseover info display for spectrum viewer. [#1894]

Mosviz
^^^^^^

- Reliably retrieves identifier using each datasets' metadata entry. [#1851]

- Improved mouseover info display for spectrum viewer. [#1894]

Specviz
^^^^^^^

- Improved mouseover info display for spectrum viewer. [#1894]

Specviz2d
^^^^^^^^^

- Improved mouseover info display for spectrum viewer. [#1894]

Bug Fixes
---------

Mosviz
^^^^^^

- RA/Dec fallback values changed to "Unspecified" to avoid JSON serialization warning when loading data. [#1958, #1992]

Other Changes and Additions
---------------------------

- Gaussian Smooth products are always labeled with the original data [#1973]


3.2.2 (unreleased)
==================

Bug Fixes
---------

Cubeviz
^^^^^^^

Imviz
^^^^^

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

3.2.1 (2023-02-02)
==================

Bug Fixes
---------

Imviz
^^^^^

- Fixed crashing when clicking Home button after markers are added. [#1971]

Specviz2d
^^^^^^^^^

- Fixes link for help button in app toolbar. [#1981]

Other Changes and Additions
---------------------------

- Unit Conversion plugin is temporarily disabled while being reworked. [#1970]

3.2 (2023-01-04)
================

New Features
------------

- New rainbow, reversed rainbow, and seismic (blue-red) colormaps for images. [#1785]

- Spinner in plot options while processing changes to contour settings. [#1794]

- Model fitting plugin can optionally expose the residuals as an additional data collection entry.
  [#1864, #1891]

- Resetting viewer limits (via ``reset_limits`` or the zoom home button) now accounts for all visible
  data layers instead of just the reference data. [#1897]

- Linear1D model component now estimates slope and intercept. [#1947]

- Model fitting and line analysis plugins provide a warning and prohibit calculating results if the
  selected data entry and spectral subset do not overlap on the spectral axis. [#1935]

- Model fitting: API and UI to re-estimate model parameters based on current data/subset selection.
  [#1952]

Cubeviz
^^^^^^^

- Added ability to load plain Numpy array cube. [#1773]

- Added Slice plugin player control buttons. [#1848]

Imviz
^^^^^

- Warnings in aperture photometry plugin when using raw profile with large subsets. [#1801]

- Subset Tools plugin now allows recentering of editable spatial subset. [#1823]

- Links control plugin shows a confirmation overlay to clear markers when changing linking type.
  [#1838]

Mosviz
^^^^^^

- Disable simultaneous row plotting and 1D linking in Mosviz
  to substantially decrease load times. [#1790]

- Added coordinates display panels for Mosviz viewers. [#1795]

- ``load_data`` method can now load JWST NIRCam and NIRSpec level 2 data. [#1835]

Specviz
^^^^^^^

- Spectrum viewer now shows X and Y values under cursor. [#1759]

- Switch to opt-in concatenation for multi-order x1d spectra. [#1659]

Specviz2d
^^^^^^^^^

- Update to be compatible with changes in specreduce 1.3, including FitTrace
  with Polynomial, Spline, and Legendre options. [#1889]

- Add dropdown for choosing background statistic (average or median). [#1922]

API Changes
-----------

Cubeviz
^^^^^^^

- ``CubeViz`` is deprecated, use ``Cubeviz``. [#1809]

Imviz
^^^^^

- Simple Aperture Photometry plugin no longer performs centroiding.
  For radial profile, curve of growth, and table reporting, the aperture
  center is used instead. For centroiding, use "Recenter" feature in
  the Subset Tools plugin. [#1841]

Mosviz
^^^^^^

- Removed unused ``MosvizProfileView`` viewer class. [#1797]

- ``MosViz`` is deprecated, use ``Mosviz``. [#1809]

Specviz
^^^^^^^

- ``SpecViz`` is deprecated, use ``Specviz``. [#1809]

Bug Fixes
---------

- Console logging is restored for "Desktop Mode" Windows users. [#1887]

- Model fitting initial estimates now respect selected subset. [#1947, #1954]

Cubeviz
^^^^^^^

- Support for fitting spectral subsets with Cubeviz [#1834]

Imviz
^^^^^

- Clearing markers in Catalog Search will only hide them, which improves
  "Clear" performance. [#1774]

- Adding data will not result in clearing existing markers. [#1848]

- ``viewer.center_on()`` now behaves correctly on non-reference data. [#1928]

Mosviz
^^^^^^

- ``mosviz_row`` metadata now included in NIRISS-parsed 1D spectra. [#1836]

- Now loads NIRCam direct image properly when loading a directory. [#1948]

3.1.2 (2022-12-20)
==================

Bug Fixes
---------

- Avoid a non-finite error in model fitting by not passing spectrum uncertainties as
  weights if the uncertainty values are all 0. [#1880]

- Redshift is no longer reset to zero when adding results from plugins to app. [#1915]

Imviz
^^^^^

- Viewer options in some plugins no longer displaying the wrong names. [#1920]

- Fixes cropped image layer with WCS linking without fast-approximation, mouseover display
  for GWCS now shows when information is outside original bounding box, if applicable. [#1908]

Mosviz
^^^^^^

- Prevent color cycling when selecting different objects/rows [#1900]

3.1.1 (2022-11-23)
==================

Bug Fixes
---------

- Change box zoom to always maintain aspect ratio. [#1726]

- Fixed removing image data from viewer when changing row. [#1812]

- Prevent duplicate labels by changing duplicate number appended
  to label to max number (of duplicates) plus 1. [#1824]

- Layer lettering now supports up to 702 layers. Beyond that, special characters are used. [#1850]

- Fix cycler so new data added have different colors [#1866]

Cubeviz
^^^^^^^

- Fix spatial-spectral highlighting after adding spectral data set (either manually or by loading
  and results from plugins into the spectral-viewer) which had prevented new subsets from being
  created. [#1856]

Imviz
^^^^^

Mosviz
^^^^^^

- Data unassigned a row is hidden under the subdropdown in the data dropdown. [#1798, #1808]

- Missing mosviz_row metadata in NIRISS-parsed 1D spectra now added. [#1836]

- Allow Mosviz ``load_data`` method to load only 1D or 2D spectra. [#1833]

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

- Fixed options for peak method in spectral extraction plugin. [#1844]

3.1 (2022-10-26)
================

New Features
------------

- Add support for nonstandard viewer reference names [#1681]

- Centralize data label generation if user does not provide a label with data load. Also
  prevent duplicate data labels from being added to data collection. [#1672]

Imviz
^^^^^

- Catalogs plugin now supports loading a JWST catalog from a local ECSV file. [#1707]

- New "batch_load" context manager to optimize loading multiple images. [#1742]

Specviz2d
^^^^^^^^^

- Improved logic for initial guess for position of "Manual" background trace in spectral extraction
  plugin. [#1738]

- Now supports loading a specific extension of the 2D spectrum file and
  transposing data on load. [#1705]

- Spectral extraction plugin now supports visualizing and exporting the 1D spectrum associated
  with the background region. [#1682]

Bug Fixes
---------

- Disable unit conversion if spectral axis is in pixels or if flux
  is in counts, respectively. [#1734]

- Improved performance when toggling visibility of data layers in data menu. [#1742]

Cubeviz
^^^^^^^

- Fixed parsing of data cube without WCS. [#1734]

Imviz
^^^^^

- Fixed Simple Aperture Photometry plugin compatibility with astropy v5.1.1. [#1769]

Mosviz
^^^^^^

- Fixed toolbar on 2d profile viewer. [#1778]

Specviz2d
^^^^^^^^^

- Fixed parser not loading x1d when s2d is provided. [#1717]

- Fixed toolbar on 2d spectrum viewer. [#1778]

Other Changes and Additions
---------------------------

- Updated example notebooks (except MosvizExample) to use in-flight JWST data. [#1680]
- Change RA/Dec significant figures from 4 to 6 in aperture photometry plugin. [#1750]

3.0.2 (2022-10-18)
==================

Bug Fixes
---------

- Fix subset selection tool conflicts caused by a duplicate toolbar. [#1679]

- Fixed blank tabbed viewers. [#1718]

- Prevent `app.add_data_to_viewer` from loading data from disk [#1725]

- Fix bug in creating and removing new image viewers from Imviz [#1741]

- Updated Zenodo link in docs to resolve to latest version. [#1743]

Imviz
^^^^^

- Fixed Compass crashing while open when loading data. [#1731]

Specviz2d
^^^^^^^^^

- Fixed padding on logger overlay. [#1722]

- Changing the visibility of a data entry from the data menu no longer re-adds the data to the viewer
  if it is already present, which avoids resetting defaults on the percentile and/or color or the
  layer. [#1724]

- Fixed handling of "Manual" background type in spectral extraction plugin. [#1737]

3.0.1 (2022-10-10)
==================

- Fixed Citations file to accurately reflect release.

3.0 (2022-10-10)
================

New Features
------------

- Profile viewers now support plotting with profiles "as steps". [#1595, #1624]

- Use spectrum's uncertainty as weight when doing model fitting. [#1630]

- Line flux in the Line Analysis plugin are reported in W/m2 if Spectral Flux is given
  in Jy [#1564]

- User-friendly API access to plugins, with exposed functionality for:  line analysis, gaussian
  smooth, moment maps, compass, collapse, metadata, slice, plot options, model fitting, links
  control, export plot, and spectral extraction.
  [#1401, #1642, #1643, #1636, #1641, #1634, #1635, #1637, #1658, #1640, #1657, #1639, #1699, #1701, #1702, #1708]

- Line Lists show which medium the catalog wavelengths were measured in,
  in accordance to the metadata entry. Lists without medium information
  are removed, until such information can be verified [#1626]

- Cycle through colors applied to data when multiple datasets are loaded to
  the same viewer [#1674]

- Added ability to set height of application widget using `show` method. [#1646]

- Add Common Galactic line lists, split Atomic/Ionic list with verified medium info [#1656]

Cubeviz
^^^^^^^

- Image viewers now have linked pan/zoom and linked box zoom. [#1596]

- Added ability to select spatial subset collapsed spectrum for Line Analysis. [#1583]

- Increased size of Cubeviz configuration from 600px to 750px. [#1638]

Imviz
^^^^^

- Changing link options now updates immediately without needing to press "Link" button. [#1598]

- New tool to create a single-pixel spatial region on the image. [#1647]

Specviz2d
^^^^^^^^^

- Support for Horne/Optimal extraction. [#1572]

- Support for importing/exporting Trace objects as data entries. [#1556]

- 2D spectrum viewer now has info panel for pixel coordinates and value. [#1608]

Bug Fixes
---------

- Fixed loading data via the Import Data button on top-left of the application.
  [#1608]

- Floating menus are now attached to their selector element. [#1673, #1712]

- Remove model fitting equation length restriction. [#1685]

- Fixed crashing of model fitting when a parameter is fixed before fitting
  is done. [#1689]

- Fixed IndexError when editing a subset while subset selection is set to "Create New". [#1700]

Cubeviz
^^^^^^^

- Calling ``cubeviz.load_data(data, data_label)``, where ``data_label`` is passed in
  as second positional argument instead of keyword, is now allowed. [#1644]

- A warning will be presented when overwriting a moment map to
  an existing file on disk. [#1683, #1684]

Imviz
^^^^^

- Fixed inaccurate aperture photometry results when aperture photometry is done on
  a non-reference image if images are linked by WCS. [#1524]

- Calling ``imviz.load_data(data, data_label)``, where ``data_label`` is passed in
  as second positional argument instead of keyword, is now allowed. Previously,
  this will crash because second positional argument is actually a
  ``parser_reference`` that is meant for internal use. [#1644]

- Fixed crashing for when data is accidentally loaded multiple times or when
  subset is deleted after a viewer is deleted. [#1649]

Mosviz
^^^^^^

- R-grism 2D spectrum data are now loaded with the correct orientation. [#1619]

- Fixed a bug to skip targets not included in NIRISS source catalog, improving
  lod times [#1696]

Specviz
^^^^^^^

- Line Lists plugin now disabled if no data is loaded instead of letting user
  load a list list and crash. [#1691]

Specviz2d
^^^^^^^^^

- Fixed default spectral extraction parameters when the background separation otherwise would have
  fallen directly on the edge of the image. [#1633]

- Fixed parser for Level 2 NIRSpec ``s2d`` files. [#1608]

- Spectral-extraction plugin: support floats for all input trace positions, separations, and widths.
  [#1652]

Other Changes and Additions
---------------------------

- Changed unit formatting to avoid astropy.units warnings in Line Analysis plugin. [#1648]

Cubeviz
^^^^^^^

- Changed the default layout to have only two image viewers, and enabled tabbing
  and dragging the viewers. [#1646]

2.10 (2022-08-26)
=================

New Features
------------

- Layer icons now show indication of linewidth. [#1593]

- Model Fitting plugin now displays parameter uncertainties after fitting. [#1597]

Bug Fixes
---------

Cubeviz
^^^^^^^

- Future proof slicing logic for ``as_steps`` implementation in glue-jupyter 0.13 or later. [#1599]

2.9 (2022-08-24)
================

New Features
------------

- New popout locations display Jdaviz in a detached popup window (``popout:window``)
  or browser tab (``popout:tab``). [#1503]

- Subset Tools plugin now allows basic editing, including rotation for certain shapes.
  [#1427, #1574, #1587]

- New ``jdaviz.core.region_translators.regions2roi()`` function to convert certain
  ``regions`` shapes into ``glue`` ROIs. [#1463]

- New plugin-level ``open_in_tray`` method to programmatically show the plugin. [#1559]

Cubeviz
^^^^^^^

- Cubeviz now has ellipse spatial Subset selection tool. [#1571]

- Cubeviz now has ``load_regions_from_file()`` and ``load_regions()`` like Imviz. [#1571]

Imviz
^^^^^

- New "Catalog Search" plugin that uses a specified catalog (currently SDSS) to search for sources in an image
  and mark the sources found. [#1455]

- Auto-populate simple aperture photometry values if JWST data is loaded into viewer. [#1549]

- Pressing Shift+b now blinks backwards. Right-clicking on the image while Blink tool
  is active on the toolbar also blinks backwards. [#1558]

Mosviz
^^^^^^

- NIRISS parser now sorts FITS files by header instead of file name. [#819]

Specviz2d
^^^^^^^^^

- Spectral extraction plugin. [#1514, #1554, #1555, #1560, #1562]

- CLI support for launching Specviz2d for a single 2D spectrum file input.
  Use notebook version if you want to open separate 2D and 1D spectra in Specviz2d. [#1576]

- New ``specviz2d.specviz`` helper property to directly access Specviz functionality from Specviz2d. [#1577]

API Changes
-----------

Imviz
^^^^^

- ``Imviz.load_static_regions_from_file()`` and ``Imviz.load_static_regions()`` are
  deprecated in favor of ``Imviz.load_regions_from_file()`` and ``Imviz.load_regions()``,
  respectively. This is because some region shapes can be made interactive now even though
  they are loaded from API. The new methods have slightly different API signatures, please
  read the API documentation carefully before use. [#1463]

Bug Fixes
---------

- Fixes subset mode to reset to "Replace" when choosing to "Create New" subset. [#1532]

- Fixes behavior of adding results from a plugin that overwrite an existing entry.  The loaded
  and visibility states are now always adopted from the existing entry that would be overwritten.
  [#1538]

- Fix support for ipywidgets 8 (while maintaining support for ipywidgets 7). [#1592]

Cubeviz
^^^^^^^

- Fixed validation message of moment number in moment map plugin. [#1536]

- Fixed ``viewer.jdaviz_helper`` returning Specviz helper instead of Cubeviz helper after Specviz
  helper is called via ``Cubeviz.specviz``. Now ``viewer.jdaviz_helper`` always returns the Cubeviz helper. [#1546]

- Increased spectral slider performance considerably. [#1550]

- Fixed the spectral subset highlighting of spatial subsets in the profile viewer. [#1528]

Specviz
^^^^^^^

- Fixed a bug where spectra with different spectral axes were not properly linked. [#1526, #1531]

Other Changes and Additions
---------------------------

- Added a UV Galactic linelist. [#1522]

- astroquery is now a required dependency of Jdaviz. [#1455]

2.8 (2022-07-21)
================

New Features
------------

- Added viewer/layer labels with icons that are synced app-wide. [#1465]

Cubeviz
^^^^^^^

- The "Import Data" button is hidden after a data cube is loaded into the app [#1495]

Mosviz
^^^^^^
- Added ``--instrument`` CLI option to support NIRISS data loading in Mosviz. [#1488]

Bug Fixes
---------

- Fix scrolling of "x" button in data menus. [#1491]

- Fix plot options colormap when setting colormap manually through API. [#1507]

Cubeviz
^^^^^^^

- Cubeviz parser now sets the wavelength axis to what is in the CUNIT3 header [#1480]

- Includes spectral subset layers in the layer dropdowns in plot options and fixes behavior when
  toggling visibility of these layers. [#1501]

Imviz
^^^^^

- Fixed coordinates info panel crashing when HDU extension with
  non-celestial WCS is loaded into Imviz together with another
  extension with celestial WCS. [#1499]

Other Changes and Additions
---------------------------

- Added a more informative error message when trying to load Jdaviz outside of Jupyter. [#1481]

2.7.1 (2022-07-12)
==================

Bug Fixes
---------

- Fix updating coordinate display when blinking via click. [#1470]

Cubeviz
^^^^^^^

- Replaced deprecated FILETYPE header keyword with EXP_TYPE to identify JWST cubes
  for proper MJD-OBS handling. [#1471]

- Fixed a bug where having Subset breaks coordinates information display
  in image viewers. [#1472]

Other Changes and Additions
---------------------------

2.7.0.post1 (2022-07-07)
========================

- Post-2.7 release to fix a PyPi distribution problem.

2.7 (2022-07-06)
================

New Features
------------
- The app and individual plugins can be opened in a new window by clicking a button in the top
  right-hand corner. [#977, #1423]

- Snackbar queue priority and history access. [#1352, #1437]

- Subset Tools plugin now shows information for composite subsets. [#1378]

- Plot options are simplified and include an advanced mode to act on multiple viewers/layers
  simultaneously. [#1343]

- Labels in data menus are truncated to fit in a single line but ensure visibility of extensions.
  [#1390]

- Data menus now control visibility of layers corresponding to the data entries instead of
  loading/unloading the entries from the viewers.  Data entries that are unloaded now appear
  in an expanded section of the menu and can be re-loaded into the viewer. [#1400]

- Several reversed version of colormaps now available for image viewers. [#1407]

- Simple zoom "back" button in all viewers. [#1436]

Cubeviz
^^^^^^^

- New tool for visualizing spectrum at a pixel's coordinate location
  in the image viewer [#1317, #1377]

Imviz
^^^^^

- Added the ability to fit Gaussian1D model to radial profile in
  Simple Aperture Photometry plugin. Radial profile and curve of growth now center
  on source centroid, not Subset center. [#1409]

API Changes
-----------

- Default percentile for all image viewers is now 95%, not min/max. [#1386]

- Default verbosity for popup messages is now "warnings" but
  the history logger is still at "info" so you can see all messages
  there instead. [#1368]

- In the Color Mode options under Plot Options, "Colormaps" and "One color per layer"
  have been renamed to "Colormap" and "Monochromatic," respectively, for all image
  viewers. [#1406]

- Viz tool display changed to ``viz.show()`` from ``viz.app``. Sidecar no longer returned by
  show methods. [#965]

Imviz
^^^^^

- In the toolbar, linked box-zoom and linked pan/zoom are now the defaults.
  Right-click on the respective button to access single-viewer box-zoom or
  single-viewer pan/zoom. [#1421]

- ``viewer.set_colormap()`` method now takes Glue colormap name, not
  matplotlib name. This is more consistent with colormap options under
  Plot Options. [#1440]

Bug Fixes
---------

- Fixed HeI-HeII line list loading. [#1431]

Cubeviz
^^^^^^^

- Fixed the default thickness of a subset layer in the spectral viewer to remain 1 for
  spatial subsets and 3 for spectral subsets. [#1380]

- Fixed linking of plugin data to the reference data that was used to create it [#1412]

- Fixed coordinates display not showing the top layer information when multiple
  layers are loaded into the image viewer. [#1445]

Imviz
^^^^^

- Fixed a bug where image loaded via the "IMPORT DATA" button is not
  linked to the data collection, resulting in Imviz unusable until
  the data are re-linked manually. [#1365]

- Fixed a bug where coordinates display erroneously showing info from
  the reference image even when it is not visible. [#1392]

- Fixed a bug where Compass zoom box is wrong when the second image
  is rotated w.r.t. the reference image and they are linked by WCS. [#1392]

- Fixed a bug where Line Profile might crash when the second image
  is rotated w.r.t. the reference image and they are linked by WCS. [#1392]

- Contrast/bias mouse-drag is now more responsive and
  calculates contrast in the same way as Glue in Qt mode. [#1403]

- Fixed a bug where some custom colormap added to Imviz is inaccessible
  via ``viewer.set_colormap()`` API. [#1440]

- Fixed a bug where Simple Aperture Photometry plugin does not know
  an existing Subset has been modified until it is reselected from
  the dropdown menu. [#1447]

- Disables the "popout in new window" buttons on the image viewer tabs
  in favor of other ways of popping out Jdaviz from notebook. [#1461]

Mosviz
^^^^^^

- Data dropdown in the gaussian smooth plugin is limited to data entries from the
  spectrum-viewer (excluding images and 2d spectra). [#1452]

2.6 (2022-05-25)
================

New Features
------------

- Line list plugin now supports exact-text filtering on line names. [#1298]

- Added a Subset Tools plugin for viewing information about defined subsets. [#1292]

- Data menus in the viewers are filtered to applicable entries only and support removing generated data from
  the app. [#1313]

- Added offscreen indication for spectral lines and slice indicator. [#1312]


Cubeviz
^^^^^^^

- Cubeviz image viewer now has coordinates info panel like Imviz. [#1315]

- New Metadata Viewer plugin. [#1325]

Imviz
^^^^^

- New way to estimate background from annulus around aperture
  in Simple Aperture Photometry plugin. [#1224]

- New curve of growth plot available in Simple Aperture
  Photometry plugin. [#1287]

- Clicking on image in pan/zoom mode now centers the image to location
  under cursor. [#1319]

Specviz
^^^^^^^

- Line List Spectral Range filter displays only lines with an observed
  wavelength within the range of the spectrum viewer [#1327]

Bug Fixes
---------

- Line Lists plugin no longer crashes when a list is removed under
  certain conditions. [#1318]

Cubeviz
^^^^^^^

- Parser now respects user-provided ``data_label`` when ``Spectrum1D``
  object is loaded. Previously, it only had effect on FITS data. [#1315]

- Fixed a bug where fitting a model to the entire cube returns all
  zeroes on failure. [#1333]

Imviz
^^^^^

- Line profile plot in Line Profile plugin no longer affects
  radial profile plot in Simple Aperture Photometry plugin. [#1224]

- Line profile plot no longer report wrong coordinates on
  dithered data that is not the reference data. [#1293]

- Radial profile plot in Simple Aperture Photometry plugin
  no longer shows masked aperture data. [#1224]

- Aperture sum in Simple Aperture Photometry plugin no longer reports
  the wrong value in MJy when input data is in MJy/sr. Previously,
  it applied number of pixels twice in the calculations, so sum in MJy
  with 10-pixel aperture would be off by a factor of 10. This bug did not
  affect data in any other units. [#1332]

- Markers API now handles GWCS with ICRS Lon/Lat defined instead of
  Right Ascension and Declination. [#1314]

Specviz
^^^^^^^

- Fixed clearing an identified spectral line when its removed. [#1322]

Specviz2d
^^^^^^^^^

- Fixed a regression that caused NIRSpec s2d to stop loading
  properly. [#1307]

2.5 (2022-04-28)
================

New Features
------------

- Search bar to filter plugins in sidebar. [#1253]

Cubeviz
^^^^^^^

- Add ESA pipeline data parser. [#1227]

Mosviz
^^^^^^

- Mosviz Desktop App utilizes new directory parsers, which falls back to NIRSpec parser if
  no instrument keyword is specified. [#1232]

API Changes
-----------

- CLI now takes the layout as a required first positional argument after jdaviz
  (``jdaviz cubeviz path/to/file``). [#1252]

Bug Fixes
---------

- Fixed clicking in Safari on MacOS when using CTRL-click as right-click. [#1262]

Imviz
^^^^^

- No longer issues a Snackbar error message when all data is deselected. [#1250]


Other Changes and Additions
---------------------------

- Change default collapse function to sum.
  This affects collapsed spectrum in Cubeviz and its Collapse plugin default. [#1229, #1237]
- Data dropdowns in plugins are now filtered to only applicable entries. [#1221]
- Cube data now has spectral axis last in the backend, to match specutils Spectrum1D
  axis order and work with updated glue-astronomy translators. [#1174]
- Plugins that create data entries allow overriding the default labels. [#1239]
- Automatic defaults for model component IDs and equation editor in model fitting. [#1239]
- Help button in toolbar to open docs in a new tab. [#1240]
- Snackbar queue handles loading interrupt more cleanly. [#1249]
- Reported quantities are rounded/truncated to avoid showing unnecessary precision. [#1244]
- Line analysis quantities are coerced so length units cancel and constants are removed from units.
  [#1261]

2.4 (2022-03-29)
================

New Features
------------

- Lines from the line list plugin can be selected to help identify as well
  as to assign redshifts from the line analysis plugin. [#1115]

- New ``jdaviz.core.region_translators`` module to provide certain translations
  from ``regions`` shapes to ``photutils`` apertures, and vice versa. [#1138]

Imviz
^^^^^

- New Line Profiles (XY) plugin to plot line profiles across X and Y axes
  for the pixel under cursor when "l" key is pressed or for manually entered
  X and Y values on the displayed image. [#1132]

- Simple aperture photometry plugin now uses ``photutils`` to for all calculation.
  Additional photometry results are also added, such as centroid and FWHM. [#1138]

Specviz
^^^^^^^

- Exposed toggle in Plot Options plugin for viewing uncertainties. [#1189, #1208]

API Changes
-----------

Imviz
^^^^^

- ``viewer.marker`` dictionary now accepts ``fill`` as an option, settable to
  ``True`` (default) or ``False``; the latter draws unfilled circle. [#1101]

Bug Fixes
---------

- Fixed support for table scrolling by enabling scrollbar. [#1116]
- Fixed loading additional spectra into a spectrum viewer after creating a
  spectral subset. [#1205]

Cubeviz
^^^^^^^

- Fixed linking of data to allow contour over-plotting. [#1154]
- Fixed an error trace when fitting a model to a spatial subset. [#1176]
- Fixed the model fitting plugin data dropdown not populating with spatial
  subsets properly. [#1176]
- Fixed visibility of switch and dropdown options in gaussian smooth plugin. [#1216]

Imviz
^^^^^

- Fixed Compass plugin performance for large image. [#1152]

- Fixed data shown out of order when ``load_data`` is called after
  ``app``. [#1178]

- Fixed the subsequent dataset not showing after blinking if the dataset
  being shown is removed from viewer. [#1164]

Other Changes and Additions
---------------------------

- Jdaviz now requires Python 3.8 or later. [#1145]

- ``photutils`` is now a required dependency. [#1138]

- Viewer toolbars are now nested and consolidated, with viewer and layer options
  moved to the sidebar. [#1140]

- Redshifts imported with a custom line list are now ignored.  Redshift must be set app-wide via
  viz.set_redshift or the line list plugin. [#1134]

- Subset selection dropdowns in plugins now show synced color indicators. [#1156, #1175]

- Line analysis plugin now shows uncertainties, when available. [#1192]

2.3 (2022-03-01)
================

New Features
------------

- There are now ``show_in_sidecar`` and ``show_in_new_tab`` methods on all the
  helpers that display the viewers in separate JupyterLab windows from the
  notebook. [#952]

- The line analysis plugin now includes logic to account for the background
  continuum. [#1060]

- Specviz can load a ``SpectrumList`` and combine all its elements into a single spectrum. [#1014]

Cubeviz
^^^^^^^

- Move slice slider to the plugin tray and add capability for selecting by wavelength as well as
  through a tool in the spectrum viewer. [#1013]

Imviz
^^^^^

- New metadata viewer plugin. [#1035]

- New radial profile plot and background auto-population in the
  simple aperture photometry plugin. [#1030, #1109]

- New plugin to display compass for image with WCS and also zoom box. [#983]

- Imviz now loads 3D Numpy array as individual slices at ``axis=0``.
  Also supports higher dimension as long as the array can be squeezed into 3D. [#1056]

- New ``do_link`` keyword for ``Imviz.load_data()``. Set it to ``False``
  when loading multiple dataset in a loop but ``Imviz.link_data()`` must be
  run at the end manually afterwards. [#1056]

- New ``imviz.load_static_regions_from_file()`` method to load region file
  via API. [#1066]

Mosviz
^^^^^^

- New metadata viewer plugin. [#1035]

Specviz
^^^^^^^

- New metadata viewer plugin. [#1035]

API Changes
-----------

- Viewers now can access the Jdaviz application using ``viewer.jdaviz_app`` and
  the helper via ``viewer.jdaviz_helper``. [#1051, #1054]

- Jdaviz no longer uses Python logging to issue warning. Warning is now issued by
  Python's ``warnings`` module. [#1085]

Cubeviz
^^^^^^^

- Subsets from the spectrum viewer are now returned as SpectralRegion objects. [#1046]

- Collapse plugin only collapses into spatial-spatial image now. Default collapse
  function is now sum, not mean. [#1006]

Imviz
^^^^^

- ``imviz.load_static_regions()`` now returns a dictionary of regions that failed
  to load with warnings. It also shows a snackbar message. [#1066]

Bug Fixes
---------

- Model plugin now validates component names to avoid equation failing. [#1020]
- Model plugin properly updates parameters after fit for compound models. [#1023]
- Model plugin now respects fixed parameters when applying model to cube, and retains
  parameter units in that case. [#1026]
- Model plugin polynomial order now avoids traceback when clearing input. [#1041]
- Box zoom silently ignores click without drag events. [#1105]
- Fixes index error when plotting new data/model. [#1120]
- API calls to subset now return full region. [#1125]

Cubeviz
^^^^^^^

- Spectral region retrieval now properly handles the case of multiple subregions. [#1046]

- Moment Map plugin no longer crashes when writing out to FITS file. [#1099]

- Moment Maps result is no longer rotated w.r.t. original data. [#1104]

Imviz
^^^^^

- Imviz no longer crashes when configuration is overwritten by MAST. [#1038]

- Imviz no longer loads incompatible data from ASDF-in-FITS file. [#1056]

- Simple Aperture Photometry plugin now shows the entire data collection
  for the application, not just selected data/subset for the default viewer. [#1096]

Mosviz
^^^^^^

Specviz
^^^^^^^

- Fix corrupted voila launch notebook. [#1044]

- Entering line list in units that require spectral equivalencies no longer crashes Line Lists plugin. [#1079]

- Unit Conversion plugin is now disabled in the presence of any Subset due to
  incompatibility between the two. [#1130]

Other Changes and Additions
---------------------------

- Redshift slider and options are moved from the toolbar to the Line List
  plugin in the plugin tray. [#1031]

- Spectral lines and redshift are refactored to improve performance. [#1036]

- Jdaviz no longer depends on ``spectral-cube``. [#1006]

- Line list plugin now includes a dropdown for valid units for custom lines. [#1073]


2.2 (2021-12-23)
================

New Features
------------

- Box and xrange zoom tools for all applicable viewers. [#997]

- Data and Subset selection are now separate in the Line Analysis plugin, to
  handle the case of multiple datasets affected by a subset. [#1012]

Bug Fixes
---------

Cubeviz
^^^^^^^

- Missing MJD-OBS in JWST data will no longer crash Cubeviz as long as
  it has MJD-BEG or DATE-OBS. [#1004]


2.1 (2021-12-10)
================

New Features
------------

- Support for units in astropy models and BlackBody in modeling plugin. [#953]

Imviz
^^^^^

- New ``imviz.create_image_viewer()`` and ``imviz.destroy_viewer()`` methods
  to allow users to programmatically create and destroy image viewers. [#907]

- New plugin to control image linking via GUI. [#909]

- New plugin to perform simple aperture photometry. [#938]

- Coordinates display now also shows Right Ascension and Declination in degrees. [#971]

Mosviz
^^^^^^

- New toggle button to lock/unlock viewer settings (x-limits in 1d and 2d spectrum viewers and
  stretch and percentile for 2d spectrum and image viewers). [#918]

- Ability to add custom columns and change visibility of columns in the table. [#961]

- Support for redshift slider and new ``mosviz.get_spectrum_1d`` and ``mosviz.get_spectrum_2d``
  helper methods. [#982]

Specviz
^^^^^^^

- MIRI s2d files can now be loaded into Specviz2d. [#915]

- Default new subset/region thickness is set to 3px. [#994]

API Changes
-----------

- Removed unused ``jdaviz.core.events.AddViewerMessage``. [#939]

Bug Fixes
---------

- ``vue_destroy_viewer_item`` no longer called twice on destroy event. [#676, #913]

Imviz
^^^^^

- ``imviz.get_interactive_regions()`` no longer produces long traceback
  for unsupported region shapes. [#906]

- Imviz now parses some image metadata into ``glue`` and understands
  ELECTRONS and ELECTRONS/S defined in FITS BUNIT header keyword. [#938]

- Imviz now updates pixel value correctly during blinking. [#985]

- Imviz now displays the correct pixel and sky coordinates for dithered
  images linked by WCS. [#992]

Specviz
^^^^^^^

- Fixed a bug where ``specviz.get_model_parameters()`` crashes after fitting
  a Gaussian model in the Model Fitting plugin. [#976]

Other Changes and Additions
---------------------------

- Cubeviz now loads data cube as ``Spectrum1D``. [#547]
- The new template load system in ``ipyvue`` is used, which enables hot reload. [#913]
- Plugins now provide options for immediately showing results in applicable viewers. [#974]

2.0 (2021-09-17)
================

- Added Imviz configuration for visualization of 2D images.
- Overhauled Mosviz to drastically increase performance, improve user interface,
  fix buggy features.
- Improved other configurations with bug fixes, user experience enhancements,
  and JWST data formats support.


1.1 (2021-03-22)
================

New Features
------------
- Added methods to extract Mosviz data table to csv or astropy table. [#468]
- Added methods to extract fitted models and model parameters to notebook. [#458]
- Created a NIRISS dataset parser for Mosviz. [#394]
- Added a Specviz2d configuration for two-dimensional spectra. [#410, #416, #421]
- Added a redshift slider to Specviz. [#380, #453, #457]
- Added new preset spectral line lists. [#379]
- Added a debugging mode to show stdout and stderr on frontend. [#368]

Bug Fixes
---------
- Fixed data selection update loop in UI menu. [#427, #456]
- Fixed a bug when using the Gaussian Smooth plugin multiple times. [#441]
- Fixed axis autoscaling when redshift slider has been used. [#404, #413]
- Now properly raises an error when trying to load a non-existent file. [#384]
- Fixed "Hide All" button behavior in line list plugin. [#383]
- Fixed a WCS bug in Mosviz. [#377]
- Fixed failing case of parsing cube extensions. [#374]

Other Changes and Additions
---------------------------
- Cleaned up the Model Fitting plugin UI. [#485]
- Improved performance when loading multiple datasets. [#435]
- Updated example notebooks. [#418]
- Moved snackbar messages to top of UI. [#375]
- Removed unused icons from toolbar. [#366]
- Refactored the Unit Conversion plugin. [#360]
- Many documentation updates/additions. [#340, #341, #343, #346, #347,
  #349, #350, #351, #352, #357, #365, #376, #471, #481, #482, #483]


1.0.3 (2020-10-08)
==================

- Added documentation. [#323, #319, #315, #308, #300]
- Bug fixes in model fitting [#325], line lists [#326], and cubeviz data labels [#313]
- Updated vispy dependency. [#311]


1.0.2 (2020-09-23)
==================

- Incorporate latest releases of dependencies.


1.0.1 (2020-09-18)
==================

- Fix issue from release.


1.0 (2020-09-18)
================

- Official release.


0.1 (2020-08-26)
================

- Initial release.
