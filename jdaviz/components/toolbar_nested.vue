<template>
  <div class="toolbar-nested-root" style="display: inline-flex; justify-content: flex-end; max-width: 100%; min-width: 0; overflow: hidden; margin-right: 0px">
    <!-- Override mode indicator -->
    <v-btn-toggle
      v-if="tool_override_mode.length > 0"
      class="custom-toolbar-mode-toggle"
      style="border-top-left-radius: 24px; border-bottom-left-radius: 24px;"
    >
      <v-btn class="custom-toolbar-mode-button" @click="restore_tools" style="background-color: #007ba1; color: white; border-bottom-right-radius: 0; border-top-right-radius: 0; margin-right: -6px; padding-top: 3px">
        <j-tooltip :tooltipcontent="`exit '${tool_override_mode}' mode and restore original toolbar`" span_style="height: inherit; display: inherit; pointer-events: cursor;">
          <v-icon style="margin-left: 4px;">mdi-close</v-icon>
          <span class="custom-toolbar-mode-label" style="color: white; margin-top: 0px; margin-left: 12px">{{ tool_override_mode }}</span>
        </j-tooltip>
      </v-btn>
    </v-btn-toggle>

    <!-- Custom widgets (dropdowns, text inputs, and sliders) -->
    <span v-if="custom_widget_items.length > 0" class="custom-toolbar-widgets" style="display: inline-flex; align-items: center; vertical-align: top; height: 42px; background-color: #007ba1; padding: 0 4px; margin-right: -4px;">
      <template v-for="(widget, idx) in custom_widget_items" :key="idx">
        <!-- Text input widget -->
        <v-text-field
          v-if="widget.type === 'text'"
          :model-value="custom_widget_selected[idx]"
          @update:modelValue="(val) => update_widget_selection(idx, val)"
          :placeholder="widget.label"
          density="compact"
          solo
          flat
          hide-details
          style="min-width: 140px; max-width: 240px;"
          class="custom-toolbar-text-input"
        ></v-text-field>
        <!-- Slider widget -->
        <j-tooltip v-else-if="widget.type === 'slider'" :tooltipcontent="widget.label" span_style="display: flex; align-items: center; height: 42px;">
          <span style="color: white; font-size: 12px; margin-right: 4px; white-space: nowrap; align-self: center;">{{ widget.label }}</span>
          <v-slider
            :model-value="custom_widget_selected[idx]"
            @update:modelValue="(val) => update_widget_selection(idx, val)"
            :min="widget.min !== undefined ? widget.min : 0"
            :max="widget.max !== undefined ? widget.max : 1"
            :step="widget.step !== undefined ? widget.step : 0.01"
            density="compact"
            hide-details
            style="min-width: 140px; max-width: 220px; margin: 16px 4px 0 4px; align-self: flex-start;"
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
          density="compact"
          variant="solo"
          flat
          hide-details
          :style="widget.multiselect ? 'width: 100%; max-width: 320px;' : 'width: 100%; max-width: 250px;'"
          class="custom-toolbar-select"
          item-title="label"
          item-value="value"
        >
          <template v-slot:selection="{ item, index }">
            <span v-if="!widget.multiselect" class="custom-toolbar-selection-text">{{ item.title }}</span>
            <v-chip
              v-else-if="index < max_chips(widget)"
              size="x-small"
              label
              class="custom-toolbar-chip"
            >{{ item.title }}</v-chip>
            <span
              v-else-if="index === max_chips(widget)"
              class="custom-toolbar-overflow"
              :title="(custom_widget_selected[idx] || []).join(', ')"
            >+{{ (custom_widget_selected[idx] || []).length - max_chips(widget) }} more</span>
          </template>
        </v-select>
      </template>
    </span>

    <v-btn-toggle v-if="custom_widget_items.length === 0" v-model="active_tool_id" style="overflow-x: hidden" class="transparent">
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
      },
      tool_override_mode(newVal) {
        // Mirror into a JS global so viewer_window.vue can block mousemove
        // re-renders with zero latency (no Python round-trip needed).
        window._jdaviz_override_mode = !!newVal;

        // bqplot_image_gl calls element.focus() inside its mousemove handler,
        // which causes the v-select input to blur and Vuetify to close the
        // dropdown.  focus() lives on HTMLElement.prototype (NOT Element.prototype),
        // so that is the correct prototype to patch.
        if (newVal && !window._jdaviz_orig_focus) {
          window._jdaviz_orig_focus = HTMLElement.prototype.focus;
          HTMLElement.prototype.focus = function(options) {
            if (!window._jdaviz_override_mode) {
              return window._jdaviz_orig_focus.call(this, options);
            }
            // Allow focus within the toolbar itself or the floating overlay (dropdown list)
            const toolbar = document.querySelector('.jdaviz-nested-toolbar');
            const overlay = document.querySelector('.v-overlay-container');
            if ((toolbar && toolbar.contains(this)) || (overlay && overlay.contains(this))) {
              return window._jdaviz_orig_focus.call(this, options);
            }
            // Suppress all other focus() calls (e.g. bqplot_image_gl canvas focus)
          };
        } else if (!newVal && window._jdaviz_orig_focus) {
          HTMLElement.prototype.focus = window._jdaviz_orig_focus;
          delete window._jdaviz_orig_focus;
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

        let style = 'min-width: 42px !important; width: 42px !important; height: 42px !important; padding: 0px !important;';
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
      max_chips(widget) {
        // number of chips shown inline before collapsing the rest into a "+N" counter
        return widget.max_chips !== undefined ? widget.max_chips : 3;
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
  display: inline-block;
  object-fit: contain;
  vertical-align: middle;
}
.suboptions-carrot:hover {
  scale: 1.75;
}
.theme--dark .invert-if-dark,
.v-theme--dark .invert-if-dark {
  filter: invert(1) !important;
}
.toolbar-nested-root {
  container-type: inline-size;
  flex-wrap: nowrap;
  align-items: flex-start;
  justify-content: flex-end;
  max-width: 100%;
  min-width: 0;
}
.custom-toolbar-mode-toggle {
  display: inline-flex !important;
  flex: 0 0 auto !important;
  width: fit-content !important;
  margin-right: 0 !important;
}
.custom-toolbar-mode-button {
  flex: 0 0 auto !important;
  min-width: 42px !important;
}
.custom-toolbar-mode-label {
  display: inline-block;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.custom-toolbar-widgets {
  display: inline-flex !important;
  flex: 0 1 auto !important;
  width: fit-content !important;
  min-width: 0;
  max-width: 100%;
  margin-left: 0 !important;
}
.custom-toolbar-select {
  flex: 1 1 auto !important;
  min-width: 0 !important;
  max-width: 100% !important;
  background-color: #007ba1 !important;
  border-radius: 4px !important;
}
.custom-toolbar-select .v-field,
.custom-toolbar-select .v-field__overlay {
  background-color: #007ba1 !important;
  box-shadow: none !important;
  border-radius: 4px !important;
  opacity: 1 !important;
}
.custom-toolbar-select .v-input__control {
  min-height: 32px !important;
  min-width: 0 !important;
}
/* selected text and input field */
.custom-toolbar-select .v-select__selection-text,
.custom-toolbar-select .v-field__input,
.custom-toolbar-select .v-field__input input,
.custom-toolbar-select input {
  color: white !important;
  font-size: 12px !important;
}
/* keep selections on a single line, collapsing overflow into the "+N" counter */
.custom-toolbar-select .v-field__input {
  min-width: 0 !important;
  flex-wrap: nowrap !important;
  overflow: hidden !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  min-height: 32px !important;
  row-gap: 0 !important;
}
.custom-toolbar-select .v-field__input > input {
  flex: 1 1 0 !important;
  min-width: 0 !important;
}
.custom-toolbar-select .v-field__field {
  min-width: 0 !important;
  overflow: hidden !important;
}
.custom-toolbar-select .v-field__append {
  flex: 0 0 28px !important;
  min-width: 28px !important;
  padding-inline-start: 4px !important;
}
.custom-toolbar-select .v-select__selection {
  margin: 0 !important;
  overflow: hidden !important;
}
.custom-toolbar-select .v-chip {
  height: 20px !important;
  margin: 0 2px 0 0 !important;
  padding: 0 6px !important;
  flex: none !important;
  background-color: rgba(255, 255, 255, 0.2) !important;
  color: white !important;
}
.custom-toolbar-select .v-chip .v-chip__content {
  font-size: 11px;
  white-space: nowrap;
  display: block;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.custom-toolbar-overflow {
  color: white !important;
  font-size: 11px;
  white-space: nowrap;
  flex: none;
  margin-left: 2px;
}
.custom-toolbar-selection-text {
  color: white !important;
  font-size: 12px;
  white-space: nowrap;
}
.custom-toolbar-select .v-icon {
  color: white !important;
}
.custom-toolbar-select input::placeholder {
  color: rgba(255, 255, 255, 0.7) !important;
}
@container (max-width: 520px) {
  .custom-toolbar-mode-label {
    display: none;
  }
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
  display: flex !important;
  align-items: center !important;
}
</style>
