<template>
  <component :is="stack.container">
    <g-viewer-tab
      v-for="(child, index) in stack.children"
      :stack="child"
      :key="index"
      :data_items="data_items"
      :app_settings="app_settings"
      :icons="icons"
      :viewer_icons="viewer_icons"
      :layer_icons="layer_icons"
      @resize="(e) => $emit('resize', e)"
      :closefn="closefn"
      @call-viewer-method="$emit('call-viewer-method', $event)"
      @change-reference-data="$emit('change-reference-data', $event)"
    ></g-viewer-tab>
    <gl-component
      v-for="(viewer, index) in stack.viewers"
      :key="viewer.id"
      :title="viewer.reference || viewer.id"
      :tab-id="viewer.id"
      @resize="(e) => $emit('resize', e)"
      @destroy="destroy($event, viewer.id)"
      style="display: flex; flex-flow: column; height: 100%; overflow-y: auto; overflow-x: hidden"
    >
        <div>
          <v-row dense style="background-color: #205f76; margin: 0px" class="jdaviz-viewer-toolbar">
            <j-tooltip tooltipcontent="data-menu is now opened by clicking on the legend in the top-right of the viewer">
              <v-btn
                text 
                elevation="3" 
                color="white"
                tile
                icon
                outlined
                style="height: 42px; width: 42px"
                @click="$emit('call-viewer-method', {'id': viewer.id, 'method': '_deprecated_data_menu'})"
                >
                <v-icon>mdi-format-list-bulleted-square</v-icon>
              </v-btn>
            </j-tooltip>

            <v-toolbar-items v-if="viewer.reference === 'table-viewer'">
              <j-tooltip tipid='table-prev'>
                <v-btn icon @click="$emit('call-viewer-method', {'id': viewer.id, 'method': 'prev_row'})" color="white">
                  <v-icon>mdi-arrow-up-bold</v-icon>
                </v-btn>
              </j-tooltip>
              <j-tooltip tipid='table-next'>
                <v-btn icon @click="$emit('call-viewer-method', {'id': viewer.id, 'method': 'next_row'})" color="white">
                  <v-icon>mdi-arrow-down-bold</v-icon>
                </v-btn>
              </j-tooltip>
            </v-toolbar-items>
            <j-play-pause-widget v-if="viewer.reference == 'table-viewer'" @event="$emit('call-viewer-method', {'id': viewer.id, 'method': 'next_row'})"></j-play-pause-widget>
            <v-spacer></v-spacer>
            <jupyter-widget class='jdaviz-nested-toolbar' :widget="viewer.toolbar"></jupyter-widget>
          </v-row>

        </div>

        <v-card tile flat style="flex: 1; margin-top: -2px; overflow: hidden;">
          <jupyter-widget :widget="viewer.data_menu"></jupyter-widget>
          <jupyter-widget
            :widget="viewer.widget"
            :ref="'viewer-widget-'+viewer.id"
            style="width: 100%; height: 100%; overflow: hidden;"
          ></jupyter-widget>
        </v-card>
    </gl-component>
  </component>
</template>

<style>
</style>

<script>
module.exports = {
  name: "g-viewer-tab",
  props: ["stack", "data_items", "closefn", "app_settings", "icons", "viewer_icons", "layer_icons"],
  created() {
    this.$parent.childMe = () => {
      return this.$children[0];
    };
  },
  watch: {
    stack(new_stack, old_stack) {
      this.$emit('resize')
    }
  },
  methods: {
    computeChildrenPath() {
      return this.$parent.computeChildrenPath();
    },
    destroy(source, viewerId) {
      /* There seems to be no close event provided by vue-golden-layout, so we can't distinguish
       * between a user closing a tab or a re-render. However, when the user closes a tab, the
       * source of the event is a vue component. We can use that distinction as a close signal. */
      source.$root && this.closefn(viewerId);
    }
  },
  computed: {
    parentMe() {
      return this.$parent;
    },
    childMe() {
      return this.$children[0];
    }
  }
};
</script>
