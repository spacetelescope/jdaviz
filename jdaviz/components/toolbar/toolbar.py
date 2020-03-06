from ...core.template_mixin import TemplateMixin
from ...utils import load_template
from traitlets import Unicode

__all__ = ['Toolbar']


class Toolbar(TemplateMixin):
    template = load_template("toolbar.vue", __file__).tag(sync=True)
