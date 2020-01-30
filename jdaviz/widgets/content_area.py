import os

from traitlets import Unicode, Bool

from .tab_area import TabArea
from ..core.template_mixin import TemplateMixin

with open(os.path.join(os.path.dirname(__file__), "content_area.vue")) as f:
    TEMPLATE = f.read()


class ContentArea(TemplateMixin):
    template = Unicode(TEMPLATE).tag(sync=True)
    top_area = Bool(True).tag(sync=True)
    bottom_area = Bool(False).tag(sync=True)

    css = Unicode("""
    .container.fill-height {
        flex-wrap: wrap;
    }

    .container.fill-height > .row {
        flex: 1 1 100%;
    }
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {
            'g-tab-area-top': TabArea(area='top_area', session=self.session),
            'g-tab-area-bottom': TabArea(area='bottom_area', session=self.session)
        }
