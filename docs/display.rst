.. _display:

***********************************
Customizing Notebook Display Layout
***********************************

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
---------------
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
---------------------

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
