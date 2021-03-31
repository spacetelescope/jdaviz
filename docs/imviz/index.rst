.. image:: ../logos/imviz.svg
   :width: 400

.. _imviz:

#####
Imviz
#####

Imviz is a tool for visualization and quick-look analysis for 2D astronomical
images. Like the rest of `jdaviz`, it is written in the Python programming
language, and therefore can be run anywhere Python is supported
(see :doc:`../installation`). Imviz is built on top of the
`astrowidgets <https://astrowidgets.readthedocs.io>`_ using
`Glupyter <https://glue-jupyter.readthedocs.io>`_ backend, providing a visual,
interactive interface to the analysis capabilities in that library.

Imviz allows images to be easily displayed and examined. It supports WCS
and so on. (TODO: Add content.)


Using Imviz
-----------

To run Imviz in a notebook::

    from jdaviz import Imviz
    imviz = Imviz()
    imviz.app

To run the two-panel version instead::

    from jdaviz import ImvizTwoPanel
    imviz = ImvizTwoPanel()
    imviz.app

(TODO: Add content.)
