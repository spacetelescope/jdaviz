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

It is also possible to extract data from the `table-viewer` using the following code::

    mosviz.to_csv()

Which will load the data from the `mosviz` table into a csv file and::

    mosviz.to_table()

Can be used to return the contents of the `mosviz` table into a Jupyter Notebook cell.
