<template>
  <div style="overflow: hidden">
    <v-btn-toggle v-model="active_tool_id" class="transparent">
        <v-tooltip v-for="[id, {tooltip, img, menu_ind, has_suboptions, primary, visible}] of Object.entries(tools_data)" v-if="primary && visible" bottom>
            <template v-slot:activator="{ on }">
                <v-btn v-on="on" icon :value="id" style="min-width: 40px !important" @contextmenu="(e) => show_submenu(e, has_suboptions, menu_ind)">
                    <img :src="img" width="20px" @click.ctrl.stop=""/>
                    <v-icon small v-if="has_suboptions" class="suboptions-carrot" @click.ctrl.stop="">mdi-menu-down</v-icon>
                </v-btn>
            </template>
            <span>{{ tooltip }}{{has_suboptions ? " [right-click for alt. tools]" : ""}}</span>
        </v-tooltip>
    </v-btn-toggle>
    <v-menu
      v-model="show_suboptions"
      :position-x="suboptions_x"
      :position-y="suboptions_y"
      absolute
      offset-y
      dense
      :close-on-click="close_on_click"
    >
      <v-list>
        <v-tooltip
          v-for="[id, {tooltip, img, menu_ind, has_suboptions, primary, visible}] of Object.entries(tools_data)"
          v-if="menu_ind==suboptions_ind && visible"
          :key="id"
          left
        >
          <template v-slot:activator="{ on, attrs }">
            <v-list-item v-bind="attrs" v-on="on" :input-value="primary" @click="() => select_primary([menu_ind, id])">
              <v-list-item-title><img class='invert-if-dark' :src="img" width="20"/></v-list-item-title>
            </v-list-item>
          </template>
          <span>{{ tooltip }}</span>
        </v-tooltip>
      </v-list>
    </v-menu>
  </div>
</template>

<script>
  export default {
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
      show_submenu (e, has_suboptions, menu_ind) {
        // needed to prevent browser context-menu
        e.preventDefault()
        // needed to prevent lab context-menu
        e.stopPropagation()
        if (!has_suboptions) {
          return
        }
        /* find the absolute position of the clicked button and position the overlaying
           submenu directly below.  Note that scrolling while the menu is open will leave
           the menu fixed on the window */
        this.show_suboptions = false
        this.suboptions_ind = menu_ind
        // e.path is not standard and not available in all browsers: https://stackoverflow.com/questions/39245488/event-path-is-undefined-running-in-firefox
        const path = e.path || (e.composedPath && e.composedPath());
        const bb = path.find(element => element.nodeName == 'BUTTON').getBoundingClientRect()
        this.suboptions_x = bb.left
        this.suboptions_y = bb.bottom
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

.theme--dark .invert-if-dark {
  filter: invert(1) !important;
}
</style>
