
.. _quickstart:

**********
Quickstart
**********

Once installed, ``jdaviz`` can be run either in a Jupyter notebook or as a standalone web application.
Detailed workflows are given within the documentation, but some quick-start tips are given below.


As a Standalone Application
===========================

.. note::
    This feature is currently in development for the new generalized version of jdaviz, so the following may change in an upcoming release.

``jdaviz`` provides a command-line tool to start the standalone desktop application in a browser. To see the syntax and usage, from a terminal, type::

    jdaviz --help

.. jdavizclihelp::

Jdaviz is now intended to be used in a flexible, generalized layout rather than the older "configs", but
these deprecated configurations are still available from the command line. For compatibility with the older
configurations during their deprecation period, you can specify ``--layout=flexible`` to launch the new
generalized Jdaviz from the command line. To load a file into a configuration::

    jdaviz --layout=[imviz|specviz|cubeviz|mosviz|specviz2d|flexible] --filepath=/path/to/data/file --file_format=FileFormat

This will warn that the ``--layout`` argument is deprecated. In the future, running the ``jdaviz``
command will simply launch the generalized Jdaviz application without going through a launcher page.
You can also specify filepath and file format using the shorter ``-fp`` and ``-ff``, respectively, which
may be useful if loading multiple files. Note that the file format is generally required because many files can be read,
for example, using either the image loader or the catalog loader. See :ref:`loaders-formats` for the current list
of available data formats. Note that you will need to enclose multi-word formats in quotation marks, for example
``--file_format='1D Spectrum'``.

Currently, running the command ``jdaviz`` without any additional input will still run a launcher. To launch the
modern generalized ``jdaviz`` from here, click the Jdaviz logo in the top right.
Alternatively, you can still use the deprecated legacy functionality to select a file from the
file picker, which will identify the best configuration according to the file type. You can also
select the desired deprecated configuration by clicking one of the bottom buttons without specifying
a file. A blank configuration will open and the IMPORT button will be available to select
a file from the file picker.



In a Jupyter Notebook
=====================

The power of Jdaviz is that it can integrated into your Jupyter notebook workflow::

    import jdaviz as jd

    jd.show()
    jd.load('filename.fits', format='Image', data_label='MyData')

Jdaviz also provides a directory of :ref:`sample notebooks <sample_notebook>`
to test the application, located in the :gh-tree:`notebooks` sub-directory of the Git repository.


Customizing Notebook Display Layout
-----------------------------------

By default, calling ``show()`` will display your visualization tool *inline* in your notebook,
that is the tool will show underneath the notebook cell it was called from:

.. code-block:: python

    import jdaviz as jd

    jd.show()
    jd.load('filename.fits', format='Image')

The height of the application in the notebook can be changed by passing an integer
specifying the height in pixels to the ``height`` argument of ``show``, for example:

.. code-block:: python

    jd.show(height=800)

You can additionally specify the location with the ``loc`` argument.
For example, ``inline`` can be specified manually with:

.. code-block:: python

    jd.show(loc='inline')

Detached Popout
^^^^^^^^^^^^^^^
Jdaviz can also be displayed in a detached window, separate from your working Jupyter interface.

.. note:: Popups must be allowed in your browser to display properly.

The following shows ``jdaviz`` in a new popout window:

.. code-block:: python

    jd.show(loc='popout')

To manually specify the anchor location, append the anchor to popout, separated by a colon:

.. code-block:: python

    jd.show(loc='popout:window')

You can also popout to a new browser tab by specifying a ``tab`` anchor:

.. code-block:: python

    jd.show(loc='popout:tab')


Sidecar (Jupyter Lab)
^^^^^^^^^^^^^^^^^^^^^

In Jupyter Lab, ``sidecar`` provides additional methods to customize where to show the viewer
in your workspace. The following shows ``jdaviz`` in the default sidecar location,
to the right of the notebook:

.. code-block:: python

    jd.show(loc='sidecar')

To manually specify the anchor location, append the anchor to sidecar, separated by a colon:

.. code-block:: python

    jd.show(loc='sidecar:right')

Other anchors include: ``split-right``, ``split-left``, ``split-top``, ``split-bottom``,
``tab-before``, ``tab-after``, ``right``. An up-to-date list can be found at
`jupyterlab-sidecar <https://github.com/jupyter-widgets/jupyterlab-sidecar>`_.

Multiple Jdaviz Instances
-------------------------

By default, any commands sent to ``jdaviz`` will be sent to the current default application.
For example:

.. code-block:: python

    import jdaviz as jd

    jd.show()  # shows the default application
    jd.load('filename.fits', format='Image')  # loads into the default application

However, multiple independent instances of Jdaviz can be created and displayed in the same notebook.
To do so, create a new Jdaviz app instance and store it in a custom variable:

.. code-block:: python

    import jdaviz as jd

    app1 = jd.new_app()
    app2 = jd.new_app()

    app1.show(loc='sidecar:right')
    app2.show(loc='sidecar:left')

    app1.load('filename1.fits', format='Image')
    app2.load('filename2.fits', format='Image')


You can also access the current default application with :py:func:`jdaviz.gca` (get current application), and pass arguments to :py:func:`jdaviz.new_app` or :py:func:`jdaviz.gca` to manage which is considered the current application.




Keyboard Shortcuts
------------------

The following keyboard shortcuts are available when your cursor is over an image viewer.
Some shortcuts require a specific plugin to be open.

.. list-table::
   :header-rows: 1
   :widths: 20 50 30

   * - Key
     - Action
     - Requirements
   * - ``b``
     - Blink to next image
     - 2+ images loaded
   * - ``B``
     - Blink to previous image
     - 2+ images loaded
   * - ``l``
     - Plot line profiles at cursor position
     - :ref:`Line Profile (XY) <plugins-image-profiles>` plugin open
   * - ``m``
     - Add marker at cursor position
     - :ref:`Markers <info-markers>` plugin open
   * - ``d``
     - Set distance measurement point (press twice to complete)
     - :ref:`Markers <info-markers>` plugin open
   * - ``Alt+d`` (``Option+d``)
     - Set distance point with snap to nearest marker
     - :ref:`Markers <info-markers>` plugin open
   * - ``r``
     - Clear all markers and distance lines
     - :ref:`Markers <info-markers>` plugin open
