<template>
  <v-menu
    v-if="selected_n_subsets > 0"
    absolute
    offset-y
    bottom
    left
  >
    <template v-slot:activator="{ on, attrs }">
      <j-tooltip
        :span_style="'display: inline-block; float: right; ' + (subset_edit_enabled ? '' : 'cursor: default;')"
        :tooltipcontent="subset_edit_tooltip"
      >
        <v-btn
          text
          class="invert-if-dark"
          v-bind="attrs"
          v-on="on"
          :disabled="!subset_edit_enabled"
        >
          Edit Subset
        </v-btn>
      </j-tooltip>
    </template>
    <v-list dense style="width: 300px">
      <v-list-item>
        <v-list-item-content>
          <j-tooltip :tooltipcontent="'Open '+subset_selected+' in Subset Tools plugin'">
            <span
              style="cursor: pointer; width: 100%"
              @click="() => {$emit('view-info')}"
            >
              Edit in plugin
            </span>
          </j-tooltip>
        </v-list-item-content>
      </v-list-item>

      <v-divider></v-divider>

      <v-list-item
        v-for="mode_item in subset_edit_modes"
        @mouseover="() => {hover_mode=mode_item.glue_name}"
        @mouseleave="() => {if (hover_mode == mode_item.glue_name) {hover_mode=''}}"
      >
        <v-list-item-icon style="margin-right: 4px">
          <img :src="mode_item.icon"/>
        </v-list-item-icon>
        <v-list-item-content>
          <!--
          <data-menu-subset-edit-modify
            :mode_item="mode_item"
          />
         -->
         {{ mode_item.glue_name }}
        </v-list-item-content>
        <v-list-item-action style="display: inline-block" v-if="hover_mode == mode_item.glue_name">
          <j-tooltip
              v-for="tool in subset_tools.slice().reverse()"
              :span_style="'display: inline-block; float: right;'"
              :tooltipcontent="api_hints_enabled ? '' : 'Interactively apply \'' + mode_item.glue_name + '\' logic to ' + subset_selected + ' using the ' + tool.name + ' tool'"
            >
              <v-btn
                icon
                max-height="24px"
                max-width="24px"
                @mouseover="() => {hover_api_hint = 'dm.modify_subset(\''+mode_item.glue_name+'\', \''+tool.name+'\')'}"
                @mouseleave="() => {if (!lock_hover_api_hint) {hover_api_hint = ''}}"
                @click="() => {$emit('modify-subset', mode_item.glue_name, tool.name)}"
              >
                <img :src="tool.img" class="invert-if-dark" width="20"/>
              </v-btn>
            </j-tooltip>
        </v-list-item-action>
      </v-list-item>
      <hover-api-hint
        v-if="api_hints_enabled"
        :hover_api_hint.sync="hover_api_hint"
        :lock_hover_api_hint.sync="lock_hover_api_hint"
      />
    </v-list>
  </v-menu>
</template>

<script>
module.exports = {
  data: function () {
      return {
        hover_mode: '',
        hover_api_hint: '',
        lock_hover_api_hint: false,
      }
    },
  props: ['subset_selected', 'subset_edit_enabled', 'subset_edit_tooltip', 'selected_n_subsets', 'subset_edit_modes', 'subset_tools', 'api_hints_enabled'],
};
</script>

<style scoped>
  .v-list-item__icon, .v-list-item__content, .v-list-item__action {
    /* even denser than dense */
    padding-top: 2px !important;
    padding-bottom: 2px !important;
    margin-top: 0px !important;
    margin-bottom: 0px !important;
  }
</style>