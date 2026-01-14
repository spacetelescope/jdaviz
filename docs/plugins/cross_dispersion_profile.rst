.. _plugins-cross_dispersion_profile:

*************************
Cross Dispersion Profile
*************************

.. plugin-availability::

Analyze cross-dispersion profiles in 2D spectra.

Description
===========

The Cross Dispersion Profile plugin extracts and displays profiles perpendicular
to the dispersion direction in 2D spectroscopic data.

**Key Features:**

* Extract spatial profiles
* Analyze trace position
* Profile visualization
* Background estimation

**Available in:** Specviz2d

UI Access
=========

Click the :guilabel:`Cross Dispersion Profile` icon in the plugin toolbar
to view cross-dispersion profiles.

API Access
==========

.. code-block:: python

    plg = specviz2d.plugins['Cross Dispersion Profile']
    # Access profile data

.. plugin-api-refs::
   :module: jdaviz.configs.specviz2d.plugins.cross_dispersion_profile.cross_dispersion_profile
   :class: CrossDispersionProfile

See Also
========

* :ref:`specviz2d-plugins` - Specviz2d plugin documentation
