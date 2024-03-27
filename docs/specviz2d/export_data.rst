.. _specviz2d-export-data:

*****************************
Exporting Data From Specviz2D
*****************************

.. _specviz2d-export-data-2d:

2D Spectra
==========

Images in the 2D spectrum viewer can be exported as `specutils.Spectrum` objects into
the notebook (replace "2D data" with the label of the desired data):

.. code-block:: python

    specviz2d.get_data(data_label="2D data")

.. _specviz2d-export-data-1d:

1D Spectra
==========

Similarly, the 1D spectrum data objects can be exported into the notebook:

.. code-block:: python

    specviz2d.get_data(data_label='1D data')

An instance of Specviz can also be accessed, which exposes some helper methods from Specviz:

.. code-block:: python

    specviz2d.specviz.get_spectra()

.. seealso::

    :ref:`Specviz: Export Data <specviz-export-data>`
        Specviz documentation on exporting spectra.


Markers Table
=============

All mouseover information in the :ref:`markers plugin <markers-plugin>` can be exported to an
:ref:`astropy table <astropy:astropy-table>`
by calling :meth:`~jdaviz.core.template_mixin.TableMixin.export_table` (see :ref:`plugin-apis`).
