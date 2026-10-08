"""Native spectral-line layers: observed positions, not profile reference data.

Links are one-way so a line table cannot redefine a spectrum's coordinates.
Each reference-free viewer has its own virtual x component: upstream line
artists skip unit conversion without reference data, so these links must
already produce display units (including for the anchor table itself).
"""

from functools import partial

from glue.core.component_link import ComponentLink
from glue.viewers.common.line_layers import BaseLineLayerArtist

from jdaviz.core.unit_conversion_utils import spectral_unit_conversion


def is_spectral_line_table(data):
    return getattr(data, 'meta', {}).get('_importer') == 'SpectralLinesImporter'


def observed_wavelength_id(data):
    return next((cid for cid in data.main_components
                 if cid.label == 'observed wavelength:default'), None)


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
