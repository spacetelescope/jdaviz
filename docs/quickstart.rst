
.. _quickstart:

Quickstart
==========

Once installed, ``jdaviz`` can be run either in a Jupyter notebook or as a standalone web application.
Detailed workflows are given within the documentation, but some quick-start tips are given below.

In a Jupyter Notebook
---------------------

The power of Jdaviz is that it can integrated into your Jupyter notebook workflow::

    import jdaviz as jd

    jd.show()
    jd.load('filename.fits', format='Image', data_label='MyData')

Jdaviz also provides a directory of :ref:`sample notebooks <sample_notebook>`
to test the application, located in the :gh-tree:`notebooks` sub-directory of the Git repository.


As a Standalone Application
---------------------------

.. note::
    This feature is currently in development for the new generalized version of jdaviz. Stay tuned for updates!
