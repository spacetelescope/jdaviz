***********************************
Using Specviz in a Jupyter Notebook 
***********************************

Specviz is developed to fully support analyzing spectra within your existing `Jupyter notebooks <https://jupyter.org/>`_! To use Specviz, install jdaviz in your notebook's python environment and add a new cell wherever you would like to use Specviz.

    >>> # Import specviz
    >>> from jdaviz import specviz
    >>> # Instantiate an instance of Specviz
    >>> specviz = SpecViz()
    >>> # Display Specviz
    >>> specviz.app

To extract the data currently loaded into the viewer:
::

    specviz.app.get_data_from_viewer('spectrum-viewer')

To learn how to add data and use Specviz, including the corresponding API calls, please see our other Specviz Documentation
