.. _imviz-notebook:

*********************************
Using Imviz in a Jupyter Notebook
*********************************

To run Imviz in a notebook::

    from jdaviz import Imviz
    imviz = Imviz()
    imviz.app

Imviz also provides programmatic access to its viewers using
`Astrowidgets <https://astrowidgets.readthedocs.io/en/latest/>`_ API.
See `~jdaviz.core.astrowidgets_api.AstrowidgetsImageViewerMixin` for
available functionality. For example::

    viewer = imviz.default_viewer
    viewer.center_on((100, 100))
