<template>
  <div>
    <j-flex-row v-if="show_multiselect_toggle && api_hints_enabled && api_hint_multiselect">
      <span :class="api_hints_enabled && api_hint_multiselect ? 'api-hint' : null">
        {{  api_hint_multiselect }} {{  multiselect ? 'True' : 'False' }}
      </span>
    </j-flex-row>
    <div v-if="show_multiselect_toggle" style="position: absolute; width: 32px; right: 0px; margin-right: 12px; margin-top: -6px; z-index: 999">
    <j-tooltip tipid='viewer-multiselect-toggle'>
      <v-btn
        icon
        style="opacity: 0.7"
        @click="$emit('update:multiselect', !multiselect)"
      >
        <img :src="multiselect ? icon_checktoradial : icon_radialtocheck" width="24" class="invert-if-dark"/>
      </v-btn>
    </j-tooltip>
  </div>
  <j-flex-row v-if="items.length> 1 || selected.length===0 || show_if_single_entry || api_hints_enabled">
    <v-select
      :menu-props="{ left: true }"
      attach
      :items="items"
      :model-value="selected"
      @update:modelValue="$emit('update:selected', $event)"
      :class="api_hints_enabled && api_hint ? 'api-hint' : null"
      :label="api_hints_enabled && api_hint ? api_hint : (label ? label : 'Viewer')"
      :hint="hint ? hint : 'Select viewer.'"
      :rules="rules ? rules : []"
      :multiple="multiselect"
      :chips="multiselect && !api_hints_enabled"
      item-title="label"
      item-value="label"
      persistent-hint
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
        <v-chip v-else-if="multiselect" style="width: calc(100% - 20px)">
          <span>
            <j-layer-viewer-icon v-if="item.raw.icon" :icon="item.raw.icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
            {{ item.raw.label }}
          </span>
        </v-chip>
        <span v-else >
          <j-layer-viewer-icon v-if="item.raw.icon" span_style="margin-right: 4px" :icon="item.raw.icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
          {{ item.raw.label }}
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
        <div class="v-list-item-content">
          <v-list-item-title>
            {{ selected.length < items.length ? "Select All" : "Clear All" }}
          </v-list-item-title>
        </div>
      </v-list-item>
      <v-divider class="mt-2"></v-divider>
    </template>
    <template #item="{ props, item }">
      <v-list-item v-bind="props" :title="undefined" class="single-line">
        <span>
          <j-layer-viewer-icon v-if="item.raw.icon" span_style='margin-right: 4px' :icon="item.raw.icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
          {{ item.raw.label }}
        </span>
      </v-list-item>
    </template>
   </v-select>
  </j-flex-row>
 </div>
</template>

<script>
export default {
  props: ['items', 'selected', 'label', 'hint', 'rules', 'show_if_single_entry', 'multiselect',
          'show_multiselect_toggle', 'icon_checktoradial', 'icon_radialtocheck',
          'api_hint', 'api_hint_multiselect', 'api_hints_enabled']
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
