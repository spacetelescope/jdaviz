<template>
  <v-app id="web-app" :style="checkNotebookContext() ? 'display: inline' : 'display: flex'" :class="'jdaviz ' + config" ref="mainapp">
    <jupyter-widget :widget="style_registry_instance"></jupyter-widget>
    <v-app-bar color="toolbar" dark :dense="state.settings.dense_toolbar" flat app absolute clipped-right :style="checkNotebookContext() ? 'margin-left: 1px; margin-right: 1px' : ''">

      <v-toolbar-items v-for="(item, index) in state.tool_items">
        <!-- this logic assumes the first entry is g-data-tools, if that changes, this may need to be modified -->
        <v-divider v-if="index > 1" vertical style="margin: 0px 10px"></v-divider>
        <j-tooltip v-if="['cubeviz', 'mosviz'].indexOf(config) !== -1 && item.name == 'g-data-tools' && state.data_items.length !== 0"></j-tooltip>
        <j-tooltip v-else :tipid="item.name">
          <jupyter-widget :widget="item.widget" :key="item.name"></jupyter-widget>
        </j-tooltip>
        <v-divider v-if="item.name === 'g-data-tools'" vertical style="margin: 0px 10px; border-width: 0"></v-divider>
      </v-toolbar-items>
      <v-spacer></v-spacer>
      <v-toolbar-items>
        <j-tooltip v-if="state.show_toolbar_buttons" tipid="app-toolbar-popout">
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
        <j-tooltip v-if="state.dev_loaders && (state.show_toolbar_buttons || state.drawer_content === 'loaders')" tipid="app-toolbar-loaders">
          <v-btn icon @click="() => {if (state.drawer_content === 'loaders') {state.drawer_content = ''} else {state.drawer_content = 'loaders'}}" :class="{active : state.drawer_content === 'loaders'}">
            <v-icon medium style="padding-top: 2px">mdi-plus-box</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip v-if="state.show_toolbar_buttons || state.drawer_content === 'logger'" tipid="app-toolbar-logger">
          <v-btn icon @click="() => {if (state.drawer_content === 'logger') {state.drawer_content = ''} else {state.drawer_content = 'logger'}}" :class="{active : state.drawer_content === 'logger'}">
            <v-icon medium style="padding-top: 2px">mdi-message-reply-text</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip v-if="state.show_toolbar_buttons || state.drawer_content === 'plugins'" tipid="app-toolbar-plugins">
          <v-btn icon @click="() => {if (state.drawer_content === 'plugins') {state.drawer_content = ''} else {state.drawer_content = 'plugins'}}" :class="{active : state.drawer_content === 'plugins'}">
            <v-icon>mdi-menu</v-icon>
          </v-btn>
        </j-tooltip>
      </v-toolbar-items>
    </v-app-bar>

    <v-content
      :style="checkNotebookContext() ? 'height: ' + state.settings.context.notebook.max_height + '; border: solid 1px #e5e5e5; border-top: 0px' : ''"
      :class="checkNotebookContext() ? '' : 'jdaviz__content--not-in-notebook'"
    >
      <v-container class="fill-height pa-0" fluid>
        <splitpanes>
          <pane size="75">
            <golden-layout
              v-if="outputCellHasHeight"
              style="height: 100%;"
              :has-headers="state.settings.visible.tab_headers"
              @state="onLayoutChange"
            >
              <gl-row :closable="false">
                <g-viewer-tab
                  v-for="(stack, index) in state.stack_items"
                  :stack="stack"
                  :key="stack.viewers.map(v => v.id).join('-')"
                  :data_items="state.data_items"
                  :app_settings="state.settings"
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
          <pane size="25" min-size="25" v-if="state.drawer_content.length > 0" style="background-color: #fafbfc; border-top: 6px solid #C75109; min-width: 250px">

            <v-card v-if="state.drawer_content === 'loaders'" flat tile class="overflow-y-auto fill-height" style="overflow-x: hidden" color="gray">
              <j-loader-panel
                :loader_items="state.loader_items"
                :loader_selected.sync="state.loader_selected"
                :api_hints_enabled="state.show_api_hints"
                :api_hints_obj="config"
              ></j-loader-panel>
            </v-card>

            <v-card v-if="state.drawer_content === 'logger'" flat tile class="overflow-y-auto fill-height" style="overflow-x: hidden" color="gray">
              <v-alert v-if="state.snackbar_history.length === 0" dense type="info">No logger messages</v-alert>
              <v-row
                  dense
                  @click="(e) => {e.stopImmediatePropagation()}"
                  v-for="history in state.snackbar_history.slice().reverse()"
                  style="margin: 6px 0px 0px 0px"
              >
                <v-alert
                  dense
                  :type="history.color">
                    [{{history.time}}]: {{history.text}}
                </v-alert>
              </v-row>
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
                  <div v-if="trayItem.is_relevant && trayItemVisible(trayItem, state.tray_items_filter)">
                    <v-expansion-panel-header class="plugin-header">
                      <v-list-item style="display: grid; min-height: 6px" class="plugin-title">
                        <v-list-item-title>
                          <j-tooltip :tipid="trayItem.name">
                            {{ trayItem.label }}
                          </j-tooltip>
                        </v-list-item-title>
                        <v-list-item-subtitle v-if="state.show_api_hints" style="white-space: normal; font-size: 8pt; padding-top: 4px; padding-bottom: 4px" class="api-hint">
                          <span class="api-hint" :style="state.tray_items_open.includes(index) ? 'font-weight: bold' : null">plg = {{  config }}.plugins['{{ trayItem.label }}']</span>
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
      return trayItem.label.toLowerCase().includes(tray_items_filter.toLowerCase()) || trayItem.tray_item_description.toLowerCase().includes(tray_items_filter.toLowerCase()) || this.trayItemMethodMatch(trayItem, tray_items_filter).length > 0
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
    onLayoutChange() {
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
</style>
