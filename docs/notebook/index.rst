#################
Jupyter Notebooks
#################

Jdaviz is designed to be integrated into existing
`Jupyter notebooks <https://jupyter.org/>`_! To do so,
install Jdaviz in your notebook's Python environment and
add a new cell wherever you would like to use Jdaviz.
For example::

    # Import Specviz
    from jdaviz import Specviz
    # Instantiate an instance of Specviz
    myviz = Specviz()
    # Display Specviz
    myviz.show()   #doctest: +SKIP

For more information on using Specviz in a notebook, see
:ref:`specviz-notebook`.
Similarly, you can open instances of :ref:`cubeviz-notebook` and :ref:`mosviz-notebook`.

Using Jdaviz in a Jupyter Notebook
----------------------------------

.. toctree::
  :maxdepth: 2

  display
  import_data
  export_data
  save_state
