from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['SubsetControl']


@tray_registry('imviz-subset-control', label="Subset Control")
class SubsetControl(TemplateMixin):
    template = load_template("subset_control.vue", __file__).tag(sync=True)

    # TODO:
    # 1. Let user select which subset to operate on.
    # 2. Hide angle field when it does not make sense (e.g., circle)
    # 3. Grab new values from user inputs
    # 4. Apply new values to Subset

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

