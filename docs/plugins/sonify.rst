.. _plugins-sonify:
.. rst-class:: section-icon-mdi-tune-variant

***********
Sonify Data
***********

.. plugin-availability::

Convert data to audio for sonification analysis.

Description
===========

The Sonify Data plugin converts spectral or spatial data into audio, providing
an alternative way to explore data patterns through sound.

The plugin requires the `Strauss <https://strauss.readthedocs.io/en/latest/>`_ package to
turn data cubes into audio grids. The audio produced by this sonification
(via the :guilabel:`Sonify Data` button) can be played by hovering the mouse over the
:ref:`viewers-spectrum_3d` viewer. A range of the cube can be sonified by applying a spectral
subset to the data before sonifying. The output device for sound can be changed by using
the :guilabel:`Sound device` dropdown.

Once sonified, the resulting layers can be adjusted in the Plot Options plugin
so that multiple sonified layers can be adjusted like a mixing board.

**Key Features:**

* Convert spectra to audio
* Map flux to pitch/volume
* Playback controls
* Export audio files

.. note::

    For mac m-series users, the ``Strauss`` library requires the
    `sounddevice <https://python-sounddevice.readthedocs.io/en/latest/>`_ and
    `PortAudio <https://www.portaudio.com>`_ libraries. In order to avoid errors with the sonification
    process, ``sounddevice`` and ``PortAudio`` must be installed as follows (these steps can be followed
    either before or after installing Strauss itself):

    1. Download the latest/stable ``PortAudio`` release from
       `PortAudio's website <https://files.portaudio.com/download.html>`_.
    2. Unpack the tarball and ``cd`` into the ``portaudio`` directory.
    3. Following the `'debug' build instructions <https://files.portaudio.com/docs/v19-doxydocs/compile_mac_coreaudio.html>`_,
       run ``./configure --enable-mac-debug && make && sudo make install``. This will place a
       "libportaudio.dylib" in the directory "usr/local/lib/" which ``sounddevice`` will link to.
    4. Install ``sounddevice`` via ``pip`` (*not* ``conda`` as ``conda`` will attempt to install
       and link to it's own portaudio).
    5. Install ``Strauss`` if not already done and proceed with the sonification.

UI Access
=========

.. wireframe-demo::
   :demo: plugins,plugins@1000:open-panel
   :enable-only: plugins
   :plugin-name: Sonify Data
   :plugin-panel-opened: false
   :demo-repeat: false

Click the :guilabel:`Sonify` icon in the plugin toolbar to:

1. Select data to sonify
2. Configure audio mapping
3. Play/pause audio
4. Export audio file

API Access
==========

.. code-block:: python

    plg = cubeviz.plugins['Sonify']
    # Configure and generate audio

.. plugin-api-refs::
   :module: jdaviz.configs.cubeviz.plugins.sonify_data.sonify_data
   :class: SonifyData

See Also
========

* :ref:`cubeviz-sonify-data` - Sonification documentation
