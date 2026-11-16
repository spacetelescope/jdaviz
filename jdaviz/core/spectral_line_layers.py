"""Native spectral-line layers: observed positions, not profile reference data.

Links are one-way so a line table cannot redefine a spectrum's coordinates.
Each reference-free viewer has its own virtual x component: upstream line
artists skip unit conversion without reference data, so these links must
already produce display units (including for the anchor table itself).
"""

from functools import partial

import numpy as np
from glue.core import Data
from glue.core.component import Component
from glue.core.component_link import ComponentLink
from glue.viewers.common.line_layers import BaseLineLayerArtist

from jdaviz.core.unit_conversion_utils import spectral_unit_conversion


def is_spectral_line_table(data):
    return getattr(data, 'meta', {}).get('_importer') in (
        'SpectralLinesImporter', 'SpectralLinesComponent')


def observed_wavelength_id(data):
    label = data.meta.get('_spectral_line_column', 'observed wavelength:default')
    return next((cid for cid in data.main_components
                 if cid.label == label), None)


def component_datasets(source):
    """Auxiliary plotting datasets, keyed by the original column's identity."""
    return getattr(source, '_spectral_line_component_data', {})


def sync_spectral_line_components(app, source, create=False):
    """Give additional observed columns their own native Glue layer identity.

    A linked x component has only one meaning within a Data object (including
    its subsets). Extra components therefore need separate Data contexts, not
    duplicate artists/subsets of the original table. The original table remains
    the default layer; these small plotting datasets mirror the other columns.
    """
    if source.meta.get('_importer') != 'SpectralLinesImporter':
        return
    if not create and not hasattr(source, '_spectral_line_component_data'):
        return
    if getattr(source, '_syncing_spectral_line_components', False):
        return
    source._syncing_spectral_line_components = True
    try:
        projections = component_datasets(source)
        source._spectral_line_component_data = projections
        columns = [cid for cid in source.main_components
                   if cid.label in source.meta.get('_jdaviz_plugin_component_column', [])]
        primary = observed_wavelength_id(source)
        if primary not in columns and columns:
            primary = columns[0]
            source.meta['_spectral_line_column'] = primary.label
        for cid, data in list(projections.items()):
            if cid not in columns or cid is primary:
                if data in app.data_collection:
                    app.data_item_remove(data.label)
                del projections[cid]
        for cid in columns:
            if cid is primary:
                continue
            units = source.get_component(cid).units
            if cid in projections and projections[cid] in app.data_collection:
                data = projections[cid]
                target = observed_wavelength_id(data)
                values = source[cid]
                if not np.array_equal(data[target], values, equal_nan=True):
                    data.update_components({target: values})
                continue
            component = cid.label.partition('observed wavelength:')[2]
            data = Data(label=app.return_unique_name(f'{source.label} [{component}]'))
            data.meta.update(_importer='SpectralLinesComponent',
                             _spectral_line_source=source.uuid,
                             _spectral_line_column=cid.label,
                             _spectral_line_component=component)
            data.add_component(Component(np.array(source[cid], copy=True), units=units),
                               cid.label)
            projections[cid] = data
            app.add_data(data, notify_done=False)
            # Only newly-created components are automatically added. Redshift
            # changes must not re-add a component explicitly removed by a user.
            for viewer in list(app._viewer_store.values()):
                if (hasattr(viewer, '_sync_spectral_line_links')
                        and any(artist.layer is source for artist in viewer.layers)):
                    app.add_data_to_viewer(viewer.reference, data.label)
        if not columns:
            for viewer in list(app._viewer_store.values()):
                if any(artist.layer is source for artist in viewer.layers):
                    app.remove_data_from_viewer(viewer.reference, source.label)
    finally:
        source._syncing_spectral_line_components = False


def rename_spectral_line_component(app, old_label, new_label):
    """Rename plotting datasets in place, preserving artists and styles."""
    old_col, new_col = (f'observed wavelength:{label}' for label in (old_label, new_label))
    for source in list(app.data_collection):
        if source.meta.get('_importer') != 'SpectralLinesImporter':
            continue
        if source.meta.get('_spectral_line_column', 'observed wavelength:default') == old_col:
            source.meta['_spectral_line_column'] = new_col
        for cid, data in component_datasets(source).items():
            if cid.label != old_col or data not in app.data_collection:
                continue
            target = observed_wavelength_id(data)
            data.meta['_spectral_line_column'] = new_col
            data.meta['_spectral_line_component'] = new_label
            target.label = new_col
            label = app.return_unique_name(f'{source.label} [{new_label}]')
            app.rename_data(data.label, label)


def line_tables(state):
    return [data for data in state.layers_data if is_spectral_line_table(data)]


def line_positions(data, display_unit):
    cid = observed_wavelength_id(data)
    if cid is None:
        return []
    native_unit = data.get_component(cid).units
    return spectral_unit_conversion(data[cid], native_unit, display_unit or native_unit)


def sync_spectral_line_links(viewer, *args):
    """Replace only this viewer's links when its axis, units or layers change."""
    if getattr(viewer, '_syncing_spectral_line_links', False):
        return
    state = viewer.state
    target = state.x_att
    reference = state.reference_data
    # Reference changes briefly leave the old x component selected.
    if reference is not None and target not in reference.components:
        return
    target_unit = (reference.get_component(target).units if reference is not None
                   and target is not None else state.x_display_unit)
    specifications = []
    if target is not None:
        for data in line_tables(state):
            source = observed_wavelength_id(data)
            if source is not None:
                specifications.append((source, data.get_component(source).units,
                                       target, target_unit))
    if specifications == getattr(viewer, '_spectral_line_link_specs', []):
        return

    viewer._syncing_spectral_line_links = True
    try:
        collection = viewer.session.data_collection
        links = [ComponentLink([source], target,
                               using=partial(spectral_unit_conversion,
                                             original_units=source_unit,
                                             target_units=target_unit or source_unit))
                 for source, source_unit, target, target_unit in specifications]
        with collection.delay_link_manager_update():
            for link in getattr(viewer, '_spectral_line_links', []):
                if link in collection.external_links:
                    collection.remove_link(link)
            collection.add_link(links)
        viewer._spectral_line_links = links
        viewer._spectral_line_link_specs = specifications
        # A replacement transform can retain the same derived ComponentID,
        # so explicitly refresh native artists even if Glue emits no CID change.
        for artist in viewer.layers:
            if isinstance(artist, BaseLineLayerArtist) and getattr(artist, 'line_mark', None):
                artist.update()
    finally:
        viewer._syncing_spectral_line_links = False
