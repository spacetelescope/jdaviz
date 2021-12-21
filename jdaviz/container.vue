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
      @save-figure="$emit('save-figure', $event)"
      @call-viewer-method="$emit('call-viewer-method', $event)"
    ></g-viewer-tab>
    <gl-component
      v-for="(viewer, index) in stack.viewers"
      :key="viewer.id"
      :title="viewer.id"
      :tab-id="viewer.id"
      @resize="$emit('resize')"
      @destroy="destroy($event, viewer.id)"
      style="display: flex; flex-flow: column; overflow: hidden"
    >
        <div>
          <v-row dense style="background-color: #205f76">
            <v-col md="auto">
              <j-tooltip tipid="viewer-toolbar-data">
                <v-menu offset-y :close-on-content-click="false" v-model="viewer.data_open">
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn 
                      text 
                      elevation="3" 
                      v-bind="attrs" 
                      v-on="on" 
                      color="white"
                      :class="{active: viewer.data_open}">
                      Data
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
                      />
                  </v-list>
                </v-menu>
              </j-tooltip>


              </v-col>
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
               <v-toolbar-items>
               <j-tooltip tipid='viewer-toolbar-figure'>
                 <!-- NOTE: since this is just a btn, not a toggle or menu, we cannot use v-model
                      but instead will use @click to toggle the state AND close any other active
                      toolbar menus (that won't already by close-on-content-click)-->
                 <v-btn icon @click="viewer.tools_open = !viewer.tools_open" :class="{active: viewer.tools_open}" color="white">
                   <v-icon>mdi-hammer-screwdriver</v-icon>
                 </v-btn>
               </j-tooltip>
               <j-tooltip tipid='viewer-toolbar-menu'>
                 <!-- NOTE: this case uses v-menu, so we'll control the active state with v-model
                      on that component, but close any other active toolbar menus (that won't already
                      with close-on-content-click with the @click on the underlying button component  
                  -->
                <v-menu offset-y :close-on-content-click="false" style="z-index: 10" v-model="viewer.layer_viewer_open">
                  <template v-slot:activator="{ on }">
                    <v-btn icon v-on="on" :class="{active : viewer.layer_viewer_open}" color="white" @click="viewer.tools_open=false">
                      <v-icon>tune</v-icon>
                    </v-btn>
                  </template>

                  <v-tabs v-model="viewer.tab" grow height="36px">
                    <v-tab key="0">Layer</v-tab>
                    <v-tab key="1">Viewer</v-tab>
                  </v-tabs>

                  <!-- NOTE: v-lazy needed for initial tab underline: https://github.com/vuetifyjs/vuetify/issues/1978#issuecomment-676892274 -->
                  <v-lazy>
                    <v-tabs-items v-model="viewer.tab" style="max-height: 500px; width: 350px;" lazy>

                    <v-tab-item key="0" class="overflow-y-auto" style="height: 100%">
                      <v-sheet class="px-4">
                        <jupyter-widget :widget="viewer.layer_options" /> 
                      </v-sheet>
                    </v-tab-item>

                    <v-tab-item key="1" eager class="overflow-y-auto" style="height: 100%">
                      <v-sheet class="px-4">
                        <jupyter-widget :widget="viewer.viewer_options" />
                      </v-sheet>
                    </v-tab-item>
                  </v-tabs-items>
                </v-menu>
               </j-tooltip>
               <j-tooltip tipid='viewer-toolbar-more'>
                <v-btn icon color="white">
                  <v-icon>more_horiz</v-icon>
                </v-btn>
               </j-tooltip>
             </v-toolbar-items>
          </v-row>

        </div>

        <v-card tile flat style="flex: 1; margin-top: -2px;">

        <v-toolbar
          dense
          floating
          absolute
          :tools_open="viewer.tools_open"
          elevation="1"
          :width="viewer.tools_open ? null : '0px'"
          style="right: 2px;"
        >
          <v-toolbar-items class="toolbar-jdaviz-style">

            <!-- <v-divider vertical></v-divider> -->
            <jupyter-widget :widget="viewer.tools"></jupyter-widget>
            <v-menu offset-y left :close-on-content-click="true" style="z-index: 10">
             <template v-slot:activator="{ on }">
               <v-btn icon color="primary" v-on="on">
                <j-tooltip tipid="viewer-toolbar-figure-save" nudgebottom="14">
                  <v-icon>mdi-content-save</v-icon>
                </j-tooltip>
               </v-btn>
             </template>
             <v-list>
              <v-list-item>
               <v-btn
                color="primary"
                @click="$emit('save-figure', {'id': viewer.id, 'filetype': 'png'})"
               >
                Save as PNG
               </v-btn>
              </v-list-item>
              <v-list-item>
               <v-btn
                color="primary"
                @click="$emit('save-figure', {'id': viewer.id, 'filetype': 'svg'})"
               >
                Save as SVG
               </v-btn>
              </v-list-item>
             </v-list>
            </v-menu>
          </v-toolbar-items>
        </v-toolbar>
        <jupyter-widget :widget="viewer.widget" style="width: 100%; height: 100%" />
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
