from pathlib import Path
import typing as t
import threading

from traitlets import Any, Dict, Instance, default
from ipywidgets import widget_serialization
from ipyvuetify import VuetifyTemplate

from jdaviz.core.style_widget import StyleWidget


T = t.TypeVar("T")
_style_paths: t.Dict[int, Path] = {}


# this is a temporary decorator until we can depend on solara, and solara has
# an equivalent implementation.
def _singleton(factory: [t.Callable[[], T]]) -> t.Callable[[], T]:
    def _get_unique_key():
        try:
            import solara.server.kernel_context as kernel_context

            try:
                kc = kernel_context.get_current_context()
                return kc.id
            except RuntimeError:
                pass  # not running in a solara virtual kernel
        except ModuleNotFoundError:
            return "not-in-solara"

    instances: t.Dict[str, T] = {}
    lock = threading.Lock()

    def wrapper(*args, **kwargs) -> T:
        key = _get_unique_key()
        if key not in instances:
            with lock:
                if key not in instances:
                    instances[key] = factory(*args, **kwargs)
        return instances[key]

    return wrapper


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


def add(path):
    if hash(path) in _style_paths:
        return
    _style_paths[hash(path)] = path


class PopoutStyleWrapper(VuetifyTemplate):
    content = Any().tag(sync=True, **widget_serialization)
    style_registry_instance = Instance(
        StyleRegistry,
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

    @default("style_registry_instance")
    @_singleton
    def _default_style_registry_instance(self):
        return get_style_registry()


@_singleton
def get_style_registry():
    return StyleRegistry(
        style_widgets={key: StyleWidget(path) for key, path in _style_paths.items()}
    )
