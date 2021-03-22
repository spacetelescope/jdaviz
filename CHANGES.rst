1.1 (2020-03-22)
----------------

    New Features
    ^^^^^^^^^^^^
    - Added methods to extract Mosviz data table to csv or astropy table. [#468]
    - Added methods to extract fitted models and model parameters to notebook. [#458]
    - Created a NIRISS dataset parser for Mosviz. [#394]
    - Added a Specviz2d configuration for two-dimensional spectra. [#410, #416, #421]
    - Added a redshift slider to Specviz. [#380, #453, #457]
    - Added new preset spectral line lists. [#379]
    - Added a debugging mode to show stdout and stderr on frontend. [#368]

    Bug Fixes
    ^^^^^^^^^
    - Fixed data selection update loop in UI menu. [#427, #456]
    - Fixed a bug when using the Gaussian Smooth plugin multiple times. [#441]
    - Fixed axis autoscaling when redshift slider has been used. [#404, #413]
    - Now properly raises an error when trying to load a non-existent file. [#384]
    - Fixed "Hide All" button behavior in line list plugin. [#383]
    - Fixed a WCS bug in Mosviz. [#377]
    - Fixed failing case of parsing cube extensions. [#374]

    Miscellaneous Changes and Additions
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    - Cleaned up the Model Fitting plugin UI. [#485]
    - Improved performance when loading multiple datasets. [#435]
    - Updated example notebooks. [#418]
    - Moved snackbar messages to top of UI. [#375]
    - Removed unused icons from toolbar. [#366]
    - Refactored the Unit Conversion plugin. [#360]
    - Many documentation updates/additions. [#340, #341, #343, #346, #347, 
      #349, #350, #351, #352, #357, #365, #376, #471, #481, #482, #483]

1.0.3 (2020-10-08)
------------------

- Added documentation. [#323, #319, #315, #308, #300]
- Bug fixes in model fitting [#325], line lists [#326], and cubeviz data labels [#313]
- Updated vispy dependency. [#311]


1.0.2 (2020-09-23)
------------------

- Incorporate latest releases of dependencies.


1.0.1 (2020-09-18)
------------------

- Fix issue from release.


1.0 (2020-09-18)
----------------

- Official release.


0.1 (2020-08-26)
----------------

- Initial release.


..
    Below is a template for the sections used in release changes.

    New Features
    ^^^^^^^^^^^^

    Bug Fixes
    ^^^^^^^^^

    Other Changes and Additions
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^
