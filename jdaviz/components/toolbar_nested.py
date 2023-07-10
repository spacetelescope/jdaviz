import os
import traitlets

from glue.config import viewer_tool
from glue.core import HubListener
from glue.icons import icon_path
from glue.viewers.common.tool import CheckableTool
from glue_jupyter.common.toolbar_vuetify import BasicJupyterToolbar, read_icon

from jdaviz.core.events import (AddDataMessage, RemoveDataMessage,
                                ViewerAddedMessage, ViewerRemovedMessage,
                                SpectralMarksChangedMessage)

__all__ = ['NestedJupyterToolbar']


class NestedJupyterToolbar(BasicJupyterToolbar, HubListener):
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
        self.viewer = viewer
        self._max_menu_ind = len(tools_nested)

        # iterate through the nested list.  The first item in each entry
        # is treated as the default primary tool of that subcategory,
        # with each additional entry available from a dropdown.  For
        # backwards compatibility with BasicJupyterToolbar, single strings
        # will be treated as having no submenu.
        for menu_ind, subtools in enumerate(tools_nested):
            if isinstance(subtools, str):
                subtools = [subtools]
            for i, tool_id in enumerate(subtools):
                tool_cls = viewer_tool.members[tool_id]
                tool = tool_cls(viewer)
                self.add_tool(tool,
                              menu_ind=menu_ind,
                              has_suboptions=len(subtools) > 1,
                              primary=i == 0,
                              visible=True)

        # handle logic for tool visibilities (which will also handle setting the primary
        # to something other than the first entry, if necessary)
        self._update_tool_visibilities()

        # default_tool_priority allows falling back on an existing tool
        # if its the primary tool.  If no items in default_tool_priority
        # are currently "primary", then either no tool will be selected
        # or will fallback on BasicJupyterToolbar's handling of
        # viewer._default_mouse_mode_cls (which will not show that tool as active).
        self.default_tool_priority = default_tool_priority
        self._handle_default_tool()

        for msg in (AddDataMessage, RemoveDataMessage, ViewerAddedMessage, ViewerRemovedMessage,
                    SpectralMarksChangedMessage):
            self.viewer.hub.subscribe(self, msg,
                                      handler=lambda _: self._update_tool_visibilities())

    def _is_visible(self, tool_id):
        # tools can optionally implement self.is_visible(). If not NotImplementedError
        # the tool will always be visible
        if hasattr(self.tools[tool_id], 'is_visible'):
            return self.tools[tool_id].is_visible()
        return True

    def _update_tool_visibilities(self):
        needs_deactivate_active = False
        for menu_ind in range(self._max_menu_ind):
            has_primary = False
            n_visible = 0
            primary_id = None
            if self.active_tool_id:
                current_primary_active = self.tools_data[self.active_tool_id]['menu_ind'] == menu_ind  # noqa
            else:
                current_primary_active = False
            for tool_id, info in self.tools_data.items():
                if info['menu_ind'] != menu_ind:
                    continue
                visible = self._is_visible(tool_id)
                if visible:
                    n_visible += 1

                if tool_id == self.active_tool_id:
                    # then the primary was already set by which tool is active
                    if visible:
                        # then keep this as primary
                        primary = True
                    else:
                        # then the currently active tool is being removed, so we need to deactivate
                        # the tool and allow the default logic to be triggered
                        primary = False
                        needs_deactivate_active = True
                elif current_primary_active and self._is_visible(self.active_tool_id):
                    # then we are keeping the previous primary
                    primary = False
                else:
                    # then there is no primary already in this submenu, so the first visible
                    # entry will be selected as primary
                    primary = visible and not has_primary

                if primary:
                    primary_id = tool_id
                    has_primary = True

                self.tools_data[tool_id] = {**info,
                                            'primary': primary,
                                            'visible': visible}
            if primary_id:
                self.tools_data[primary_id] = {**self.tools_data[primary_id],
                                               'has_suboptions': n_visible > 1}

        # mutation to dictionary needs to be manually sent to update the UI
        self.send_state("tools_data")
        if needs_deactivate_active:
            self.active_tool_id = None

    def _handle_default_tool(self):
        # default to the first item in the default_tool_priority list that is currently
        # already primary
        for tool_id in self.default_tool_priority:
            if tool_id not in self.tools_data:
                continue
            if self.tools_data[tool_id]['primary'] and self.tools_data[tool_id]['visible']:
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

    def add_tool(self, tool, menu_ind, has_suboptions=True, primary=False, visible=True):
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
                'primary': primary,
                'visible': visible
            }
        }

    def vue_select_primary(self, args):
        """
        Activate the primary tool from a given menu index
        """
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

        # and finally, set to be the active tool (this triggers _on_change_v_model which in turn
        # triggers BasicJupyterToolbar._on_change_active_tool)
        self.active_tool_id = tool_id
