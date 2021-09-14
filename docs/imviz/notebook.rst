.. _imviz_notebooks:

*********************************
Using Imviz in a Jupyter Notebook
*********************************

To run Imviz in a notebook::

    from jdaviz import Imviz
    imviz = Imviz()
    imviz.app

Imviz also provides programmatic access to its viewers using
`Astrowidgets <https://astrowidgets.readthedocs.io/en/latest/>`_ API.
For example::

    viewer = imviz.get_viewer('viewer-1')
    viewer.center_on((100, 100))
