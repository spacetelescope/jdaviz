2.3 (unreleased)
================

New Features
------------

- There are now ``show_in_sidecar`` and ``show_in_new_tab`` methods on all the
  helpers that display the viewers in separate JupyterLab windows from the
  notebook. [#952]

- The line analysis plugin now includes logic to account for the background
  continuum. [#1060]

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
