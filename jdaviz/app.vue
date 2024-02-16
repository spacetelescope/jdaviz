<template>
  <v-app id="web-app" :style="checkNotebookContext() ? 'display: inline' : 'display: flex'" :class="'jdaviz ' + config" ref="mainapp">
    <jupyter-widget :widget="style_registry_instance"></jupyter-widget>
    <v-overlay v-if="state.logger_overlay"
      absolute
      opacity="0.7">
      <div :style="!state.settings.dense_toolbar ? 'position: absolute; top: 14px; right: 55px' : 'position: absolute; top: 6px; right: 55px'">
        <j-tooltip tipid="app-snackbar-history">
          <v-btn icon @click="state.logger_overlay = !state.logger_overlay" :class="{active : state.logger_overlay}">
            <v-icon medium style="padding-top: 2px">mdi-message-reply</v-icon>
          </v-btn>
        </j-tooltip>
      </div>
      <div :style="{'position': 'absolute',
                    'top': !state.settings.dense_toolbar ? '64px' : '48px',
                    'left': '0px',
                    'width': '100%',
                    'height': !state.settings.dense_toolbar ? 'calc(100% - 64px)' : 'calc(100% - 48px)',
                    'overflow-y': 'scroll',
                    'border-top': '6px solid #C75109',
                    'padding-left': '15%',
                    'padding-top': '20px'}"
            @click="state.logger_overlay = false">
        <v-row
            dense
            @click="(e) => {e.stopImmediatePropagation()}"
            v-for="history in state.snackbar_history.slice().reverse()"
            style="width: 80%">
          <v-alert
            dense
            :type="history.color"
            style="width: 100%; margin: 6px 0px 0px; text-align: left">
              [{{history.time}}]: {{history.text}}
          </v-alert>
        </v-row>
      </div>
    </v-overlay>
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
        <j-tooltip tipid="app-toolbar-popout">
          <jupyter-widget :widget="popout_button" ></jupyter-widget>
        </j-tooltip>
        <j-tooltip tipid="app-help">
          <v-btn icon :href="docs_link" target="_blank">
            <v-icon medium>mdi-help-box</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip tipid="app-snackbar-history">
          <v-btn icon @click="state.logger_overlay = !state.logger_overlay" :class="{active : state.logger_overlay}">
            <v-icon medium style="padding-top: 2px">mdi-message-reply-text</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip tipid="app-toolbar-plugins">
          <v-btn icon @click="state.drawer = !state.drawer" :class="{active : state.drawer}">
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
          <pane size="25" min-size="25" v-if="state.drawer" style="background-color: #fafbfc; border-top: 6px solid #C75109; min-width: 250px">
            <v-card flat tile class="overflow-y-auto fill-height" style="overflow-x: hidden" color="gray">
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
                    <v-expansion-panel-header >
                      <j-tooltip :tipid="trayItem.name">
                        {{ trayItem.label == 'Orientation' ? 'Orientation (prev. Links Control)' : trayItem.label }}
                      </j-tooltip>
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
      // simple exact text search match on the plugin title for now.
      return trayItem.label.toLowerCase().indexOf(tray_items_filter.toLowerCase()) !== -1
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
  }
};
</script>
