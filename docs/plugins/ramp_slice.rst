.. _plugins-ramp_slice:
.. rst-class:: section-icon-mdi-tune-variant

**********
Ramp Slice
**********

.. plugin-availability::

Navigate through detector ramp integrations and groups.

Description
===========

.. warning::

   Ramp functionality is still under active development. Stay tuned for updates!

The Ramp Slice plugin provides controls for navigating through integration
and group dimensions in JWST detector ramp data.

**Key Features:**

* Integration navigation
* Group navigation
* Difference/group display modes
* Synchronize slice display

**Available in:** :ref:`rampviz`

UI Access
=========

Use the ramp slice controls to navigate through integrations and groups.

API Access
==========

.. code-block:: python

    plg = rampviz.plugins['Ramp Slice']
    plg.integration = 5
    plg.group = 10

.. plugin-api-refs::
   :module: jdaviz.configs.cubeviz.plugins.slice.slice
   :class: RampSlice

See Also
========

* :ref:`rampviz` - Rampviz documentation
