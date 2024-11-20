<template>
  <div>
  <v-row v-if="items.length > 1 || selected.length===0 || show_if_single_entry || api_hints_enabled">
    <v-select
      :menu-props="{ left: true }"
      attach
      :items="items"
      v-model="selected"
      @change="$emit('update:selected', $event)"
      :label="api_hints_enabled && api_hint ? api_hint : (label ? label : 'Layer')"
      :class="api_hints_enabled ? 'api-hint' : null"
      :hint="hint ? hint : 'Select layer.'"
      :rules="rules ? rules : []"
      :multiple="multiselect"
      :chips="multiselect && !api_hints_enabled"
      item-text="label"
      item-value="label"
      :persistent-hint="!disable_persistent_hint"
      :hide-details="disable_persistent_hint"
    >
    <template v-slot:selection="{ item, index }">
      <div class="single-line" style="width: 100%">
        <span v-if="api_hints_enabled" class="api-hint" :style="index > 0 ? 'display: none' : null">
          {{ multiselect ?
            selected
            :
            '\'' + selected + '\''
          }}
        </span>
        <v-chip v-else-if="multiselect" style="width: calc(100% - 10px)">
          <span>
            <j-layer-viewer-icon v-if="data.item.icon" :icon="item.icon" :icons="icons" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
            {{ item.label }}
          </span>
        </v-chip>
        <span v-else >
          <j-layer-viewer-icon v-if="item.icon" span_style="margin-right: 4px" :icon="item.icon" :icons="icons" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
          {{ item.label }}
        </span>
      </div>
    </template>
    <template v-slot:prepend-item v-if="multiselect">
      <v-list-item
        ripple
        @mousedown.prevent
        @click="() => {if (selected.length < items.length) { $emit('update:selected', items.map((item) => item.label))} else {$emit('update:selected', [])}}"
      >
        <v-list-item-action>
          <v-icon>
            {{ selected.length == items.length ? 'mdi-close-box' : selected.length ? 'mdi-minus-box' : 'mdi-checkbox-blank-outline' }}
          </v-icon>
        </v-list-item-action>
        <v-list-item-content>
          <v-list-item-title>
            {{ selected.length < items.length ? "Select All" : "Clear All" }}
          </v-list-item-title>
        </v-list-item-content>
      </v-list-item>
      <v-divider class="mt-2"></v-divider>
    </template>
    <template slot="item" slot-scope="data">
      <div class="single-line">
        <span>
          <j-layer-viewer-icon span_style="margin-right: 4px" :icon="data.item.icon" :icons="icons" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
          {{ data.item.label }}
        </span>
      </div>
    </template>
   </v-select>
  </v-row>
 </div>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'label', 'hint', 'rules', 'icons', 'show_if_single_entry', 'multiselect',
          'api_hint', 'api_hints_enabled', 'disable_persistent_hint'
  ]
};
</script>

<style scoped>
  .v-select__selections {
    flex-wrap: nowrap !important;
    display: block !important;
    margin-bottom: -32px;
  }
  .single-line {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
  }
</style>
