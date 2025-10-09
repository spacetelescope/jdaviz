import pathlib
from specutils import Spectrum

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import (BaseImporterToDataCollection,
                                           _spectrum_assign_component_type)
from .roman_helpers import is_roman_asdf, load_roman_asdf_spectrum


@loader_importer_registry('roman-asdf-importer')
class RomanAsdfImporter(BaseImporterToDataCollection):
    """
    Importer for Roman ASDF 1D Spectrum files.
    """
    label = "Roman ASDF 1D Spectrum"
    resolver = "file"
    format = "roman-asdf"
    template_file = __file__, "../../../core/loaders/importers/to_dc_with_label.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        else:
            self.data_label_default = 'Roman ASDF Spectrum'

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '1D Spectrum', 'reference': 'spectrum-1d-viewer'}]

    @property
    def target(self):
        """Return the target dict for this importer."""
        # Call parent to get viewer choices, similar to BaseImporterToDataCollection
        if len(self.viewer.create_new.choices) > 0:
            return {'type': 'viewer',
                    'icon': 'mdi-window-maximize',
                    'label': self.viewer.create_new.choices[0]}
        else:
            return {}

    @property
    def is_valid(self):
        """Check if the input file is a valid Roman ASDF spectrum."""
        # Only valid for file paths (strings/Paths), not Spectrum objects
        if not isinstance(self.input, (str, pathlib.Path)):
            return False
        if not pathlib.Path(self.input).exists():
            return False
        return is_roman_asdf(str(self.input))

    @property
    def output(self):
        """Load and return the spectrum."""
        spec = load_roman_asdf_spectrum(str(self.input))
        if not isinstance(spec, Spectrum):
            raise ValueError("Roman ASDF importer did not produce a specutils.Spectrum")
        return spec

    def assign_component_type(self, comp_id, comp, units, physical_type):
        return _spectrum_assign_component_type(comp_id, comp, units, physical_type)