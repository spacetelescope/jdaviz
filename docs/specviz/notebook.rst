***********************************
Using Specviz in a Jupyter Notebook
***********************************

Specviz is developed to fully support analyzing spectra within your existing `Jupyter notebooks <https://jupyter.org/>`_! To use Specviz, install jdaviz in your notebook's python environment and add a new cell wherever you would like to use Specviz.

    >>> # Import specviz
    >>> from jdaviz import SpecViz
    >>> # Instantiate an instance of Specviz
    >>> specviz = SpecViz()
    >>> # Display Specviz
    >>> specviz.app   #doctest: +SKIP

To extract the data currently loaded into the viewer do::

    specviz.get_spectra()

which yields a `specutils.Spectrum1D` object that you can manipulate however
you wish.  You can then load the modified spectrum back into the notebook via
the API described in :ref:`api-import`.

Alternatively, if you want more control over Specviz, you can access it the
via the lower-level application interface that connects to the ``glue-jupyter``
application level.  This is accessed via the ``.app`` attribute of the
`~jdaviz.configs.specviz.helper.SpecViz` helper class.  For example::

     specviz.app.get_data_from_viewer('spectrum-viewer')

For more on what you can do with this lower-level object, see the API sections
and the
`glue-jupyter documentation <https://glue-jupyter.readthedocs.io/en/latest/>`_
