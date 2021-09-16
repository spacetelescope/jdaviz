#################
Jupyter Notebooks
#################

Jdaviz is designed to be integrated into existing `Jupyter notebooks <https://jupyter.org/>`_! To do so, install Jdaviz in your notebook's Python environment and add a new cell wherever you would like to use Jdaviz.  For example::

    # Import Specviz
    from jdaviz import Specviz
    # Instantiate an instance of Specviz
    myviz = Specviz()
    # Display Specviz
    myviz.app   #doctest: +SKIP

Similarly, you can open instances of :ref:`mosviz-notebook`, :ref:`cubeviz-notebook`, and :ref:`imviz-notebook`.

Using Jdaviz in a Jupyter Notebook
----------------------------------

.. toctree::
  :maxdepth: 2

  import_data
  export_data
  save_state