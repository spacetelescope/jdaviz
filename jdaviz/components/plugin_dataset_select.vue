<template>
  <v-row v-if="items.length > 1 || selected.length===0 || show_if_single_entry || api_hints_enabled">
    <v-select
      :menu-props="{ left: true }"
      attach
      :items="items"
      v-model="selected"
      @change="$emit('update:selected', $event)"
      :class="api_hints_enabled && api_hint ? 'api-hint' : null"
      :label="api_hints_enabled && api_hint ? api_hint : (label ? label : 'Data')"
      :hint="hint ? hint : 'Select data.'"
      :rules="rules ? rules : []"
      :multiple="multiselect"
      :chips="multiselect"
      :disabled="disabled"
      item-text="label"
      item-value="label"
      persistent-hint
    >
      <template slot="selection" slot-scope="data">
        <div class="single-line" style="width: 100%">
          <v-chip v-if="multiselect" style="width: calc(100% - 10px)">
            <span>
              <j-layer-viewer-icon v-if="data.item.icon" span_style="margin-right: 4px" :icon="data.item.icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
              {{ data.item.label }}
            </span>
          </v-chip>
          <span v-else :class="api_hints_enabled ? 'api-hint' : null">
            <j-layer-viewer-icon v-if="data.item.icon && !api_hints_enabled" span_style="margin-right: 4px" :icon="data.item.icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
            {{ api_hints_enabled ?
              '\'' + data.item.label + '\''
              :
              data.item.label
            }}
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
            <j-layer-viewer-icon v-if="data.item.icon" span_style="margin-right: 4px" :icon="data.item.icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
            {{ data.item.label }}
          </span>
        </div>
      </template>
   </v-select>
  </v-row>
</template>
<script>
module.exports = {
  props: ['items', 'selected', 'label', 'hint', 'rules', 'show_if_single_entry', 'multiselect',
          'api_hint', 'api_hints_enabled', 'disabled']
}
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
