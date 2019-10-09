import os

from traitlets import Unicode

from .tab_area import TabArea
from ..core.template_mixin import TemplateMixin

with open(os.path.join(os.path.dirname(__file__), "content_area.vue")) as f:
        TEMPLATE = f.read()


class ContentArea(TemplateMixin):
    template = Unicode(TEMPLATE).tag(sync=True)
    source = Unicode("https://google.com").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components={'g-tab-area': TabArea(session=self.session)}
