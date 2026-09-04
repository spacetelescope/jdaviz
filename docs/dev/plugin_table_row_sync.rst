Plugin State in Catalog Rows
============================

Plugins can opt specific state into catalog-row synchronization with declarations from
:mod:`jdaviz.core.table_row_sync`.  The catalog owns the generated columns, and selecting a
catalog row restores the declared plugin state.  Changing the plugin writes the current state
to the active row.

Scalar attributes
-----------------

Declare a scalar traitlet with :class:`~jdaviz.core.table_row_sync.PluginTableRowSync`::

    table_row_sync = (
        PluginTableRowSync('redshift', 'rs_redshift'),
    )

This produces ``Line Lists:redshift``.  The first name is the stable public attribute ID and
the second is the observable backing traitlet.  The default plugin hooks read and write the
traitlet directly.

Fixed selector state
--------------------

State stored behind an editable select requires a fixed selector and plugin adapter hooks::

    table_row_sync = (
        PluginTableRowSync('pa', 'pa', selectors=(('overlay', 'default'),)),
    )

This produces ``Footprints[overlay=default]:pa``.  Override
``read_table_row_sync_attribute`` and ``apply_table_row_sync_attribute`` to access the fixed
backing entry without changing the user's current selection.  When the editable-select entry is
renamed, call ``CatalogRowLinkManager.rename_plugin_selector`` so the declaration, catalog column,
metadata, and per-table synchronization state migrate to the new selector value together.  New
entries can clone the selector-scoped declaration and pass the expanded declarations to
``CatalogRowLinkManager.update_plugin_declarations``; reconciliation creates the new managed
column, visible by default, for every catalog.

Packed groups
-------------

Use :class:`~jdaviz.core.table_row_sync.PluginTableRowSyncGroup` when several settings form one
transactional recipe.  The group produces one string column containing canonical, versioned
JSON.  For example, the 2D Spectral Extraction recipe is stored in ``2D Spectral Extraction``.

Override ``read_table_row_sync_group`` to return a JSON-safe mapping and
``apply_table_row_sync_group`` to validate and apply the complete mapping.  Complex adapters
should validate before mutation, snapshot state for rollback, suppress intermediate observers,
apply settings in dependency order, and refresh once after a successful commit.

Packed values may contain strings, finite numbers, booleans, nulls, lists, and dictionaries.
NumPy scalars are normalized automatically.  Quantities and arbitrary Python objects are not
supported.

Named data references
---------------------

Use ``value_kind='data_label'`` for a value that references an entry in the Glue data
collection.  Dataset renames are propagated into scalar columns and packed JSON recipes.
Deleting a dataset clears matching references to null.  Changes to the contents of a referenced
dataset are not tracked.

Hybrid dataset selectors can declare stable manual choices::

    PluginTableRowSync('ext_dataset', 'ext_dataset_selected',
                       value_kind='data_label', manual_values=('From Plugin',))

Manual values are not changed by dataset rename or deletion.

Behavior and constraints
------------------------

Generated columns are read-only, non-renameable, and non-removable.  Their link control can
disable synchronization for an individual table viewer.  Columns for an irrelevant plugin are
hidden and synchronization pauses until the plugin becomes relevant again.  Column labels are
presentation only; synchronization uses structured metadata stored on the catalog.
