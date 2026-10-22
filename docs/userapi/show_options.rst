.. _userapi-show_options:

************
Show Options
************

Configuration options for customizing how Jdaviz is displayed in Jupyter notebooks.

Description
===========

The ``show()`` method controls how Jdaviz applications are displayed in Jupyter environments.
You can customize the location (inline, sidecar, popout) and size (height) to fit your workflow.

Display Locations
=================

Inline Display
--------------

The default display mode shows Jdaviz inline in your notebook, directly below the cell:

.. code-block:: python

    import jdaviz as jd

    jd.show()  # Default: loc='inline'

This is equivalent to:

.. code-block:: python

    jd.show(loc='inline')

Inline display is best for:

* Quick data exploration
* Keeping visualization close to your code
* Simple notebooks with single visualizations
* Sharing notebooks where output should be preserved

Sidecar Display (JupyterLab)
-----------------------------

In JupyterLab, you can display Jdaviz in a separate pane while keeping your notebook visible:

.. code-block:: python

    jd.show(loc='sidecar')

This opens Jdaviz to the right of your notebook by default. You can specify the anchor position:

.. code-block:: python

    # Right side (default)
    jd.show(loc='sidecar:right')

    # New tab before current notebook
    jd.show(loc='sidecar:tab-before')

    # New tab after current notebook
    jd.show(loc='sidecar:tab-after')

    # Split pane to the right
    jd.show(loc='sidecar:split-right')

    # Split pane to the left
    jd.show(loc='sidecar:split-left')

    # Split pane on top
    jd.show(loc='sidecar:split-top')

    # Split pane on bottom
    jd.show(loc='sidecar:split-bottom')

.. note::
   Sidecar display is only available in JupyterLab. In classic Jupyter notebooks,
   ``loc='sidecar'`` will fall back to inline display.

Sidecar display is best for:

* Working with code and visualization simultaneously
* Keeping visualization visible while scrolling through notebook
* Complex analysis requiring reference to the visualization
* Multiple viewer workflows

Popout Display
--------------

Popout mode opens Jdaviz in a separate browser window or tab:

.. code-block:: python

    # New browser window
    jd.show(loc='popout')
    jd.show(loc='popout:window')

    # New browser tab
    jd.show(loc='popout:tab')

.. note::
   Your browser must allow popups for this to work. Check your browser's popup blocker settings.

Popout display is best for:

* Maximum screen real estate for visualization
* Multi-monitor setups
* Presentations and demonstrations
* Complex workflows requiring full screen visualization

Customizing Size
================

Height
------

You can customize the height of the display (primarily for inline mode):

.. code-block:: python

    # Height in pixels (integer)
    jd.show(height=800)

    # Height as string with units
    jd.show(height='800px')

The default height is typically 600 pixels. Adjust based on:

* Screen resolution
* Amount of data to display
* Notebook layout preferences
* Number of viewers in the configuration

Height affects:

* Inline display directly
* The application widget in all display modes
* All instances of the same configuration in the notebook

Customizing Title
-----------------

You can set a custom title for sidecar and popout displays:

.. code-block:: python

    # Custom title for sidecar
    jd.show(loc='sidecar', title='HST Image Analysis')

    # Custom title for popout
    jd.show(loc='popout', title='Spectrum Viewer')

If not specified, the title defaults to the configuration name (e.g., "jdaviz").

API Access
==========

Complete Signature
------------------

The full ``show()`` method signature:

.. code-block:: python

    def show(self, loc="inline", title=None, height=None):
        """Display the Jdaviz application.

        Parameters
        ----------
        loc : str
            Display location. Options:
            - 'inline': Below notebook cell (default)
            - 'sidecar': Separate pane (JupyterLab only)
            - 'sidecar:<anchor>': Specific sidecar position
            - 'popout': New browser window
            - 'popout:window': New browser window
            - 'popout:tab': New browser tab

        title : str, optional
            Window/tab title (for sidecar/popout only)

        height : int or str, optional
            Display height in pixels
        """

Top-Level API
-------------

The top-level ``jdaviz.show()`` also accepts these parameters:

.. code-block:: python

    import jdaviz

    # Auto-create instance with custom display
    jdaviz.show(loc='sidecar', height=800)

Configuration-Specific Examples
-------------------------------

**Imviz:**

.. code-block:: python

    from jdaviz import Imviz

    imviz = Imviz()
    imviz.show(loc='sidecar', height=1000, title='Image Viewer')

**Specviz:**

.. code-block:: python

    from jdaviz import Specviz

    specviz = Specviz()
    specviz.show(loc='popout:tab', title='Spectrum Analysis')

**Cubeviz:**

.. code-block:: python

    from jdaviz import Cubeviz

    cubeviz = Cubeviz()
    cubeviz.show(height=1200)  # Inline with custom height

Advanced Usage
==============

Multiple Instances
------------------

You can create and display multiple instances:

.. code-block:: python

    import jdaviz as jd

    # app 1 in sidecar
    jd1 = jd.new_app()
    jd1.show(loc='sidecar:split-left', title='Images')

    # app 2 inline
    jd2 = jd.new_app()
    jd2.show(loc='inline', height=600)

Dynamic Display
---------------

You can call ``show()`` multiple times to change the display:

.. code-block:: python

    # Start inline
    jd.show(loc='inline')

    # Later, move to sidecar
    jd.show(loc='sidecar')

    # Then popout
    jd.show(loc='popout')

Direct App Display
------------------

Alternatively, you can display the app object directly:

.. code-block:: python

    jd._app  # Display in notebook cell output

This is equivalent to ``jd.show(loc='inline')`` but provides less control over the display.

Details
=======

Browser Compatibility
---------------------

* **Popout mode**: Requires popup permission in browser
* **Sidecar mode**: JupyterLab 3.0+ recommended
* **Inline mode**: Works in all Jupyter environments

Performance Considerations
--------------------------

* Large datasets may render more slowly in inline mode
* Sidecar and popout modes can provide better performance for interactive work
* Height settings affect rendering time for inline display

Persistence
-----------

* Inline displays are saved with notebook output
* Sidecar and popout displays are ephemeral (not saved)
* Rerunning cells recreates all displays

See Also
========

* :ref:`userapi-cheatsheet` - Quick reference for common operations
* :ref:`quickstart` - Getting started guide
* :ref:`plugin-apis` - Plugin API documentation
