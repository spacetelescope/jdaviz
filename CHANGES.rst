2.1 (unreleased)
================

New Features
------------

- Support for units and BlackBody in modeling plugin. [#953]

Cubeviz
^^^^^^^

Imviz
^^^^^

- New ``imviz.create_image_viewer()`` and ``imviz.destroy_viewer()`` methods
  to allow users to programmatically create and destroy image viewers. [#907]

- New plugin to control image linking via GUI. [#909]

- New plugin to perform simple aperture photometry. [#938]

Mosviz
^^^^^^

- New toggle button to lock/unlock viewer settings (x-limits in 1d and 2d spectrum viewers and 
  stretch and percentile for 2d spectrum and image viewers). [#918]

- Ability to add custom columns and change visibility of columns in the table. [#961]

Specviz
^^^^^^^

- MIRI s2d files can now be loaded into Specviz2d. [#915]

API Changes
-----------

- Removed unused ``jdaviz.core.events.AddViewerMessage``. [#939]

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

- ``vue_destroy_viewer_item`` called twice on destroy event. [#676, #913]

Cubeviz
^^^^^^^

Imviz
^^^^^

- ``imviz.get_interactive_regions()`` no longer produces long traceback
  for unsupported region shapes. [#906]

- Imviz now parses some image metadata into ``glue`` and understands
  ELECTRONS and ELECTRONS/S defined in FITS BUNIT header keyword. [#938]

Mosviz
^^^^^^

Specviz
^^^^^^^

- Fixed a bug where ``specviz.get_model_parameters()`` crashes after fitting
  a Gaussian model in the Model Fitting plugin. [#976]

Other Changes and Additions
---------------------------

- Cubeviz now loads data cube as ``Spectrum1D``. [#547]
- The new template load system in ``ipyvue`` is used, which enables hot reload. [#913]

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
