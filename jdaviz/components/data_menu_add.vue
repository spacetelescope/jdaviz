<template>
  <v-menu
    absolute
    offset-y
    left
    v-if="dataset_items.length > 0 || subset_tools.length > 0"
    >
    <template v-slot:activator="{ on, attrs }">
      <j-tooltip
        v-if="dataset_items.length > 0 || subset_tools.length > 0"
        tooltipcontent="Add data or subset to viewer"
      >
        <v-btn
          icon
          :class="loaded_n_data > 0 ? 'invert-if-dark' : 'invert-if-dark pulse'"
          v-bind="attrs"
          v-on="on"
        >
          <v-icon>mdi-plus</v-icon>
        </v-btn>
      </j-tooltip>
    </template>
    <v-list dense style="width: 300px; max-height: 300px; overflow-y: auto;">
      <v-subheader v-if="dataset_items.length > 0"><span>Load Data</span></v-subheader>
      <v-list-item
        v-for="data in dataset_items"
      >
        <v-list-item-content>
          <j-tooltip tooltipcontent="add data to viewer">
            <span
              style="cursor: pointer; width: 100%"
              :class="api_hints_enabled ? 'api-hint' : ''"
              @click="() => {$emit('add-data', data.label)}"
            >
              {{ api_hints_enabled ?
                'dm.add_data(\''+data.label+'\')'
                :
                data.label
              }} 
            </span>
          </j-tooltip>
        </v-list-item-content>
      </v-list-item>
      <v-subheader v-if="subset_tools.length > 0"><span>Create Subset</span></v-subheader>
      <v-list-item
        v-if="subset_tools.length > 0"
      >
        <v-list-item-content style="display: inline-block">
          <j-tooltip
            v-for="tool in subset_tools"
            span_style="display: inline-block"
            :tooltipcontent="api_hints_enabled ? '' : 'Create new '+tool.name+' subset'"
          >
            <v-btn 
              icon
              @mouseover="() => {hover_api_hint = 'dm.create_subset(\''+tool.name+'\')'}"
              @mouseleave="() => {if (!lock_hover_api_hint) {hover_api_hint = ''}}"
              @click="() => {$emit('create-subset', tool.name)}"
            >
              <img :src="tool.img" width="20" class="invert-if-dark"/>
            </v-btn>
          </j-tooltip>
        </v-list-item-content>
      </v-list-item>
      <hover-api-hint
        v-if="api_hints_enabled"
        :hover_api_hint.sync="hover_api_hint"
        :lock_hover_api_hint.sync="lock_hover_api_hint"
        :icons="icons"
      />
    </v-list>
  </v-menu>

</template>

<script>
module.exports = {
  data: function () {
      return {
        hover_api_hint: '',
        lock_hover_api_hint: false,
      }
    },
  props: ['dataset_items', 'subset_tools', 'loaded_n_data', 'api_hints_enabled', 'icons'],
};
</script>