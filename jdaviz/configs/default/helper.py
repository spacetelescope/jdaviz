from jdaviz.core.helpers import ConfigHelper


class Freeform(ConfigHelper):
    """Freeform mode Helper class."""

    _default_configuration = "default"
    _default_spectrum_viewer_reference_name = "spectrum-viewer-1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
