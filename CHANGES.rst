2.11 (unreleased)
=================

New Features
------------

- Profile viewers now support plotting with profiles "as steps". [#1595, #1624]

- Use spectrum's uncertainty as weight when doing model fitting. [#1630]

- Line flux in the Line Analysis plugin are reported in W/m2 if Spectral Flux is given
  in Jy [#1564]

- User-friendly API access to plugins, with exposed functionality for:  line analysis, gaussian
  smooth, moment maps, compass, collapse, metadata, slice, plot options, model fitting, links
  control, export plot, and spectral extraction.
  [#1401, #1642, #1643, #1636, #1641, #1634, #1635, #1637, #1658, #1640, #1657, #1639]

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

- Increased size of Cubeviz configuration from 600px to 860px. [#1638]

Imviz
^^^^^

- Changing link options now updates immediately without needing to press "Link" button. [#1598]

- New tool to create a single-pixel spatial region on the image. [#1647]

Mosviz
^^^^^^

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

- Support for Horne/Optimal extraction. [#1572]

- Support for importing/exporting Trace objects as data entries. [#1556]

- 2D spectrum viewer now has info panel for pixel coordinates and value. [#1608]

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

Bug Fixes
---------

- Fixed loading data via the Import Data button on top-left of the application.
  [#1608]

- Floating menus are now attached to their selector element. [#1673]

- Remove model fitting equation length restriction. [#1685]

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

Specviz
^^^^^^^

Specviz2d
^^^^^^^^^

- Fixed default spectral extraction parameters when the background separation otherwise would have
  fallen directly on the edge of the image. [#1633]

- Fixed parser for Level 2 NIRSpec ``s2d`` files. [#1608]

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
