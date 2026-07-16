<template>
  <div style="overflow: hidden; margin-right: 0px">
    <!-- Override mode indicator -->
    <v-btn-toggle
      v-if="tool_override_mode.length > 0"
      style="border-top-left-radius: 24px; border-bottom-left-radius: 24px;"
    >
      <v-btn @click="restore_tools" style="background-color: #007ba1; color: white; border-bottom-right-radius: 0; border-top-right-radius: 0; margin-right: -6px; padding-top: 3px">
        <j-tooltip :tooltipcontent="`exit '${tool_override_mode}' mode and restore original toolbar`" span_style="height: inherit; display: inherit; pointer-events: cursor;">
          <v-icon style="margin-left: 4px;">mdi-close</v-icon>
          <span style="color: white; margin-top: 3px; margin-left: 12px">{{ tool_override_mode }}</span>
        </j-tooltip>
      </v-btn>
    </v-btn-toggle>

    <!-- Custom widgets (dropdowns and sliders) -->
    <span v-if="custom_widget_items.length > 0" style="display: inline-flex; align-items: center; vertical-align: top; height: 42px; background-color: #007ba1; padding: 0 4px; margin-right: -4px;">
      <template v-for="(widget, idx) in custom_widget_items" :key="idx">
        <!-- Slider widget -->
        <j-tooltip v-if="widget.type === 'slider'" :tooltipcontent="widget.label" span_style="display: flex; align-items: center; height: 42px;">
          <span style="color: white; font-size: 12px; margin-right: 4px; white-space: nowrap; align-self: center;">{{ widget.label }}</span>
          <v-slider
            :model-value="custom_widget_selected[idx]"
            @update:modelValue="(val) => update_widget_selection(idx, val)"
            :min="widget.min !== undefined ? widget.min : 0"
            :max="widget.max !== undefined ? widget.max : 1"
            :step="widget.step !== undefined ? widget.step : 0.01"
            density="compact"
            hide-details
            style="min-width: 140px; max-width: 220px; margin: 0 4px; align-self: center;"
            class="custom-toolbar-slider"
            color="white"
            track-color="rgba(255,255,255,0.4)"
          ></v-slider>
          <span style="color: white; font-size: 12px; min-width: 32px; text-align: right; align-self: center;">{{ typeof custom_widget_selected[idx] === 'number' ? custom_widget_selected[idx].toFixed(2) : custom_widget_selected[idx] }}</span>
        </j-tooltip>
        <!-- Select/dropdown widget -->
        <v-select
          v-else
          :model-value="custom_widget_selected[idx]"
          @update:modelValue="(val) => update_widget_selection(idx, val)"
          :items="widget.items"
          :placeholder="widget.label"
          :multiple="widget.multiselect"
          :chips="widget.multiselect"
          :small-chips="widget.multiselect"
          deletable-chips
          density="compact"
          solo
          flat
          hide-details
          style="min-width: 120px; max-width: 250px;"
          class="custom-toolbar-select"
          item-title="label"
          item-value="value"
        ></v-select>
      </template>
    </span>

    <v-btn-toggle v-model="active_tool_id" :style="" class="transparent">
      <template v-for="[id, {tooltip, img, menu_ind, has_suboptions, primary, visible, disabled_msg}] of Object.entries(tools_data)" :key="id">
        <v-tooltip v-if="primary && visible &&!should_hide_in_popout(id)" location="bottom">
          <template v-slot:activator="{ props }">
            <v-btn v-bind="props" variant="text" density="comfortable" :value="id" :disabled="disabled_msg.length > 0" :style="get_tool_button_style(id, disabled_msg)" @contextmenu="(e) => show_submenu(e, has_suboptions, menu_ind)">
              <img class="invert-if-dark toolbar-icon-img" :src="img" @click.ctrl.stop=""/>
              <v-icon small v-if="has_suboptions" class="suboptions-carrot invert-if-dark" @click="(e) => show_submenu(e, has_suboptions, menu_ind)" @click.ctrl.stop="">mdi-menu-down</v-icon>
            </v-btn>
          </template>
          <span>{{ disabled_msg.length > 0 ? disabled_msg : tooltip }}{{has_suboptions ? " [click arrow for alt. tools]" : ""}}</span>
        </v-tooltip>
      </template>
    </v-btn-toggle>
    <v-menu
      v-model="show_suboptions"
      :activator="suboptions_target"
      location="bottom start"
      origin="top start"
      :open-on-click="false"
      :open-on-focus="false"
      :open-on-hover="false"
      :close-on-click="close_on_click"
    >
      <v-list>
        <template v-for="[id, {tooltip, img, menu_ind, has_suboptions, primary, visible}] of Object.entries(tools_data)" :key="id">
          <v-tooltip
            v-if="menu_ind==suboptions_ind && visible && !should_hide_in_popout(id)"
            location="start"
          >
            <template v-slot:activator="{ props }">
              <v-list-item
                v-bind="props"
                :active="primary"
                :class="{ 'suboptions-item-active': primary }"
                @click="() => select_primary([menu_ind, id])"
              >
                <v-list-item-title><img class='invert-if-dark' :src="img" width="20"/></v-list-item-title>
              </v-list-item>
            </template>
            <span>{{ tooltip }}</span>
          </v-tooltip>
        </template>
      </v-list>
    </v-menu>
  </div>
</template>

<script>
  export default {
    data() {
      return {
        suboptions_target: null,
      }
    },
    watch: {
      show_suboptions(value) {
        /* workaround for safari on MacOS, which triggers an extra click when using ctrl-click as right-click. The
         * `close-on-click` can't be prevented with `@click.ctrl.stop` */
        if (value) {
          setTimeout(() => {
            this.close_on_click = true;
          }, 100)
        } else {
          this.close_on_click = false;
        }
      }
    },
    methods: {
      should_hide_in_popout(id) {
        if (id == 'jdaviz:viewer_popout') {
          // hide when in popout context, show otherwise
          return !!(this.$el && this.$el.closest('.jupyter-widgets-popout-container'));
        }
        return false
      },
      get_tool_button_style(id, disabled_msg) {
        const viewerActionTools = [
          'jdaviz:viewer_focus_toggle',
          'jdaviz:viewer_clone',
          'jdaviz:viewer_popout',
        ];

        let style = 'min-width: 40px !important; width: 40px !important; height: 40px !important; padding: 0px !important;';
        if (viewerActionTools.includes(id)) {
          // top app-toolbar dark blue
          style += ' background-color: rgba(0, 59, 77, 1);';
        } else if (this.tool_override_mode.length > 0) {
          style += ' background-color: #007ba1;';
        }
        if (disabled_msg.length > 0) {
          style += ' opacity: 0.5;';
        }

        return style;
      },
      update_widget_selection(idx, val) {
        // Update the selection for a specific widget index
        let newSelected = [...this.custom_widget_selected];
        newSelected[idx] = val;
        this.custom_widget_selected = newSelected;
      },
      show_submenu (e, has_suboptions, menu_ind) {
        // needed to prevent browser context-menu
        e.preventDefault()
        // needed to prevent lab context-menu
        e.stopPropagation()
        if (!has_suboptions) {
          return
        }
        /* Find the clicked button and use it as the Vuetify menu activator. */
        this.show_suboptions = false
        this.suboptions_ind = menu_ind
        // e.path is not standard and not available in all browsers: https://stackoverflow.com/questions/39245488/event-path-is-undefined-running-in-firefox
        const path = e.path || (e.composedPath && e.composedPath()) || []
        const buttonEl = path.find(element => element && element.nodeName === 'BUTTON')
          || (e.currentTarget && e.currentTarget.closest && e.currentTarget.closest('button'))
          || (e.target && e.target.closest && e.target.closest('button'));
        if (!buttonEl) {
          return
        }
        this.suboptions_target = buttonEl
        this.$nextTick(() => {
          this.show_suboptions = true
        })
      }
    },
  }
</script>

<style>
.suboptions-carrot {
  transform: rotate(-45deg);
  bottom: 0px;
  right: 6px !important;
  margin-right: -22px;
  /* the parent button will invert everything anyways, so we need to override this to be black first,
     regardless of light or dark theme */
  color: black !important;
}
.toolbar-icon-img {
  width: 20px;
  height: 20px;
  display: block;
}
.suboptions-carrot:hover {
  scale: 1.75;
}
.theme--dark .invert-if-dark,
.v-theme--dark .invert-if-dark {
  filter: invert(1) !important;
}
.custom-toolbar-select {
  background-color: #007ba1 !important;
  border-radius: 4px !important;
}
.custom-toolbar-select.v-text-field.v-text-field--solo .v-input__slot {
  background-color: #007ba1 !important;
}
.custom-toolbar-select >>> .v-input__slot {
  min-height: 32px !important;
  padding: 0 8px !important;
  background-color: #007ba1 !important;
}
.custom-toolbar-select >>> .v-text-field__slot {
  background-color: #007ba1 !important;
}
.custom-toolbar-select >>> .v-select__slot {
  background-color: #007ba1 !important;
}
.custom-toolbar-select >>> .v-input__control {
  min-height: 32px !important;
}
.custom-toolbar-select >>> .v-select__selections {
  min-height: 28px !important;
  padding: 0 !important;
}
.custom-toolbar-select >>> .v-select__selection {
  color: white !important;
  font-size: 12px;
  margin: 2px 4px 2px 0 !important;
}
.custom-toolbar-select >>> .v-chip {
  height: 22px !important;
  margin: 2px !important;
}
.custom-toolbar-select >>> .v-chip .v-chip__content {
  font-size: 11px;
}
.custom-toolbar-select >>> .v-icon {
  color: white !important;
}
.custom-toolbar-select >>> input::placeholder {
  color: rgba(255, 255, 255, 0.7) !important;
}
.custom-toolbar-slider .v-slider-track__background,
.custom-toolbar-slider .v-slider-track__fill {
  opacity: 1 !important;
}
.custom-toolbar-slider .v-slider-thumb__surface {
  background-color: white !important;
}
.custom-toolbar-slider .v-input__control {
  min-height: unset !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
</style>
