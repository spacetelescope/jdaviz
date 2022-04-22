import os
import traitlets

from glue.config import viewer_tool
from glue.icons import icon_path
from glue.viewers.common.tool import CheckableTool
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
    close_on_click = traitlets.Bool(False).tag(sync=True)
    # which submenu to show when show_suboptions is True
    suboptions_ind = traitlets.Int(0).tag(sync=True)
    # absolute positions to display the menu
    suboptions_x = traitlets.Float().tag(sync=True)
    suboptions_y = traitlets.Float().tag(sync=True)

    def __init__(self, viewer, tools_nested, default_tool_priority=[]):
        super().__init__(viewer)

        # iterate through the nested list.  The first item in each entry
        # is treated as the default primary tool of that subcategory,
        # with each additional entry available from a dropdown.  For
        # backwards compatibility with BasicJupyterToolbar, single strings
        # will be treated as having no submenu.
        for menu_ind, subtools in enumerate(tools_nested):
            if isinstance(subtools, str):
                subtools = [subtools]
            for i, tool_id in enumerate(subtools):
                mode_cls = viewer_tool.members[tool_id]
                mode = mode_cls(viewer)
                self.add_tool(mode,
                              menu_ind=menu_ind,
                              has_suboptions=len(subtools) > 1,
                              primary=i == 0)

        # default_tool_priority allows falling back on an existing tool
        # if its the primary tool.  If no items in default_tool_priority
        # are currently "primary", then either no tool will be selected
        # or will fallback on BasicJupyterToolbar's handling of
        # viewer._default_mouse_mode_cls (which will not show that tool as active).
        self.default_tool_priority = default_tool_priority
        self._handle_default_tool()

    def _handle_default_tool(self):
        # default to the first item in the default_tool_priority list that is currently
        # already primary
        for tool_id in self.default_tool_priority:
            if tool_id not in self.tools_data:
                continue
            if self.tools_data[tool_id]['primary']:
                self.active_tool_id = tool_id
                break

    @traitlets.observe('active_tool_id')
    def _on_change_v_model(self, event):
        super()._on_change_v_model(event)

        if event['new'] is None and event['old'] not in self.default_tool_priority:
            # then we're unchecking a non-default tool
            self._handle_default_tool()
        elif event['new'] is not None and not isinstance(self.tools[event['new']], CheckableTool):
            # then we're clicking on a non-checkable tool and want to default to the previous
            if event['old'] is not None:
                self.active_tool_id = event['old']

    def add_tool(self, tool, menu_ind, has_suboptions=True, primary=False):
        # NOTE: this method is essentially copied from glue-jupyter's BasicJupyterToolbar,
        # but we need extra values in the tools_data dictionary.  We could call super(),
        # but then that would create tools_data twice, which would then cause
        # issues/re-rerendering
        self.tools[tool.tool_id] = tool
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

        if isinstance(self.tools[tool_id], CheckableTool):
            # only switch to primary if its actually checkable, otherwise
            # just activate once
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
