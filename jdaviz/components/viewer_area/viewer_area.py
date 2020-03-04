from ...core.template_mixin import TemplateMixin
from ...utils import load_template
from traitlets import Unicode

__all__ = ['ViewerArea']


class ViewerArea(TemplateMixin):
    template = load_template("viewer_area.vue", __file__).tag(sync=True)
    css = Unicode("""
    .glComponent {
    width: 100%;
    height: 100%;
    overflow: auto;
}
    .lm_item {
    width: 100%;
    height: 100%;
    overflow: auto;
}
    .lm_row {
    width: 100%;
    height: 100%;
    overflow: auto;
}
    """).tag(sync=True)
