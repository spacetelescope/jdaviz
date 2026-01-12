.. _loaders-source-file-drop:

************************
Loading via File Drop
************************

The file drop loader allows you to drag and drop files directly into the Jdaviz interface.

Usage
=====

In the Jdaviz application interface, simply drag and drop a file from your file system
onto the viewer area. The application will automatically detect the file type and
prompt you to select the appropriate format if needed.

Notebook Usage
==============

When using Jdaviz in a Jupyter notebook:

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # The file drop interface will appear in the viewer
    # Drag and drop your file onto the interface

The file drop loader provides the same functionality as the :ref:`loaders-source-file`
loader but with a more interactive interface.
