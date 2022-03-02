<template>
  <div style="overflow-y: hidden">
    <v-btn-toggle v-model="active_tool_id" class="transparent">
        <v-tooltip v-for="[id, {tooltip, img, menu_ind, has_suboptions, primary}] of Object.entries(tools_data)" v-if="primary" bottom>
            <template v-slot:activator="{ on }">
                <v-btn v-on="on" icon :value="id" @contextmenu="(e) => show_submenu(e, has_suboptions, menu_ind)">
                    <img :src="img" width="20"/>
                    <v-icon v-if="has_suboptions" style="position: absolute; transform: rotate(-45deg); bottom: 0px; right: 0px; margin-bottom: -18px; margin-right: -18px;">mdi-menu-down</v-icon>
                </v-btn>
            </template>
            <span>{{ tooltip }}</span>
        </v-tooltip>
    </v-btn-toggle>
    <v-menu
      v-model="show_suboptions"
      :position-x="suboptions_x"
      :position-y="suboptions_y"
      absolute
      offset-y
      dense
    >
      <v-list>
        <v-tooltip
          v-for="[id, {tooltip, img, menu_ind, has_suboptions, primary}] of Object.entries(tools_data)"
          v-if="menu_ind==suboptions_ind && !primary"
          :key="id"
          left
        >
          <template v-slot:activator="{ on, attrs }">
            <v-list-item v-bind="attrs" v-on="on">
              <v-list-item-title @click="() => select_primary([menu_ind, id])"><img :src="img" width="20"/></v-list-item-title>
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
    methods: {
      show_submenu (e, has_suboptions, menu_ind) {
        e.preventDefault()
        if (!has_suboptions) {
          return
        }
        this.show_suboptions = false
        this.suboptions_ind = menu_ind
        const bb = e.path.find(element => element.nodeName == 'BUTTON').getBoundingClientRect()
        this.suboptions_x = bb.left
        this.suboptions_y = bb.bottom
        this.$nextTick(() => {
          this.show_suboptions = true
        })
      }
    },
  }
</script>
