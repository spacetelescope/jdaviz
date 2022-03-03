<template>
  <component :is="stack.container">
    <g-viewer-tab
      v-for="(child, index) in stack.children"
      :stack="child"
      :key="index"
      :data-items="dataItems"
      @resize="$emit('resize')"
      :closefn="closefn"
      @data-item-selected="$emit('data-item-selected', $event)"
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
            <j-tooltip tipid="viewer-toolbar-data">
              <v-menu offset-y :close-on-content-click="false" v-model="viewer.data_open">
                <template v-slot:activator="{ on, attrs }">
                  <v-btn 
                    text 
                    elevation="3" 
                    v-bind="attrs" 
                    v-on="on" 
                    color="white"
                    tile
                    icon
                    outlined
                    :class="{active: viewer.data_open}"
                    style="height: 42px; width: 42px">
                    <v-icon>mdi-format-list-bulleted-square</v-icon>
                  </v-btn>
                </template>

                <v-list style="max-height: 500px; width: 350px;" class="overflow-y-auto">
                    <v-checkbox
                      v-for="item in dataItems" :key="item.id" :label="item.name" dense hide-details
                      :input-value="viewer.selected_data_items.includes(item.id)"
                      @change="$emit('data-item-selected', {
                        id: viewer.id,
                        item_id: item.id,
                        checked: $event
                      })"
                      class="pl-4"
                    ></v-checkbox>
                </v-list>
              </v-menu>
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
            <jupyter-widget class='jdaviz-nested-toolbar' :widget="viewer.toolbar_nested"></jupyter-widget>
          </v-row>

        </div>

        <v-card tile flat style="flex: 1; margin-top: -2px; overflow-y: auto;">
          <jupyter-widget :widget="viewer.widget" style="width: 100%; height: 100%"></jupyter-widget>
        </v-card>
    </gl-component>
  </component>
</template>

<script>
module.exports = {
  name: "g-viewer-tab",
  props: ["stack", "dataItems", "closefn"],
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
