.. _plugins-sonify:

************

Sonify Data

************

.. plugin-availability::

Convert data to audio for sonification analysis.

Description
===========

The Sonify Data plugin converts spectral or spatial data into audio, providing
an alternative way to explore data patterns through sound.

**Key Features:**

* Convert spectra to audio
* Map flux to pitch/volume
* Playback controls
* Export audio files

**Available in:** Cubeviz

UI Access
=========

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
