.. _imviz-import-data:

***********
Import Data
***********

Imviz can load data in the form of a filename (string), .jpg, .png,
an astropy object, or a numpy array if the data is 2D.

Importing data through the GUI
------------------------------

The first way that users can load their data into the Imviz application is
by clicking the :guilabel:`Import` button at the top left of the application's
user interface. This opens a dialogue where the user can enter the path of file
that can be parsed as a :class:`~astropy.nddata.NDData` (2D data only), :class:`~astropy.io.fits.HDUList`,
or :class:`~astropy.io.fits.ImageHDU` in the text field:

.. image:: ../cubeviz/img/cubeviz_import_data.png

After clicking :guilabel:`Import`, the data file will be parsed and loaded into the
application. A notification will appear to let users know if the data import
was successful. Afterward, the new data set can be found in the :guilabel:`Data`
tab of each viewer's options menu as described in :ref:`cubeviz-selecting-data`

Importing data via the API
--------------------------

Alternatively, if users are working in a coding environment like a Jupyter
notebook, they have access to the Imviz helper class API. Using this API,
users can load data into the application through code using the `load_data`
method, which takes as input either the name of a local file or a
:class:`~astropy.nddata.NDData` (2D data only), :class:`~astropy.io.fits.HDUList`,
or :class:`~astropy.io.fits.ImageHDU` object.