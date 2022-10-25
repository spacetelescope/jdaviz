.. _specviz2d-export-data:

*****************************
Exporting Data From Specviz2D
*****************************

.. _specviz2d-export-data-2d:

2D Spectra
==========

Images in the 2D spectrum viewer can be exported as `specutils.Spectrum1D` objects into
the notebook:

.. code-block:: python

    specviz2d.app.get_data_from_viewer('spectrum-2d-viewer')

which returns a dictionary, with the loaded data labels as keywords and `specutils.Spectrum1D`
objects as values.  To return only a single `specutils.Spectrum1D` object, pass the data label:

.. code-block:: python

    specviz2d.app.get_data_from_viewer('spectrum-2d-viewer', 'my-data-label')


.. _specviz2d-export-data-1d:

1D Spectra
==========

Similarly, the 1D spectrum data objects can be exported into the notebook:

.. code-block:: python

    specviz2d.app.get_data_from_viewer('spectrum-viewer')

or:

.. code-block:: python

    specviz2d.app.get_data_from_viewer('spectrum-viewer', 'my-data-label')


An instance of Specviz can also be accessed, which exposes some helper methods from Specviz:

.. code-block:: python

    specviz2d.specviz.get_spectra()

.. seealso::

    :ref:`Specviz: Export Data <specviz-export-data>`
        Specviz documentation on exporting spectra.
