from traitlets import Any, Dict, Instance, default
from ipywidgets import widget_serialization
from ipyvuetify import VuetifyTemplate

from jdaviz.core.style_widget import StyleWidget


class StyleRegistry(VuetifyTemplate):
    style_widgets = Dict(default_value={}).tag(sync=True, **widget_serialization)

    @default("template")
    def _template(self):
        return """
        <template>
            <span>
                <jupyter-widget v-for="style_widget in style_widgets" :widget="style_widget">
                </jupyter-widget>
            </span>
        </template>
        """

    def add(self, path):
        if hash(path) in self.style_widgets:
            return
        self.style_widgets = {**self.style_widgets, hash(path): StyleWidget(path)}


instance = StyleRegistry()


class PopoutStyleWrapper(VuetifyTemplate):
    content = Any().tag(sync=True, **widget_serialization)
    style_registry_instance = Instance(
        StyleRegistry,
        default_value=instance
    ).tag(sync=True, **widget_serialization)

    @default("template")
    def _template(self):
        return """
        <template>
            <div>
                <jupyter-widget :widget="style_registry_instance"></jupyter-widget>
                <jupyter-widget :widget="content"></jupyter-widget>
            </div>
        </template>
        """
