********************************
Jdaviz Design and Infrastructure
********************************

.. note::

    At the time of writing, Jdaviz was still in heavy development.
    If you notice that this page has fallen behind, please
    `report an issue to the Jdaviz GitHub issues <https://github.com/spacetelescope/jdaviz/issues/new>`_.

This section outlines the top-level structure of Jdaviz. At the highest level,
Jdaviz layers different, sometimes changing technologies in the Jupyter platform
to do its visualization, and therefore provides a framework for these technologies
to work together. This document describes that framework, as well as the high-level
sets of components needed for the Jdaviz use cases; it lists the layers of the Jdaviz
framework in essentially the order in which they contact users in a typical
visualization-heavy workflow. An overview of the layers is in this diagram,
and each is described in more details below:

.. figure:: jdaviz.svg
    :alt: Jdaviz design and infrastructure chart.

    This figure illustrates the basics of Jdaviz design and infrastructure.
    The top layer contains user-facing applications and supported
    interfaces. The middle layer encapsulates its component widgets and the
    visualization libraries involved. The bottom layer consists of low-level
    data analysis and I/O libraries.

Jdaviz: Interfaces and Applications
===================================

Interfaces
----------

"Interfaces" are the tools the user is using to access the analysis tools.
The word "platform" might at first seem more applicable, but in this case
all of the interfaces are using Jupyter as the platform, to ensure a
consistent look-and-feel and a single platform for which to target the tools.
The interfaces are then specific *interfaces* through which users access this platform.
The target interfaces are:

* **Notebook/Lab**: While the actual app the user is running may be either
  `JupyterLab <https://jupyterlab.readthedocs.io>`_ or the "classic"
  `Jupyter Notebook <https://jupyter-notebook.readthedocs.io>`_, the interface idiom
  is similar - a relatively linear notebook-style workflow.
  This is the most flexible interface as it allows the user to implement their own
  code free-form in the notebook and run it with cells using Jdaviz tools.
  Hence this layer particularly emphasizes modularity and flexibility.
* **Desktop**: This interface is meant to behave like a more traditional "desktop app",
  i.e., a window with a fixed set of functionality and a particular layout for a
  specific set of scientific use cases. This interface is accessed via a
  `Voilà <https://voila.readthedocs.io>`_ wrapper that loads the same machinery as the
  other interfaces but presents the outputs of notebook "cells" as the only view.
  This trades the flexibility of the notebook interface for a consistent and
  reproducible layout and simpler interface without the distraction of the notebook
  and associated code.
* **MAST**: This interface is used by the
  `Mikulski Archive for Space Telescopes (MAST) <https://archive.stsci.edu>`_,
  which embeds Jdaviz applications inside existing websites. This provides the
  capabilities of the Jdaviz tools in other websites, while providing the sites
  the freedom to be designed and laid out independently from the visualization
  tool framework. While this even further restricts the functionality, it provides
  maximum flexibility in embedding.

Each of these interfaces uses a common set of applications implemented in Python
and leveraging ipywidgets_ as the communication layer between Python and the
JavaScript-level layout, rendering, and interactivity libraries. Hence the following
layers are primarily implemented in Python, but utilize tools like ipyvuetify_ and
ipygoldenlayout_ to allow the Python code to interact with the JavaScript
implementations at the interface level.

Applications
------------

The next layer is the "application" layer for visualization. These applications
in and of themselves do not implement significant functionality, but are particular
layouts that combine the lower layers to accomplish specific visualization tasks.
They have particular science goals that are then mainly reflected in the capabilities
of the lower layers (widgets), but the functionality in them are connected together
to solve those goals in the applications. The desktop app and embedded website
interfaces will typically wrap exactly one of these applications, while the notebook/lab's
additional flexibility means it may include multiple applications, or a mix of
applications and individual widgets.

Specific target applications include:

* *Specviz*: A view into a single astronomical spectrum. It provides a UI to
  view the spectrum, as well as perform common scientific operations like marking
  spectral regions for further analysis (e.g., in a notebook), subtracting continua,
  measuring and fitting spectral lines, etc.
* *Mosviz*: A view into many astronomical spectra, typically the output of a
  multi-object spectrograph (e.g.,
  `JWST NIRSpec <https://jwst.nasa.gov/content/observatory/instruments/nirspec.html>`_).
  It provides capabilities for individual spectra like Specviz, but for multiple spectra
  at a time along with additional contextual information like on-sky views of the
  spectrograph slit.
* *Cubeviz*: A view of spectroscopic data cubes (e.g., from
  `JWST MIRI <https://jwst.nasa.gov/content/observatory/instruments/miri.html>`_),
  along with 1D spectra extracted from the cube. In addition to common visualization
  capabilities like viewing slices or averages in image or wavelength space,
  the application will provide some standard manipulations like smoothing, moment maps,
  parallelized line fitting, etc.
* *Imviz*: An image-viewer for 2D images leveraging the same machinery as the other
  applications. While this application is not intended to encapsulate a complete
  range of astronomical imaging-based workflows, it enables quick-look style
  visualization of images in a way that is compatible with the rest of the Jdaviz framework.

Application Engine
^^^^^^^^^^^^^^^^^^

The applications are driven by a shared layer that connects the "high-level" layers
to the "low-level" layers, as discussed below. The application engine manages this
shared layer. Or more concretely, the application engine is the Python-level object
that can be accessed by the user in any of the interfaces to interact with a particular
application. It contains several sub-pieces to achieve this goal. The most directly-used
portion of this is the layout configuration management: Jdaviz applications specify
the UI layout they use via this part of the application engine. The application engine
then constructs the layout using glue-jupyter_, ipywidgets_, and other layout
libraries like ipyvuetify_. The application engine also is responsible
for managing application-level events and data. This is done via the built-in functionality
of the `glue-core <https://github.com/glue-viz/glue>`_ library, so the application engine
also provides the interface for registering new functionality (both UI and data/processing)
via glue-core's registries.

Note that most of the application engine implementation belongs in glue-jupyter_
or glue-core, as it is not unique to Jdaviz (or even astronomy). However, Jdaviz has
customized it for specific use cases, though some of the implementations might be moved
upstream as Jdaviz matures, especially if they are useful beyond Jdaviz.

Visualization: Component Widgets
================================

The "component widgets" layer is the first of the "low-level" layers, i.e., the layers
that actually implement specific visualization and analysis functionality. These widgets
are self-contained and in general are meant to be composed in applications.
However, for the notebook/lab interface, component widgets can and should be used directly
by users for specialized scientific workflows. Component widgets in principle can be
developed in any framework that can be exposed as an ipywidgets_ widget, although
currently the plan is that most will be glue-jupyter_ viewers
(using `bqplot <https://bqplot.readthedocs.io/en/latest/>`_ backend)
combined with ipyvuetify_ layouts (that builds on Vue.js). As with the application engine,
the general goal is to push any functionality necessary for these widgets upstream
and not confine them to Jdaviz, but with allowances that some customization may be needed
for Jdaviz-specific elements.

.. note::

    GlueViz in the diagram above encapsulates all the libraries tied to the Glue
    visualization ecosystem. They include but not limited to glue-core, glue-jupyter,
    glue-astronomy, and bqplot-image-gl. Due to the complexity of Jdaviz's
    dependency tree, we will not mention all of them in this section.

Known component widgets for the target applications include:

* *Spectrum viewer*: A widget that shows a 1D astronomical data set, primarily aimed at
  astronomical spectra. Interactivity includes panning, zooming, and region marking.
* *Image viewer*: A widget that shows an astronomical image, along with its on-sky
  coordinates when WCS are available. Interactivity includes panning, zooming, stretch
  (contrast and scale), and cut values.
* *Cube slicer*: A widget for displaying slices or similar aggregate operations on
  spectroscopic data cubes. While similar to the image viewer in appearance and
  interactive capabilities, the core difference is that the main data object is
  expected to be a data cube rather than a 2D image, and this is reflected in additional
  aggregation/slicing operations.
* *Table viewer*: A widget to show tabular datasets like `astropy.table.Table` objects.
  Primarily meant to be combined with other viewers to examine the complete set of
  properties from a selection made in another viewer. Interactivity focuses on sorting
  and selection of specific rows (to then be highlighted in other viewers or interacted
  with in notebook/lab).

In addition to the component widgets above, there are also *plugins* that go with
them to provide the necessary user interactions. Each plugin is specialized to do one
thing, e.g., a "model fitting" plugin to allow users to fit
:ref:`astropy models <astropy:astropy-modeling>` to spectra.

Data Analysis and I/O Libraries
===============================

The above layers are focused primarily on visualization. All actual *operations* and
analysis tasks to be applied to visualized astronomical dataset are to be implemented
in the respective Python libraries. It is important to note that these libraries are
*independent* efforts from Jdaviz, and can therefore be used in whole, part, or not
at all with the Jdaviz tools. This allows a full range of workflows, while also
maintaining transparency to scientific users in regards to exactly how an operation
in the Jdaviz tools actually works; i.e., they can at any time use the library directly
instead of accessing it through Jdaviz.

Some common libraries include (this list is not exhaustive):

* astropy_ (general astronomy-related functionality)
* `specutils <https://specutils.readthedocs.io>`_ (spectral analysis)
* `photutils <https://photutils.readthedocs.io>`_ (imaging photometry)

Note that those libraries themselves depend on the wider scientific Python ecosystem,
so the list and the diagram above do not fully cover all of Jdaviz's dependencies,
but are the primary "top-level" data analysis or I/O libraries that most users are likely
to focus on to complement or extend their Jdaviz workflows.

.. note::

    In the diagram above, optional dependencies of Jdaviz have dotted lines.
    Optional dependencies mean they are only required for certain Jdaviz
    workflows and are not explicitly installed by default when you install Jdaviz.


.. _ipywidgets: https://ipywidgets.readthedocs.io
.. _ipyvuetify: https://github.com/mariobuikhuizen/ipyvuetify
.. _ipygoldenlayout: https://github.com/nmearl/ipygoldenlayout
.. _glue-jupyter: https://github.com/glue-viz/glue-jupyter
