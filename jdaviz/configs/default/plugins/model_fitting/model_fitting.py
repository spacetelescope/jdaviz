from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['ModelFitting']


@tray_registry('g-model-fitting')
class ModelFitting(TemplateMixin):
    template = load_template("model_fitting.vue", __file__).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
