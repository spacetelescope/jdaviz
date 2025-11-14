******************
Specviz Selections
******************

This section explains the working theory behind the selection tool and was inspired by
the the introduction of two methods to the Specviz helper:

* `~jdaviz.configs.specviz.helper.Specviz.get_spectra()`
* `~jdaviz.configs.specviz.helper.Specviz.get_spectral_regions()` (deprecated as of v4.1 in favor of
  `~jdaviz.configs.default.plugins.subset_tools.subset_tools.SubsetTools.get_regions()`)

Data loaded in are imported into Jdaviz and immediately converted into a
``specutils.SpectralRegion`` object. These are a spectral analog to the Astropy ``regions``
(which instead focuses on spatial regions and their associated WCS). These spectral regions
are returned by the ``specviz.get_spectra()`` method.

The selection tool allows the user to specify a specific range on the graph.
This is defined by the underlying ``glue`` library upon which Jdaviz relies on as a
"glue subset." Thus throughout the software documentation, we will refer to these
user defined ranges as "subsets." Effectively, the selection tool defines a mask that
can be thought of as "definition" of which data is and is not included in the subset.
Upon extraction via `~jdaviz.configs.default.plugins.subset_tools.subset_tools.SubsetTools.get_regions()`,
the method will return a new ``specutils.SpectralRegion`` object that applies that
mask atop of the proper region (data) displayed, and realizes the subset the user
defined in Jdaviz.
