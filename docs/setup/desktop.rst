
.. _setup-desktop:

Install Standalone Desktop UI
==============================

The standalone desktop application provides a native Jdaviz experience without requiring
a Python installation or Jupyter environment.

System Requirements
-------------------

* macOS 10.15 or later, Windows 10/11, or Linux
* 4 GB RAM minimum (8 GB recommended)
* 500 MB available disk space

Download and Install
--------------------

macOS
^^^^^

1. Download the latest macOS installer (.dmg file) from the `Jdaviz releases page <https://github.com/spacetelescope/jdaviz/releases>`_
2. Open the .dmg file
3. Drag the Jdaviz application to your Applications folder
4. Launch Jdaviz from your Applications folder

.. note::
    On first launch, you may need to right-click and select "Open" to bypass macOS security restrictions
    for applications from unidentified developers.

Windows
^^^^^^^

1. Download the latest Windows installer (.exe file) from the `Jdaviz releases page <https://github.com/spacetelescope/jdaviz/releases>`_
2. Run the installer
3. Follow the installation wizard prompts
4. Launch Jdaviz from the Start menu or desktop shortcut

Linux
^^^^^

1. Download the latest Linux AppImage from the `Jdaviz releases page <https://github.com/spacetelescope/jdaviz/releases>`_
2. Make the AppImage executable:

   .. code-block:: bash

       chmod +x Jdaviz-*.AppImage

3. Run the AppImage:

   .. code-block:: bash

       ./Jdaviz-*.AppImage

Getting Started
---------------

Once installed, launch the application and use the File menu to load your data files.
The desktop application supports all standard Jdaviz features including:

* Loading FITS files and other supported formats
* Interactive visualization
* Plugin-based analysis tools
* Exporting results and visualizations

For detailed usage instructions, see the :ref:`quickstart` guide.

Updating
--------

To update to a newer version, simply download and install the latest release following
the same installation instructions above. Your settings and preferences will be preserved.

Troubleshooting
---------------

If you encounter issues launching or using the desktop application, please check the
`GitHub issues page <https://github.com/spacetelescope/jdaviz/issues>`_ or file a new issue
with details about your system and the problem you're experiencing.
