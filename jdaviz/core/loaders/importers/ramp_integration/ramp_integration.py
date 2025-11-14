import numpy as np
from astropy.nddata import NDDataArray

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


__all__ = ['RampIntegrationImporter']


@loader_importer_registry('Ramp Integration')
class RampIntegrationImporter(BaseImporterToDataCollection):
    template_file = __file__, "../to_dc_with_label.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.config == 'rampviz':
            self.viewer.selected = ['integration-viewer']
            self.viewer.create_new_items = []
        else:
            self.viewer.select_default()

    @staticmethod
    def _get_supported_viewers():
        return [{'label': 'Ramp Integration', 'reference': 'rampviz-profile-viewer'}]

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'rampviz'):
            # NOTE: temporary during deconfig process
            return False

        return isinstance(self.input, (np.ndarray, NDDataArray))

    @property
    def output(self):
        """
        Returns the ramp integration data in a format that can be directly consumed by glue.

        The input is expected to be an NDDataArray with shape (1, 1, n_groups) where:
        - The first two dimensions are spatial (collapsed to 1x1)
        - The third dimension is the group/resultant axis

        This matches the format produced by ramp_extraction.py's extract() method when
        passed to add_results_from_plugin().
        """
        data = self.input

        # If input is a plain numpy array, wrap it in an NDDataArray
        if isinstance(data, np.ndarray):
            data = NDDataArray(data)

        # Ensure the data has metadata (required for glue integration)
        if not hasattr(data, 'meta') or data.meta is None:
            data.meta = {}

        return data

    def __call__(self):
        viewers = self.viewer.selected_obj
        super().__call__()
        if viewers is not None:
            for viewer in viewers:
                viewer._initialize_x_axis()

    def assign_component_type(self, comp_id, comp, units, physical_type):
        if comp_id == 'data':
            physical_type = 'ramp_integration'
        elif comp_id == 'Pixel Axis 2 [x]':
            physical_type = 'ramp_integration_group'
        return super().assign_component_type(comp_id, comp, units, physical_type)
