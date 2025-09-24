<template>
  <v-app id="web-app" :style="checkNotebookContext() ? 'display: inline' : 'display: flex'" :class="'jdaviz ' + config" ref="mainapp">
    <jupyter-widget :widget="style_registry_instance"></jupyter-widget>
    <div style="overflow: hidden; width: 0px; height: 0px">
      <jupyter-widget :widget="widget" v-for="widget in invisible_children" :key="widget"></jupyter-widget>
    </div>
    <v-app-bar color="toolbar" dark :dense="state.settings.dense_toolbar" flat app absolute clipped-right :style="checkNotebookContext() ? 'margin-left: 1px; margin-right: 1px' : ''">

      <v-toolbar-items v-if="config === 'deconfigged'">
        <j-tooltip v-if="(!state.settings.server_is_remote || state.settings.remote_enable_importers)" tipid="app-toolbar-loaders">
          <v-btn icon @click="() => {if (state.drawer_content === 'loaders') {state.drawer_content = ''} else {state.drawer_content = 'loaders'}}" :class="{active : state.drawer_content === 'loaders'}">
            <v-icon medium style="padding-top: 2px">mdi-plus-box</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip tipid="app-toolbar-save">
          <v-btn icon @click="() => {if (state.drawer_content === 'save') {state.drawer_content = ''} else {state.drawer_content = 'save'}}" :class="{active : state.drawer_content === 'save'}" :disabled="!state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Export')].is_relevant">
            <v-icon medium style="padding-top: 2px">mdi-content-save</v-icon>
          </v-btn>
        </j-tooltip>

        <v-divider vertical style="margin: 0px 10px"></v-divider>

        <j-tooltip tipid="app-toolbar-settings">
          <v-btn icon @click="() => {if (state.drawer_content === 'settings') {state.drawer_content = ''} else {state.drawer_content = 'settings'}}" :class="{active : state.drawer_content === 'settings'}" :disabled="!state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Plot Options')].is_relevant">
            <v-icon medium style="padding-top: 2px">mdi-cog</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip tipid="app-toolbar-info">
          <v-btn icon @click="() => {if (state.drawer_content === 'info') {state.drawer_content = ''} else {state.drawer_content = 'info'}}" :class="{active : state.drawer_content === 'info'}" :disabled="!state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Metadata')].is_relevant">
            <v-icon medium style="padding-top: 2px">mdi-information-outline</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip tipid="app-toolbar-plugins">
          <v-btn icon @click="() => {if (state.drawer_content === 'plugins') {state.drawer_content = ''} else {state.drawer_content = 'plugins'}}" :class="{active : state.drawer_content === 'plugins'}" :disabled="state.tray_items.filter(ti => {return (ti.is_relevant && ti.sidebar === 'plugins')}).length === 0">
            <v-icon>mdi-tune-variant</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip tipid="app-toolbar-subsets">
          <v-btn icon @click="() => {if (state.drawer_content === 'subsets') {state.drawer_content = ''} else {state.drawer_content = 'subsets'}}" :class="{active : state.drawer_content === 'subsets'}" :disabled="!state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Plot Options')].is_relevant">
            <v-icon>
              {{ state.subset_mode_create ? 'mdi-selection-drag' : 'mdi-selection' }}
            </v-icon>
          </v-btn>
        </j-tooltip>

        <v-divider vertical style="margin: 0px 10px"></v-divider>
      </v-toolbar-items>

      <v-toolbar-items v-for="(item, index) in state.tool_items">
        <!-- this logic assumes the first entry is g-data-tools, if that changes, this may need to be modified -->
        <v-divider v-if="config !== 'deconfigged' && index > 1" vertical style="margin: 0px 10px"></v-divider>
        <j-tooltip v-if="item.name === 'g-data-tools' && ['cubeviz', 'mosviz', 'rampviz'].indexOf(config) === -1" tooltipcontent="Open data menu in sidebar (this button will be removed in a future release)">
          <v-btn tile depressed color="turquoise" @click="state.drawer_content = 'loaders'">
            Import Data
          </v-btn>
        </j-tooltip>
        <j-tooltip v-else-if="['cubeviz', 'mosviz'].indexOf(config) !== -1 && item.name == 'g-data-tools' && state.data_items.length !== 0"></j-tooltip>
        <j-tooltip v-else :tipid="item.name">
          <jupyter-widget :widget="item.widget" :key="item.name"></jupyter-widget>
        </j-tooltip>
        <v-divider v-if="config !== 'deconfigged' && item.name === 'g-data-tools'" vertical style="margin: 0px 10px; border-width: 0"></v-divider>
      </v-toolbar-items>

      <v-spacer></v-spacer>
      <v-toolbar-items v-if="config !== 'deconfigged'">
        <j-tooltip tipid="app-toolbar-popout" span_style="scale: 0.8; margin-left: -4px; margin-right: -4px">
          <jupyter-widget :widget="popout_button" ></jupyter-widget>
        </j-tooltip>
        <j-tooltip v-if="state.show_toolbar_buttons" tipid="app-help">
          <v-btn icon :href="docs_link" target="_blank">
            <v-icon medium>mdi-help-box</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip v-if="state.show_toolbar_buttons && checkNotebookContext()" tipid="app-api-hints">
          <v-btn icon @click="state.show_api_hints = !state.show_api_hints" :class="{active : state.show_api_hints}">
            <img :src="state.icons['api']" width="24" class="invert-if-dark" style="opacity: 1.0"/>
          </v-btn>
        </j-tooltip>
        <v-divider v-if="state.show_toolbar_buttons" vertical style="margin: 0px 10px"></v-divider>
        <j-tooltip v-if="(state.dev_loaders || ['cubeviz', 'mosviz', 'rampviz'].indexOf(config) === -1) && (state.show_toolbar_buttons || state.drawer_content === 'loaders') && state.loader_items.length > 0 && (!state.settings.server_is_remote || state.settings.remote_enable_importers)" tipid="app-toolbar-loaders">
          <v-btn icon @click="() => {if (state.drawer_content === 'loaders') {state.drawer_content = ''} else {state.drawer_content = 'loaders'}}" :class="{active : state.drawer_content === 'loaders'}">
            <v-icon medium style="padding-top: 2px">mdi-plus-box</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip v-if="state.show_toolbar_buttons || state.drawer_content === 'logger'" tipid="app-toolbar-logger-configged">
          <v-btn icon @click="() => {if (state.drawer_content === 'logger') {state.drawer_content = ''} else {state.drawer_content = 'logger'}}" :class="{active : state.drawer_content === 'logger'}">
            <v-icon medium style="padding-top: 2px">mdi-message-reply-text</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip v-if="state.show_toolbar_buttons || state.drawer_content === 'plugins'" tipid="app-toolbar-plugins-configged">
          <v-btn icon @click="() => {if (state.drawer_content === 'plugins') {state.drawer_content = ''} else {state.drawer_content = 'plugins'}}" :class="{active : state.drawer_content === 'plugins'}">
            <v-icon>mdi-menu</v-icon>
          </v-btn>
        </j-tooltip>
      </v-toolbar-items>

      <v-toolbar-items v-if="config === 'deconfigged'">
        <v-layout column  class="app-bar-right" style="height: 28px; padding-bottom: 12px; margin-top: 2px" v-if="state.show_toolbar_buttons || state.global_search_menu || state.about_popup">
          <span style="align-items: right; display: inline-flex; margin-right: 2px">
            <v-menu
              offset-y
              style="max-width: 600px"
            >
              <template v-slot:activator="{ on, attrs }">
                <v-text-field
                    v-model='state.global_search'
                    append-icon='mdi-magnify'
                    style="width: 200px; margin-right: 8px; margin-top: 2px"
                    dense
                    clearable
                    hide-details
                    single-line
                    v-bind="attrs"
                    v-on="on"
                ></v-text-field>
              </template>
              <v-card style="min-width: 350px; max-height: 500px; overflow-y: scroll">
                <v-container>
                  <div v-for="ldrItem in state.loader_items" :key="ldrItem.label">
                    <v-row v-if="trayItemVisible(ldrItem, state.global_search)">
                      <v-list-item style="display: grid; min-height: 6px; cursor: pointer" @click="(e) => {search_item_clicked({attr: 'loaders', label: ldrItem.label})}">
                        <v-list-item-title>
                          Loader: {{ ldrItem.label }}
                        </v-list-item-title>
                        <v-list-item-subtitle v-if="state.show_api_hints" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint">ldr = {{  api_hints_obj || config }}.loaders['{{ ldrItem.label }}']</span>
                        </v-list-item-subtitle>
                        <v-list-item-subtitle v-if="state.show_api_hints && state.global_search.length" v-for="api_method in trayItemMethodMatch(ldrItem, state.global_search)" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint">ldr.{{ api_method }}</span>
                        </v-list-item-subtitle>
                      </v-list-item>
                    </v-row>
                  </div>
                  <div v-for="vcItem in state.new_viewer_items" :key="vcItem.label">
                    <v-row v-if="vcItem.is_relevant && trayItemVisible(vcItem, state.global_search)">
                      <v-list-item style="display: grid; min-height: 6px; cursor: pointer" @click="(e) => {search_item_clicked({attr: 'new_viewers', label: vcItem.label})}">
                        <v-list-item-title>
                          New Viewer: {{ vcItem.label }}
                        </v-list-item-title>
                        <v-list-item-subtitle v-if="state.show_api_hints" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint">vc = {{  api_hints_obj || config }}.new_viewers['{{ vcItem.label }}']</span>
                        </v-list-item-subtitle>
                        <v-list-item-subtitle v-if="state.show_api_hints && state.global_search.length" v-for="api_method in trayItemMethodMatch(vcItem, state.global_search)" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint">vc.{{ api_method }}</span>
                        </v-list-item-subtitle>
                      </v-list-item>
                    </v-row>
                  </div>
                  <div v-for="dmItem in state.viewer_items" :key="dmItem.name">
                    <v-row v-if="trayItemVisible(dmItem, state.global_search)">
                      <v-list-item style="display: grid; min-height: 6px; cursor: pointer" @click="(e) => {search_item_clicked({attr: 'data_menus', label: dmItem.name})}">
                        <v-list-item-title>
                          Data Menu: {{ dmItem.name }}
                        </v-list-item-title>
                        <v-list-item-subtitle v-if="state.show_api_hints" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint">dm = {{  api_hints_obj || config }}.viewers['{{ dmItem.name }}'].data_menu</span>
                        </v-list-item-subtitle>
                        <v-list-item-subtitle v-if="state.show_api_hints && state.global_search.length" v-for="api_method in trayItemMethodMatch(dmItem, state.global_search)" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint">dm.{{ api_method }}</span>
                        </v-list-item-subtitle>
                      </v-list-item>
                    </v-row>
                  </div>
                  <div v-for="(trayItem, index) in state.tray_items" :key="index">
                    <v-row v-if="trayItem.is_relevant && trayItemVisible(trayItem, state.global_search)">
                      <v-list-item style="display: grid; min-height: 6px; cursor: pointer" @click="(e) => {search_item_clicked({attr: 'plugins', label: trayItem.label})}">
                        <v-list-item-title>
                          {{ trayItem.label }}
                        </v-list-item-title>
                        <v-list-item-subtitle v-if="state.show_api_hints" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint">plg = {{  api_hints_obj || config }}.plugins['{{ trayItem.label }}']</span>
                        </v-list-item-subtitle>
                        <v-list-item-subtitle v-if="state.show_api_hints && state.global_search.length" v-for="api_method in trayItemMethodMatch(trayItem, state.global_search)" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint">plg.{{ api_method }}</span>
                        </v-list-item-subtitle>
                        <v-list-item-subtitle style="white-space: normal; font-size: 8pt">
                          {{ trayItem.tray_item_description }}
                        </v-list-item-subtitle>
                      </v-list-item>
                    </v-row>
                  </div>
                </v-container>
              </v-card>
            </v-menu>
          </span>

          <span style="display: inline-flex; align-items: center; margin-top: 4px;">
            <v-spacer></v-spacer>

            <j-about-menu
              :jdaviz_version="state.jdaviz_version"
              :api_hints_obj="api_hints_obj"
              :api_hints_enabled="state.show_api_hints"
              :about_widget="state.tray_items[state.tray_items.map(ti => ti.label).indexOf('About')].widget"
              :force_open_about.sync="force_open_about"
            ></j-about-menu>

            <j-tooltip v-if="state.show_toolbar_buttons && checkNotebookContext()" tipid="app-api-hints">
              <v-btn small icon @click="state.show_api_hints = !state.show_api_hints" :class="{active : state.show_api_hints}">
                <img :src="state.icons['api']" width="24" class="color-to-white" style="opacity: 1.0; padding-top: 2px; padding-bottom: 2px"/>
              </v-btn>
            </j-tooltip>
            <j-tooltip tipid="app-toolbar-popout" span_style="scale: 0.8; margin-left: -4px; margin-right: -4px">
              <jupyter-widget :widget="popout_button" ></jupyter-widget>
            </j-tooltip>
          </span>
        </v-layout>
      </v-toolbar-items>
    </v-app-bar>

    <v-content
      :style="checkNotebookContext() ? 'height: ' + state.settings.context.notebook.max_height + '; border: solid 1px #e5e5e5; border-top: 0px' : ''"
      :class="checkNotebookContext() ? '' : 'jdaviz__content--not-in-notebook'"
    >
      <v-container class="fill-height pa-0" fluid>
        <splitpanes>
          <pane size="25" min-size="25" v-if="config === 'deconfigged' && state.drawer_content.length > 0" style="background-color: #fafbfc; border-top: 6px solid #C75109; min-width: 320px">
            <v-card v-if="state.drawer_content === 'loaders'" flat tile class="fill-height" style="overflow-x: hidden; overflow-y: hidden" color="gray">
              <v-tabs fixed-tabs dark background-color="viewer_toolbar" v-model="state.add_subtab">
                <v-tab>Data</v-tab>
                <v-tab>Viewer</v-tab>
              </v-tabs>
              <v-tabs-items v-model="state.add_subtab" style="overflow-y: auto">
                <v-tab-item style="padding-bottom: 40px">
                  <j-loader-panel
                    :loader_items="state.loader_items"
                    :loader_selected.sync="state.loader_selected"
                    :api_hints_enabled="state.show_api_hints"
                    :api_hints_obj="api_hints_obj || config"
                    :server_is_remote="state.settings.server_is_remote"
                  ></j-loader-panel>
                </v-tab-item>
                <v-tab-item style="padding-bottom: 40px">
                  <j-new-viewer-panel
                    :new_viewer_items="state.new_viewer_items"
                    :new_viewer_selected.sync="state.new_viewer_selected"
                    :api_hints_enabled="state.show_api_hints"
                    :api_hints_obj="api_hints_obj || config"
                  ></j-new-viewer-panel>
                </v-tab-item>
              </v-tabs-items>
            </v-card>
            <v-card v-if="state.drawer_content === 'save'" flat tile class="overflow-y-auto fill-height" style="overflow-x: hidden" color="gray">
              <span v-if="state.show_api_hints" class="api-hint" style="font-weight: bold">plg = {{  api_hints_obj || config }}.plugins['Export']</span>
              <jupyter-widget :widget="state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Export')].widget"></jupyter-widget>
            </v-card>
            <v-card v-if="state.drawer_content === 'plugins'" flat tile class="overflow-y-auto fill-height" style="overflow-x: hidden" color="gray">
              <v-text-field
                v-model='state.tray_items_filter'
                append-icon='mdi-magnify'
                style="padding: 0px 8px"
                clearable
                hide-details
              ></v-text-field>
              <v-expansion-panels accordion multiple focusable flat tile v-model="state.tray_items_open">
                <v-expansion-panel v-for="(trayItem, index) in state.tray_items" :key="index">
                  <div v-if="trayItem.is_relevant && trayItemVisible(trayItem, state.tray_items_filter) && (trayItem.sidebar === 'plugins' || config !== 'deconfigged')">
                    <v-expansion-panel-header class="plugin-header">
                      <v-list-item style="display: grid; min-height: 6px" class="plugin-title">
                        <v-list-item-title>
                          <j-tooltip :tipid="trayItem.name">
                            {{ trayItem.label }}
                          </j-tooltip>
                        </v-list-item-title>
                        <v-list-item-subtitle v-if="state.show_api_hints" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint" :style="state.tray_items_open.includes(index) ? 'font-weight: bold' : null">plg = {{  api_hints_obj || config }}.plugins['{{ trayItem.label }}']</span>
                        </v-list-item-subtitle>
                        <v-list-item-subtitle v-if="state.show_api_hints && state.tray_items_filter.length" v-for="api_method in trayItemMethodMatch(trayItem, state.tray_items_filter)" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint">plg.{{ api_method }}</span>
                        </v-list-item-subtitle>
                        <v-list-item-subtitle style="white-space: normal; font-size: 8pt">
                          {{ trayItem.tray_item_description }}
                        </v-list-item-subtitle>
                      </v-list-item>
                    </v-expansion-panel-header>
                    <v-expansion-panel-content style="margin-left: -12px; margin-right: -12px;">
                      <jupyter-widget v-if="state.tray_items_open.includes(index)" :widget="trayItem.widget"></jupyter-widget>
                    </v-expansion-panel-content>
                  </div>
                </v-expansion-panel>
              </v-expansion-panels>
              <v-divider></v-divider>
            </v-card>
            <v-card v-if="state.drawer_content === 'info'" flat tile class="fill-height" style="overflow-x: hidden; overflow-y: hidden" color="gray">
              <v-tabs fixed-tabs dark background-color="viewer_toolbar" v-model="state.info_subtab">
                <v-tab>Metadata</v-tab>
                <v-tab>Markers</v-tab>
                <v-tab>Logger</v-tab>
              </v-tabs>
              <v-tabs-items v-model="state.info_subtab" style="overflow-y: auto">
                <v-tab-item style="padding-bottom: 40px">
                  <span v-if="state.show_api_hints" class="api-hint" style="font-weight: bold">plg = {{  api_hints_obj || config }}.plugins['Metadata']</span>
                  <jupyter-widget :widget="state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Metadata')].widget"></jupyter-widget>
                </v-tab-item>
                <v-tab-item style="padding-bottom: 40px">
                  <span v-if="state.show_api_hints" class="api-hint" style="font-weight: bold">plg = {{  api_hints_obj || config }}.plugins['Markers']</span>
                  <jupyter-widget :widget="state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Markers')].widget"></jupyter-widget>
                </v-tab-item>
                <v-tab-item style="padding-bottom: 40px">
                  <span v-if="state.show_api_hints" class="api-hint" style="font-weight: bold">plg = {{  api_hints_obj || config }}.plugins['Logger']</span>
                  <jupyter-widget :widget="state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Logger')].widget"></jupyter-widget>
                </v-tab-item>
              </v-tabs-items>
            </v-card>
            <v-card v-if="state.drawer_content === 'subsets'" flat tile class="overflow-y-auto fill-height" style="overflow-x: hidden" color="gray">
              <span v-if="state.show_api_hints" class="api-hint" style="font-weight: bold">plg = {{  api_hints_obj || config }}.plugins['Subset Tools']</span>
              <jupyter-widget :widget="state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Subset Tools')].widget"></jupyter-widget>
            </v-card>
            <v-card v-if="state.drawer_content === 'settings'" flat tile class="fill-height" style="overflow-x: hidden; overflow-y: hidden" color="gray">
              <v-tabs fixed-tabs dark background-color="viewer_toolbar" v-model="state.settings_subtab">
                <v-tab :disabled="!state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Plot Options')].is_relevant">Plot Options</v-tab>
                <v-tab>Units</v-tab>
              </v-tabs>
              <v-tabs-items v-model="state.settings_subtab" style="overflow-y: auto">
                <v-tab-item style="padding-bottom: 40px">
                  <span v-if="state.show_api_hints" class="api-hint" style="font-weight: bold">plg = {{  api_hints_obj || config }}.plugins['Plot Options']</span>
                  <jupyter-widget :widget="state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Plot Options')].widget"></jupyter-widget>
                </v-tab-item>
                <v-tab-item style="padding-bottom: 40px">
                  <span v-if="state.show_api_hints" class="api-hint" style="font-weight: bold">plg = {{  api_hints_obj || config }}.plugins['Unit Conversion']</span>
                  <jupyter-widget :widget="state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Unit Conversion')].widget"></jupyter-widget>
                </v-tab-item>
              </v-tabs-items>
            </v-card>

          </pane>

          <pane size="75" min-size='25'>
            <golden-layout
              v-if="outputCellHasHeight && showGoldenLayout"
              style="height: 100%;"
              :has-headers="state.settings.visible.tab_headers"
              @state="onLayoutChange"
              :state="golden_layout_state"
            >
              <gl-row :closable="false">
                <g-viewer-tab
                  v-for="(stack, index) in state.stack_items"
                  :stack="stack"
                  :key="stack.viewers.map(v => v.id).join('-') + stack.children.map(v => v.id).join('-')"
                  :data_items="state.data_items"
                  :app_settings="state.settings"
                  :config="config"
                  :icons="state.icons"
                  :viewer_icons="state.viewer_icons"
                  :layer_icons="state.layer_icons"
                  :closefn="destroy_viewer_item"
                  @data-item-visibility="data_item_visibility($event)"
                  @data-item-unload="data_item_unload($event)"
                  @data-item-remove="data_item_remove($event)"
                  @call-viewer-method="call_viewer_method($event)"
                  @change-reference-data="change_reference_data($event)"
                ></g-viewer-tab>
              </gl-row>
            </golden-layout>
          </pane>

          <pane size="25" min-size="25" v-if="config !== 'deconfigged' && state.drawer_content.length > 0" style="background-color: #fafbfc; border-top: 6px solid #C75109; min-width: 250px">
            <v-card v-if="state.drawer_content === 'loaders'" flat tile class="overflow-y-auto fill-height" style="overflow-x: hidden" color="gray">
              <j-loader-panel
                :loader_items="state.loader_items"
                :loader_selected.sync="state.loader_selected"
                :api_hints_enabled="state.show_api_hints"
                :api_hints_obj="api_hints_obj || config"
                :server_is_remote="state.settings.server_is_remote"
              ></j-loader-panel>
            </v-card>

            <v-card v-if="state.drawer_content === 'logger'" flat tile class="overflow-y-auto fill-height" style="overflow-x: hidden" color="gray">
              <jupyter-widget :widget="state.tray_items[state.tray_items.map(ti => ti.label).indexOf('Logger')].widget"></jupyter-widget>
            </v-card>

            <v-card v-if="state.drawer_content === 'plugins'" flat tile class="overflow-y-auto fill-height" style="overflow-x: hidden" color="gray">
              <v-text-field
                v-model='state.tray_items_filter'
                append-icon='mdi-magnify'
                style="padding: 0px 8px"
                clearable
                hide-details
              ></v-text-field>
              <v-expansion-panels accordion multiple focusable flat tile v-model="state.tray_items_open">
                <v-expansion-panel v-for="(trayItem, index) in state.tray_items" :key="index">
                  <div v-if="trayItem.is_relevant && trayItemVisible(trayItem, state.tray_items_filter) && trayItem.label !== 'Logger'">
                    <v-expansion-panel-header class="plugin-header">
                      <v-list-item style="display: grid; min-height: 6px" class="plugin-title">
                        <v-list-item-title>
                          <j-tooltip :tipid="trayItem.name">
                            {{ trayItem.label }}
                          </j-tooltip>
                        </v-list-item-title>
                        <v-list-item-subtitle v-if="state.show_api_hints" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint" :style="state.tray_items_open.includes(index) ? 'font-weight: bold' : null">plg = {{  api_hints_obj || config }}.plugins['{{ trayItem.label }}']</span>
                        </v-list-item-subtitle>
                        <v-list-item-subtitle v-if="state.show_api_hints && state.tray_items_filter.length" v-for="api_method in trayItemMethodMatch(trayItem, state.tray_items_filter)" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint">plg.{{ api_method }}</span>
                        </v-list-item-subtitle>
                        <v-list-item-subtitle style="white-space: normal; font-size: 8pt">
                          {{ trayItem.tray_item_description }}
                        </v-list-item-subtitle>
                      </v-list-item>
                    </v-expansion-panel-header>
                    <v-expansion-panel-content style="margin-left: -12px; margin-right: -12px;">
                      <jupyter-widget v-if="state.tray_items_open.includes(index)" :widget="trayItem.widget"></jupyter-widget>
                    </v-expansion-panel-content>
                  </div>
                </v-expansion-panel>
              </v-expansion-panels>
              <v-divider></v-divider>
            </v-card>
            </pane>


        </splitpanes>
      </v-container>
    </v-content>
    <v-snackbar
      v-model="state.snackbar.show"
      :timeout="state.snackbar.timeout"
      :color="state.snackbar.color"
      top
      right
      transition="slide-x-transition"
      absolute
      style="margin-right: 95px; margin-top: -2px"
    >
      {{ state.snackbar.text }}

      <v-progress-circular
              v-if="state.snackbar.loading"
              indeterminate
      ></v-progress-circular>

      <v-btn
              v-if="!state.snackbar.loading"
              text
              @click="close_snackbar_message($event)"
      >
        Close
      </v-btn>
    </v-snackbar>
    <v-fade-transition>
      <div v-show="loading" class="jd-loading-overlay"></div>
    </v-fade-transition>
  </v-app>
</template>

<script>
export default {
  data() {
    return {
      outputCellHasHeight: false,
      showGoldenLayout: true,
    };
  },
  methods: {
    checkNotebookContext() {
      this.notebook_context = document.getElementById("ipython-main-app")
        || document.querySelector('.jp-LabShell')
        || document.querySelector(".lm-Widget#main"); /* Notebook 7 */
      return this.notebook_context;
    },
    trayItemVisible(trayItem, tray_items_filter) {
      if (tray_items_filter === null || tray_items_filter.length == 0) {
        return true
      }
      // simple exact text search match on the plugin title/description for now.
      description = trayItem.tray_item_description || ''
      label = trayItem.label || trayItem.name || ''
      return label.toLowerCase().includes(tray_items_filter.toLowerCase()) || description.toLowerCase().includes(tray_items_filter.toLowerCase()) || this.trayItemMethodMatch(trayItem, tray_items_filter).length > 0
    },
    trayItemMethodMatch(trayItem, tray_items_filter ) {
      if (tray_items_filter === null) {
        return []
      }
      if (tray_items_filter === '.') {
        return trayItem.api_methods
      }
      return trayItem.api_methods.filter((item) => ("."+item.toLowerCase()).includes(tray_items_filter.toLowerCase()))
    },
    onLayoutChange(v) {
      this.golden_layout_state = v;
      /* Workaround for #1677, can be removed when bqplot/bqplot#1531 is released */
      window.dispatchEvent(new Event('resize'));
    }
  },
  mounted() {
    /* Workaround for https://github.com/jupyter-widgets/ipywidgets/issues/2499, can be removed when ipywidgets 8 is
     * released */
    const jpOutputElem = this.$refs.mainapp.$el.closest('.jp-OutputArea-output');
    if (jpOutputElem) {
      jpOutputElem.classList.remove('jupyter-widgets');
    }
    /* Workaround for Lab 4.2: cells outside the viewport get the style "display: none" which causes the content to not
     * have height. This causes an error in size calculations of golden layout from which it doesn't recover.
     */
    new ResizeObserver(entries => {
      this.outputCellHasHeight = entries[0].contentRect.height > 0;
    }).observe(this.$refs.mainapp.$el);
    this.outputCellHasHeight = this.$refs.mainapp.$el.offsetHeight > 0

    /* workaround: when initializing with an existing golden_layout state, the layout doesn't show. rendering it a
     * second time the layout does show.
     */
    if (this.golden_layout_state) {
      setTimeout(() => {
        this.showGoldenLayout = false;
        setTimeout(() => {
          this.showGoldenLayout = true;
        }, 100);
      }, 500);
    }
  }
};
</script>

<style scoped>
.plugin-header.v-expansion-panel-header {
  padding-top: 8px;
  padding-bottom: 8px;
  padding-left: 4px;
  padding-right: 12px;
}
.plugin-title.v-list-item:after {
  display: none !important;
}
.app-bar-right .v-input__append-inner {
  padding-bottom: 6px !important;
}
</style>
