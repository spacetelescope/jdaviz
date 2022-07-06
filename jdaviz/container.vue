<template>
  <component :is="stack.container">
    <g-viewer-tab
      v-for="(child, index) in stack.children"
      :stack="child"
      :key="index"
      :data_items="data_items"
      :app_settings="app_settings"
      :icons="icons"
      @resize="$emit('resize')"
      :closefn="closefn"
      @data-item-selected="$emit('data-item-selected', $event)"
      @data-item-visibility="$emit('data-item-visibility', $event)"
      @data-item-remove="$emit('data-item-remove', $event)"
      @call-viewer-method="$emit('call-viewer-method', $event)"
    ></g-viewer-tab>
    <gl-component
      v-for="(viewer, index) in stack.viewers"
      :key="viewer.id"
      :title="viewer.id"
      :tab-id="viewer.id"
      @resize="$emit('resize')"
      @destroy="destroy($event, viewer.id)"
      style="display: flex; flex-flow: column; height: 100%; overflow-y: auto; overflow-x: hidden"
    >
        <div>
          <v-row dense style="background-color: #205f76" class="jdaviz-viewer-toolbar">
            <j-viewer-data-select
              :data_items="data_items" 
              :viewer="viewer"
              :app_settings="app_settings"
              :icons="icons"
              @data-item-selected="$emit('data-item-selected', $event)"
              @data-item-visibility="$emit('data-item-visibility', $event)"
              @data-item-remove="$emit('data-item-remove', $event)"
            ></j-viewer-data-select>


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
            <jupyter-widget class='jdaviz-nested-toolbar' :widget="viewer.toolbar_nested"></jupyter-widget>
          </v-row>

        </div>

        <v-card tile flat style="flex: 1; margin-top: -2px; overflow-y: auto">
          <div :class="viewer.config==='imviz' ? 'viewer-label viewer-label-imviz invert-if-dark' : 'viewer-label invert-if-dark'">
            <j-tooltip :tooltipcontent="viewer.reference+' (click to select)'" span_style="white-space: nowrap">
              <v-icon :class="viewer.config==='imviz' ? 'invert' : 'invert-if-dark'">mdi-numeric-{{viewer.index}}-circle-outline</v-icon>
            </j-tooltip>
            <span :class="viewer.config==='imviz' ? 'invert' : 'invert-if-dark'" style="padding: 10px">{{viewer.reference || viewer.id}}</span>
          </div>
          <jupyter-widget :widget="viewer.widget" style="width: 100%; height: 100%"></jupyter-widget>
        </v-card>
    </gl-component>
  </component>
</template>

<style>
.viewer-label {
  position: absolute;
  background-color: transparent;
  border-bottom-right-radius: 4px; 
  z-index: 1;
  width: 24px;
  overflow: hidden;
  white-space: nowrap;
  cursor: pointer;
}
.viewer-label-imviz {
  background-color: #393939c2;
}
.viewer-label:hover {
  background-color: #e5e5e5;
  width: auto;
}
.viewer-label-imviz:hover {
  background-color: #777777c2;
}
</style>

<script>
module.exports = {
  name: "g-viewer-tab",
  props: ["stack", "data_items", "closefn", "app_settings", "icons"],
  created() {
    this.$parent.childMe = () => {
      return this.$children[0];
    };
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
