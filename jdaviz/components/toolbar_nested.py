import os
import ipyvuetify as v
import traitlets
import base64

from glue.config import viewer_tool
from glue.icons import icon_path
import glue.viewers.common.tool
from glue.viewers.common.tool import CheckableTool

#from jdaviz.core.registries import tool_registry

__all__ = ['NestedJupyterToolbar']

_icons = {}


def read_icon(file_name, format):
    if file_name not in _icons:
        with open(file_name, "rb") as f:
            _icons[file_name] =\
                f'data:image/{format};base64,{base64.b64encode(f.read()).decode("ascii")}'

    return _icons[file_name]


class NestedJupyterToolbar(v.VuetifyTemplate):
    template_file = (__file__, 'toolbar_nested.vue')

    active_tool = traitlets.Instance(glue.viewers.common.tool.Tool, allow_none=True,
                                     default_value=None)
    tools_data = traitlets.Dict(default_value={}).tag(sync=True)
    active_tool_id = traitlets.Any().tag(sync=True)

    # whether to show a popup menu
    show_suboptions = traitlets.Bool(False).tag(sync=True)
    # which submenu to show when show_suboptions is True
    suboptions_ind = traitlets.Int(0).tag(sync=True)
    # absolute positions to display the menu
    suboptions_x = traitlets.Float().tag(sync=True)
    suboptions_y = traitlets.Float().tag(sync=True)

    def __init__(self, viewer, tools_nested):
        self.output = viewer.output_widget
        self.tools = {}
        if viewer._default_mouse_mode_cls is not None:
            self._default_mouse_mode = viewer._default_mouse_mode_cls(viewer)
            self._default_mouse_mode.activate()
        else:
            self._default_mouse_mode = None
        super().__init__()

        for menu_ind, subtools in enumerate(tools_nested):
            for i, tool_id in enumerate(subtools):
                mode_cls = viewer_tool.members[tool_id]
                mode = mode_cls(viewer)
                self.add_tool(mode, menu_ind=menu_ind, has_suboptions=len(subtools)>1, primary=i==0)

    @traitlets.observe('active_tool_id')
    def _on_change_v_model(self, change):
        if change.new is not None:
            if isinstance(self.tools[change.new], CheckableTool):
                self.active_tool = self.tools[change.new]
            else:
                # In this case it is a non-checkable tool and we should
                # activate it but not keep the tool checked in the toolbar
                self.tools[change.new].activate()
                self.active_tool_id = None
        else:
            self.active_tool = None

    @traitlets.observe('active_tool')
    def _on_change_active_tool(self, change):
        if change.old:
            change.old.deactivate()
        else:
            if self._default_mouse_mode:
                self._default_mouse_mode.deactivate()
        if change.new:
            change.new.activate()
            self.active_tool_id = change.new.tool_id
        else:
            self.active_tool_id = None
            if self._default_mouse_mode is not None:
                self._default_mouse_mode.activate()

    def add_tool(self, tool, menu_ind, has_suboptions=True, primary=False):
        self.tools[tool.tool_id] = tool
        # TODO: we should ideally just incorporate this check into icon_path directly.
        if os.path.exists(tool.icon):
            path = tool.icon
        else:
            path = icon_path(tool.icon, icon_format='svg')
        self.tools_data = {
            **self.tools_data,
            tool.tool_id: {
                'tooltip': tool.tool_tip,
                'img': read_icon(path, 'svg+xml'),
                'menu_ind': menu_ind,
                'has_suboptions': has_suboptions,
                'primary': primary
            }
        }

    def vue_select_primary(self, args):
        menu_ind, tool_id = args
        for search_tool_id, info in self.tools_data.items():
            if info['menu_ind'] == menu_ind and info['primary']:
                prev_id = search_tool_id
                prev_info = info
                break
        else:
            raise ValueError("could not find previous selection")

        self.tools_data = {
            **self.tools_data,
            prev_id: {
                **prev_info,
                'primary': False
            },
            tool_id: {
                **self.tools_data[tool_id],
                'primary': True
            }
        }

        # and finally, set to be the active tool
        self.active_tool_id = tool_id

#tool_registry.add("j-nested-toolbar", cls=NestedJupyterToolbar)
