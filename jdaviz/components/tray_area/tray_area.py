from ...core.template_mixin import TemplateMixin
from ...utils import load_template
from traitlets import Unicode

__all__ = ['TrayArea']


class TrayArea(TemplateMixin):
    template = load_template("tray_area.vue", __file__).tag(sync=True)
