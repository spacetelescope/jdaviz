.. _mosviz-notebook:

***************************
Exporting data from Mosviz
***************************

.. include:: ../_templates/deprecated_config_banner.rst

Initialize an instance of the Mosviz app in a Jupyter notebook using the following code:

.. code-block:: python

    from jdaviz import Mosviz
    mosviz = Mosviz()
    # If solely using the Mosviz API, feel free to comment out the following line.
    mosviz.show()

After running the code above, you can interact with the Mosviz application from
subsequent notebook cells via the API methods attached to the
:class:`~jdaviz.configs.mosviz.helper.Mosviz` object,
for example loading data into the app as described in :ref:`mosviz-import-api`.

The :class:`~jdaviz.configs.mosviz.helper.Mosviz` helper class can be used similarly to how
:class:`~jdaviz.configs.cubeviz.helper.Cubeviz` is used in :ref:`cubeviz-notebook`.
The viewers in Mosviz that can be used that way are ``image-viewer``, ``spectrum-viewer``,
and ``spectrum-2d-viewer``.

.. seealso::

    :ref:`Cubeviz data export <cubeviz-notebook>`
        Cubeviz documentation on data exporting.

It is also possible to extract the contents of the table viewer using
`~jdaviz.configs.mosviz.helper.Mosviz.to_csv`:

.. code-block:: python

    mosviz.to_csv(filename="MOS_data.csv", selected=False)

which will save the data from the Mosviz table into the given CSV filename.
If the ``selected`` keyword is set to `True`, only the checked
rows in the table will be output. A previous CSV file of the same name can
be overwritten by setting the ``overwrite`` keyword to `True`.
The contents of ``table-viewer`` can also be extracted to a notebook cell by
running :py:meth:`~jdaviz.configs.mosviz.helper.Mosviz.to_table`:

.. code-block:: python

    mosviz.to_table()
