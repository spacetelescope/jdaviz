.. _mosviz-notebook:

***********************************
Using Mosviz in a Jupyter Notebook 
***********************************

To initialize an instance of the Mosviz app in a Jupyter notebook, simply run
the following code in a cell of the notebook::

    >>> from jdaviz import Mosviz
    >>> mosviz = Mosviz()
    >>> mosviz.app  # doctest: +SKIP

After running the code above, you can interact with the Mosviz application from 
subsequent notebook cells via the API methods attached to the
`~jdaviz.configs.mosviz.helper.Mosviz` object,
for example loading data into the app as described in :ref:`mosviz-import-data`.

.. seealso::

    :ref:`Cubeviz data export <cubeviz-notebook>`
        Cubeviz documentation on data exporting.

The `~jdaviz.configs.mosviz.helper.Mosviz` helper class can be used similarly to how
`~jdaviz.configs.cubeviz.helper.Cubeviz` is used in :ref:`cubeviz-notebook`.
The viewers in Mosviz that can be used that way are ``image-viewer``, ``spectrum-viewer``,
and ``spectrum-2d-viewer``.

It is also possible to extract the contents of the table viewer using
`~jdaviz.configs.mosviz.helper.Mosviz.to_csv`::

    mosviz.to_csv(filename="MOS_data.csv", selected=False)

Which will save the data from the Mosviz table into the given CSV filename.
If the ``selected`` keyword is set to `True`, only the checked
rows in the table will be output. A previous CSV file of the same name can
be overwritten by setting the ``overwrite`` keyword to `True`.
The contents of ``table-viewer`` can also be extracted to a notebook cell by
running `~jdaviz.configs.mosviz.helper.Mosviz.to_table`::

    mosviz.to_table()
