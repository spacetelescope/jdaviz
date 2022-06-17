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
      @data-item-visibility="$emit('data-item-visibility', $event)"
      @data-item-unload="$emit('data-item-unload', $event)"
      @data-item-remove="$emit('data-item-remove', $event)"
      @call-viewer-method="$emit('call-viewer-method', $event)"
    ></g-viewer-tab>
    <gl-component
      v-for="(viewer, index) in stack.viewers"
      :key="viewer.id"
      :title="viewer.config === 'cubeviz' ? viewer.reference : viewer.id"
      :tab-id="viewer.id"
      @resize="resizeViewer(viewer)"
      @destroy="destroy($event, viewer.id)"
      style="display: flex; flex-flow: column; height: 100%; overflow-y: auto; overflow-x: hidden"
    >
        <div>
          <v-row dense style="background-color: #205f76; margin: 0px" class="jdaviz-viewer-toolbar">
            <j-viewer-data-select
              :data_items="data_items" 
              :viewer="viewer"
              :app_settings="app_settings"
              :layer_icons="layer_icons"
              :icons="icons"
              @data-item-visibility="$emit('data-item-visibility', $event)"
              @data-item-unload="$emit('data-item-unload', $event)"
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
            <jupyter-widget class='jdaviz-nested-toolbar' :widget="viewer.toolbar"></jupyter-widget>
          </v-row>

        </div>

        <v-card tile flat style="flex: 1; margin-top: -2px; overflow-y: hidden;">
          <div v-if="app_settings.viewer_labels" class='viewer-label-container'>
            <div v-if="Object.keys(viewer_icons).length > 1" class="viewer-label invert-if-dark">
              <j-tooltip span_style="white-space: nowrap">
                <j-layer-viewer-icon span_style="float: right;" :icon="viewer_icons[viewer.id]"></j-layer-viewer-icon>
              </j-tooltip>
              <span class="invert-if-dark" style="margin-left: 24px; margin-right: 32px; line-height: 24px">{{viewer.reference || viewer.id}}</span>
            </div>

            <div v-for="(layer_info, layer_name) in viewer.visible_layers" class="viewer-label invert-if-dark">
              <j-tooltip span_style="white-space: nowrap">
                <j-layer-viewer-icon span_style="float: right;" :icon="layer_icons[layer_name]" :linewidth="layer_info.linewidth" :linestyle="'solid'" :color="layer_info.color"></j-layer-viewer-icon>
              </j-tooltip>
              <span class="invert-if-dark" style="margin-left: 24px; margin-right: 32px; line-height: 24px">
                <v-icon v-if="layer_info.prefix_icon" dense>
                  {{layer_info.prefix_icon}}
                </v-icon>
                {{layer_name}}{{layer_info.suffix_label}}
              </span>
            </div>
          </div>

          <jupyter-widget
            :widget="viewer.widget"
            :ref="'viewer-widget-'+viewer.id"
            :style="'width: 100%; height: 100%; overflow: hidden; transform: rotate('+viewer.rotation+'deg)'"
          ></jupyter-widget>
        </v-card>
    </gl-component>
  </component>
</template>

<style>
.viewer-label-container {
  position: absolute;
  right: 0;
  z-index: 1;
  width: 24px;
}
.viewer-label {
  display: block;
  float: right;
  background-color: #c3c3c3c3;
  width: 24px;
  overflow: hidden;
  white-space: nowrap;
  /*cursor: pointer;*/
}
.viewer-label:last-child {
  padding-bottom: 2px;
}
.viewer-label:hover {
  background-color: #e5e5e5;
  width: auto;
  border-bottom-left-radius: 4px; 
  border-top-left-radius: 4px;
}
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
      console.log("watch: stack")
      new_stack.viewers.forEach((viewer) => {
        console.log("original resize of "+viewer.id)
        this.resizeViewer(viewer)
      })
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
    },
    resizeViewer(viewer) {
      if (viewer.config !== 'imviz') {
        this.$emit('resize')
        return
      }

      const viewerWidget = this.$refs['viewer-widget-'+viewer.id][0]
      const cardEl = viewerWidget.$parent
      const cardHeight = cardEl.$el.clientHeight
      const cardWidth = cardEl.$el.clientWidth

      // resize width and height to be the diagonal dimension, 
      // then offset so the center stays in the center
      // TODO: eventually we may want to make this dynamic to avoid over-resizing
      // (by using a rectangle and also adjusting as the rotation angle is changed)
      const diagDim = (cardEl.$el.clientHeight**2+cardEl.$el.clientWidth**2)**0.5;
      const top = (cardHeight - diagDim) / 2
      const left = (cardWidth - diagDim) / 2

      viewerWidget.$el.style.height = diagDim+"px"
      viewerWidget.$el.style.width = diagDim+"px"
      viewerWidget.$el.style.position = 'absolute'
      viewerWidget.$el.style.top = top+"px"
      viewerWidget.$el.style.left = left+"px"
      //console.log("diagDim: "+diagDim+ " top: "+top+" left: "+left)

      // TODO: "undo" oversizing by adjusting the viewer.zoom_level
      // TODO: box zoom also needs to account for scale factor to set limits that result in the box
      // being shown in the viewer, not the oversized canvas
      this.$emit('resize', {viewer: viewer.id,
                            height: cardHeight,
                            width: cardWidth,
                            canvasHeight: diagDim,
                            canvasWidth: diagDim})
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
