
.. _setup-platform:

Run Jdaviz on a Platform
=========================

Run Jdaviz on cloud-based astronomy platforms without local installation.

Available Platforms
-------------------

Time Series Integrated Knowledge Engine (TIKE)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The TIKE science platform provides a cloud-based Jupyter environment with Jdaviz pre-installed, optimized
for time series data analysis.

**Access:** `TIKE Science Platform <https://timeseries.science.stsci.edu/>`_

**Features:**

* No local installation required
* Pre-configured with Jdaviz and JWST tools
* Direct access to MAST data archives
* Collaborative notebooks
* Free for astronomical research use

**Getting Started:**

1. Visit the TIKE science platform
2. Log in with your STScI account (or create one)
3. Create a new notebook
4. Import and use Jdaviz:

   .. code-block:: python

       import jdaviz
       jdaviz.show()

Roman Science Platform (Nexus)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Roman Science Platform provides cloud-based analysis tools for Roman Space Telescope
data, with Jdaviz integrated for visualization.

**Access:** `Roman Science Platform <https://roman.ipac.caltech.edu/>`_

**Features:**

* Cloud-hosted notebooks
* Roman data access
* Pre-installed Jdaviz
* Scalable computing resources

**Getting Started:**

1. Request access to the Roman Science Platform
2. Launch a notebook server
3. Use Jdaviz in your notebooks:

   .. code-block:: python

       import jdaviz
       jdaviz.show()

Other Cloud Platforms
^^^^^^^^^^^^^^^^^^^^^

Jdaviz can also be used on general-purpose cloud platforms with Jupyter support:

Google Colab
""""""""""""

.. code-block:: bash

    # Install Jdaviz in Colab
    !pip install jdaviz

    import jdaviz
    jdaviz.show()

.. note::
    Some features may have limitations in Colab due to the environment constraints.

Binder
""""""

You can launch Jdaviz example notebooks directly in Binder without any installation.
Visit the `Jdaviz GitHub repository <https://github.com/spacetelescope/jdaviz>`_ and
look for the "Launch Binder" badge.

Platform Comparison
-------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Platform
     - Installation Required
     - Data Access
     - Compute Resources
     - Best For
   * - TIKE
     - No
     - MAST/JWST
     - Shared
     - JWST data
   * - Roman Nexus
     - No
     - Roman data
     - Scalable
     - Roman data
   * - Google Colab
     - Yes (pip)
     - User upload
     - Limited
     - Quick tests
   * - Binder
     - No
     - Demo data
     - Limited
     - Trying examples

Getting Help
------------

For platform-specific issues:

* **TIKE:** ; the `TIKE intro <https://github.com/spacetelescope/tike_content/blob/main/content/Introduction.md>`_
* **Roman Science Platform:** See the `Roman documentation <https://roman-docs.stsci.edu/data-handbook/roman-research-nexus>`_
* **Jdaviz issues:** File issues on the `GitHub repository <https://github.com/spacetelescope/jdaviz/issues>`_

See Also
--------

* :ref:`setup-local` - Install Jdaviz locally
* :ref:`quickstart` - Getting started guide
* :ref:`sample_notebook` - Example notebooks
