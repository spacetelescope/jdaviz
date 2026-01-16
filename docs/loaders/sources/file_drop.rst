:excl_platforms: mast

.. _loaders-source-file-drop:

************************
Loading via File Drop
************************

The file drop loader allows you to drag and drop files directly into the Jdaviz interface.

In the Jdaviz application interface, simply drag and drop a file from your file system
onto the viewer area. The application will automatically detect the file type and
prompt you to select the appropriate format if needed.

For cases where the Jupyter kernel is not running on the local machine,
the file drop loader provides the capability to upload files from the local
machine.  Otherwise, the file drop loader provides the same functionality as
the :ref:`loaders-source-file` loader but with a more interactive interface.

UI Access
=========

.. wireframe-demo::
   :demo: loaders,loaders@1000:select-dropdown=Source:file drop,loaders:highlight=#source-select
   :enable-only: loaders
   :demo-repeat: false

API Access
==============

When using Jdaviz in a Jupyter notebook:

.. code-block:: python

    import jdaviz as jd
    jd.show()

    jd.loaders['File Drop'].show()

    # The file drop interface will appear in the viewer
    # Drag and drop your file onto the interface
