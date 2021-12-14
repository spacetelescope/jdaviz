.. _cubeviz-import-data:

***********
Import Data
***********

There are two primary ways in which you can load your data into the Cubeviz
application. Cubeviz supports loading FITS files that can be parsed as 
:class:`~specutils.Spectrum1D` objects, in which case the application will
attempt to automatically parse the data into the viewers as described in 
:ref:`cubeviz-display-cubes`, including the 1D spectrum viewer.

Importing data through the GUI
------------------------------

The first way you can load your data into the Cubeviz application is
by clicking the :guilabel:`Import` button at the top left of the application's 
user interface. This opens a dialogue where you can navigate your local
file system (single click to enter a folder) and select the path of a file 
that can be parsed as a :class:`~specutils.Spectrum1D`:

.. image:: img/cubeviz_import_data.png

After clicking :guilabel:`Import`, the data file will be parsed and loaded into the 
application. A green success message will appear if the data import 
was successful. Afterward, the new data set can be found in the :guilabel:`Data` 
tab of each viewer's options menu as described in :ref:`cubeviz-selecting-data`.

.. _api-import-cubeviz:

Importing data via the API
--------------------------

Alternatively, if you are working in a coding environment like a Jupyter
notebook, you have access to the Cubeviz helper class API. Using this API,
you can load data into the application through code using the
:meth:`~jdaviz.core.helpers.ConfigHelper.load_data`
method, which takes as input either the name of a local file or a 
:class:`~specutils.Spectrum1D` object.

    >>> from jdaviz import Cubeviz
    >>> cubeviz = Cubeviz()
    >>> cubeviz.load_data("/Users/demouser/data/cube_file.fits")  # doctest: +SKIP
