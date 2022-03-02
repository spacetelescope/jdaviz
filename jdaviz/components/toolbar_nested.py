import os
import traitlets

from glue.config import viewer_tool
from glue.icons import icon_path


from glue_jupyter.common.toolbar_vuetify import BasicJupyterToolbar, read_icon

__all__ = ['NestedJupyterToolbar']


class NestedJupyterToolbar(BasicJupyterToolbar):
    template_file = (__file__, 'toolbar_nested.vue')

    # defined in BasicJupyterToolbar:
    # active_tool = traitlets.Instance
    # tools_data = traitlets.Dict
    # active_tool_id = traitlets.Any

    # whether to show a popup menu
    show_suboptions = traitlets.Bool(False).tag(sync=True)
    # which submenu to show when show_suboptions is True
    suboptions_ind = traitlets.Int(0).tag(sync=True)
    # absolute positions to display the menu
    suboptions_x = traitlets.Float().tag(sync=True)
    suboptions_y = traitlets.Float().tag(sync=True)

    def __init__(self, viewer, tools_nested):
        super().__init__(viewer)

        for menu_ind, subtools in enumerate(tools_nested):
            for i, tool_id in enumerate(subtools):
                mode_cls = viewer_tool.members[tool_id]
                mode = mode_cls(viewer)
                self.add_tool(mode, menu_ind=menu_ind, has_suboptions=len(subtools)>1, primary=i==0)

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
