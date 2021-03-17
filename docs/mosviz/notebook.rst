.. _mosviz-notebook:

***********************************
Using Mosviz in a Jupyter Notebook 
***********************************

To initialize an instance of the Mosviz app in a Jupyter notebook, simply run
the following code in a cell of the notebook::

    >>> from jdaviz import MosViz
    >>> mosviz = MosViz()
    >>> mosviz.app #doctest: +SKIP

After running the code above, you can interact with the Mosviz application from 
subsequent notebook cells via the API methods attached to the `mosviz` object,
for example loading data into the app as described in :ref:`mosviz-import-data`.

.. seealso::

    `Cubeviz data export <https://jdaviz.readthedocs.io/en/latest/cubeviz/notebook.html>`_
        Cubeviz documentation on data exporting.

The `~jdaviz.configs.mosviz.helper.MosViz` helper class can be used similarly to how
`cubeviz` is used in the previous link.
The viewers in `mosviz` that can be used that way are `image-viewer`, `spectrum-viewer`,
and `spectrum-2d-viewer`.

It is also possible to extract the contents of the table viewer via::

    mosviz.to_csv(filename="MOS_data.csv", selected=False)

Which will save the data from the `mosviz` table into a csv file named
`filename`. If the `selected` parameter is set to `True`, only the checked
rows in the table will be output. A previous csv file of the same name can
be overwritten by setting the `overwrite` parameter to `True`.
The contents of `table-viewer` can also be extracted to a notebook cell by
running the following::

    mosviz.to_table()

