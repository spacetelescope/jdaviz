Glupyter Framework Overview
===========================

The glue-jupyter ("glupyter") package supports interacting with and
visualizing data within the Jupyter environment using core elements from
the Glue python package. It is distinct because unlike the more
prominent Glue package, glupyter does not leverage Qt as the front-end
gui library. Instead, glupyter maintains the separation between the data
model (e.g. the core elements from Glue that are not dependent on the
front-end library), and the view of the data (in this case, web-based
tooling provided by Jupyter).

Glupyter implements a base ``JupyterApplication`` object through which
users can manage their data, create viewers, and add links between data
sets. The data management and linking are controlled separate from the
viewers in that changes made directly to the data state propagate to the
UI (i.e. the UI acts strictly as the view to the data state, not the
controller of the data state). The viewers themselves are based on the
IPyWidget package which allows the creation of widgets that can be used
and interacted with in python, but rendered in a javascript environment.

There are two distinct use cases for the glupyter environment: first, as
a means to procedurally interact with pieces of a user's workflow *in
addition* to their work in e.g. a Jupyter Notebook; and second, to
provide users a web-based gui to interact with and visualize their data
while hiding the Jupyter context, e.g. a standalone web application.
These two use cases describe a data-first and gui-first approach,
respectively. This document will focus on detailing the design of the
gui-first approach, depicted in the following diagram.

.. note::
    The ``.xml`` file in the ``img`` directory can be used to edit the
    diagram using applications like, e.g.,
    `draw.io <https://draw.io>`_.

.. image:: ../img/glue-jupyter_diagram.png

General user interface design
-----------------------------

The general user interface is a parallel design to the Qt desktop
interface. It is meant to be the standard scaffolding supporting the
implementation of the individual viewers, data management functions, and
user plugins in much the same way that the Qt desktop version does.

The implementation leverages three primary packages:

1. ``glue-jupyter``: handles the data and state management, including
   the plugin infrastructure that provides the registry of available
   viewers, analysis functions, etc.
2. ``ipyvuetify``: provides the ui widgets for composing the web-based
   front-end.
3. ``ipygoldenlayout``: an additional widget that supports tabbing and
   docking the displayed viewers.

Widget design
-------------

There are two potential approaches to designing widgets using the
ipyvuetify paradigm: composing everything in the python widget subclass
as a collection of python ipyvuetify components; or break the state of
the widget from its view and implement the latter as template file.

The first approach, while conceptually easier to understand, has a few
shortcomings. Chief of which is the fact that the view logic is jumbled
up with the state of the widget. That is, we are composing the visual
representation of the widget, defining the viewer logic, and defining
its state all during initialization. This is both extremely verbose --
as the nested nature of the Vuetify library means many of the
intermediate widget classes (e.g. ``Layout``, ``Container``, ``Row``,
etc) need to be defined as instance attributes -- and, perhaps more
severe, makes it more difficult to design reactive UI behavior that
responds to state changes in the widget classes automatically. This
means that we must constantly interact with the UI widgets to change
their state directly instead of simply having the UI *respond* to state
changes in the custom widget class. Fundamentally, this approach means
that *in addition to* the state of the custom widget (e.g. ``Toolbar``),
we must also be aware of the state of *each individual widget* that
composes it. Put another way, there's no *central source of truth* for
the state of the custom widget as each element may contain some kind of
stateful information about itself.

An alternative design is to have each widget implemented as a
``VuetifyTemplate`` object. In this way, custom widgets are defined as
ipywidget-like elements whose visual representation is described by a
Vuetify template. The template composes the visual representation of the
custom widget using the Vue formalism, while the state is implemented as
trailets on the custom widget class. The template reads and responds to
state and state changes on the custom widget, and the custom widget need
not know or care about how that state is being represented (i.e. the
only state is that of the custom widget).

With this approach in hand, all widgets in the glupyter gui are composed
of two files: the python file declaring the widget class (e.g.
``Toolbar``), and the ``.vue`` file containing the template describing
how the widget is to be rendered using components from the Vuetify
library in the nominal Vue framework. In this way, there is a clear
separation between the state of each widget (contained in the python
file) and the view of that state (contained in the Vuetify file). Below
is an example of what such a widget might looking like:

.. code:: markup

    <template>
      <v-toolbar>
        <v-toolbar-side-icon></v-toolbar-side-icon>
        <v-toolbar-title>Title</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-toolbar-items class="hidden-sm-and-down">
          <v-btn flat>Link One</v-btn>
          <v-btn flat>Link Two</v-btn>
          <v-btn flat>Link Three</v-btn>
        </v-toolbar-items>
      </v-toolbar>
    </template>

.. code:: python

    with open(os.path.join(os.path.dirname(__file__), "toolbar.vue")) as f:
        TEMPLATE = f.read()


    class Toolbar(VuetifyTemplate):
        template = Unicode(TEMPLATE).tag(sync=True)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            ...

The state of the widget is contained in attributes on the python class
which allows them to be referenced in the Vuetify template. Notice in
the example below that the ``v-btn`` instances simply respond to the
state of the ``Toolbar`` widget's ``button_names`` attribute, and the
``Toolbar`` class could know nothing about *how* that state is being
represented.

.. code:: markup

    <v-toolbar-items class="hidden-sm-and-down">
      <v-btn flat v-for="name in button_names">{{ name }}</v-btn>
    </v-toolbar-items>

.. code:: python

    class Toolbar(VuetifyTemplate):
        template = Unicode(TEMPLATE).tag(sync=True)
        button_names = List(['One', 'Two', 'Three']).tag(sync=True)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            ...

The design of the interface can be broken down into three main areas:
the toolbar, the navigation drawer, and the dock area. Each of these
areas represents a single primary widget in the web-based application
built using ``ipyvuetify``, unified in the ``Application`` class.

Widget communication
--------------------

There are two fundamental forms of communication between widgets:
direction communication using the ``observer`` pattern, and global
communication using the centralized event hub provided by Glue.

Direct messaging
~~~~~~~~~~~~~~~~

Because the software stack utilizes the ipywidgets package, attributes
on defined widget classes (e.g. ``button_names`` on the ``Toolbar``
widget in the example above) are implemented as traitlets, which can be
observed for changes. In order to register callbacks in response to
changes to attributes defined on widget classes, interested parties must
have a direct reference to the widget instance.

For example, if we consider that the ``Toolbar`` class above is
implemented as part of a broader ``Application``, we can respond to
changes in the ``button_names`` traitlet by setting a callback function
in the ``observe`` method of the ``Toolbar`` widget:

.. code:: python

    class Application(VuetifyTemplate):
        template = Unicode("""
            <template>
                <custom-toolbar></custom-toolbar>
            </template>
            """).tag(sync=True)

        def __init__(self, *args, **kwargs):
            # Associate the `custom-toolbar` element with the `Toolbar` class
            kwargs.set_default('components', {}).update({'custom-toolbar': Toolbar()})
            super().__init__(*args, **kwargs)

            self.toolbar = self.components['custom-toolbar']

            # This sets up the child-to-parent behavior
            self.toolbar.observe(self.on_button_names_changed, names='button_names')

            # Here we take advantage of the way trailets work

        def on_button_names_changed(self, *args, **kwargs):
            print("The list of button names has been changed.")

This type of direct child-to-parent (i.e. the parent is responding to
changes on the child) communication compliments the direct
parent-to-child communication (i.e. the parent passing data to the
child). However, this does not solve the application-level issue of
multiple components, conceivably several levels deep, trying to interact
with and pass data to each other. In this case, we decouple the widgets
from each other and instead have them interact with a central,
application-level communication hub through message objects.

Global event handing
~~~~~~~~~~~~~~~~~~~~

Communication between widgets that do not have a direct reference to
each other is handled using the ``Hub`` class of the glue-core package
(a dependency of glue-jupyter). The hub implements the publish/subscribe
paradigm wherein widgets subscribe to particular messages on the hub and
are notified whenever those messages are published by any part of the
UI. This system allows us to break hard dependencies between widgets in
the UI the require passing references around and to develop widgets
independently.