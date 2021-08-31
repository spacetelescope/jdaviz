******************
Specviz Selections
******************

This section explains the working theory behind the selection tool and was inspired by
the the introduction of two methods to the Specviz helper:

* ``specviz.get_spectra()``
* ``specviz.get_spectral_regions()``

Data loaded in are imported into Jdaviz and immediately converted into a
``specutils.SpectralRegion`` object. These are a spectral analog to the Astropy ``regions``
(which instead focuses on spatial regions and their associated WCS). These spectral regions
are returned by the ``specviz.get_spectra()`` method.

The selection tool allows the user to specify a specific range on the graph.
This is defined by the underlying Glue library upon which Jdaviz relies on as a
"Glue Subset." Thus throughout the software documentation, we will refer to these
user defined ranges as "subsets." Effectively, the selection tool defines a mask that
can be thought of as "definition" of which data is and is not included in the subset.
Upon extraction via ``specviz.get_spectral_regions()``, the method will return a new
``specutils.SpectralRegion`` object that applies that mask atop of the proper region
(data) displayed, and realizes the subset the user defined in Jdaviz.
