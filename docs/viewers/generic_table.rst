.. _viewers-generic_table:
.. rst-class:: section-icon-mdi-plus-box

*********************************
Generic Tables
*********************************


.. _viewers-generic_table-catalog:


Generic Table
=============
Generic Table viewers show data loaded with ``format = Generic Catalog``. 
In this table, the ``ID`` column is the index column, and the values are not changeable.  

.. note:: 

    Most of the functionality between Source Catalogs and Generic Catalogs viewers is identical. 
    The main difference is related to how the data is stored in the tables.


.. _viewers-generic_table-tablefeatures:

Table viewer features
======================
.. seealso::

    :ref:`Table Features <viewers-table>`
        Documentation on further details regarding the table viewer options.


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-tab", "value": "Viewer", "delay": 1500, "caption": "Select the Viewer tab"}, {"action": "select-dropdown", "value": "Viewer Type:Table", "delay": 1500, "caption": "Set viewer type to Table"}]