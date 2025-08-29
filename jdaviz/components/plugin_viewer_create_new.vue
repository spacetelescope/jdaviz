<template>
  <div>
  <span v-if="api_hints_enabled" class="api-hint" style="margin-left: -12px">
    {{(api_hint.endsWith(' = ') ? api_hint.slice(0, -3) : api_hint)}}.create_new = '{{ create_new_selected }}'
  </span>
  <div v-if="create_new_selected.length > 0">
    <plugin-auto-label
      :value="new_label_value"
      @change="$emit('update:new_label_value', $event)"
      @update:value="$emit('update:new_label_value', $event)"
      :default="new_label_default"
      :auto="new_label_auto"
      @update:auto="$emit('update:new_label_auto', $event)"
      :invalid_msg="new_label_invalid_msg"
      :label="'New ' + create_new_selected + ' Viewer Label'"
      :api_hint="(api_hint.endsWith(' = ') ? api_hint.slice(0, -3) : api_hint) + '.new_label ='"
      :api_hints_enabled="api_hints_enabled"
      :hint="'Label for the newly created ' + create_new_selected + ' viewer.'"
    >
      <j-tooltip tooltipcontent="Cancel creating new viewer">
        <v-btn icon @click="$emit('update:create_new_selected', '')"><v-icon>mdi-close</v-icon></v-btn>
      </j-tooltip>
    </plugin-auto-label>
  </div>
  <div v-else>
    <div>
      <v-row v-if="show_multiselect_toggle && api_hints_enabled && api_hint_multiselect">
        <span :class="api_hints_enabled && api_hint_multiselect ? 'api-hint' : null">
          {{  api_hint_multiselect }} {{  multiselect ? 'True' : 'False' }}
        </span>
      </v-row>
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
    <v-row v-if="items.length > 1 || selected.length===0 || show_if_single_entry || api_hints_enabled">
      <v-select
        :menu-props="{ left: true, top: true, maxHeight: 300 }"
        attach
        :items="items"
        v-model="selected"
        @change="$emit('update:selected', $event)"
        :class="api_hints_enabled && api_hint ? 'api-hint' : null"
        :label="api_hints_enabled && api_hint ? api_hint : (label ? label : 'Viewer')"
        :hint="hint ? hint : 'Select viewer.'"
        :rules="rules ? rules : []"
        :multiple="multiselect"
        :chips="multiselect && !api_hints_enabled"
        item-text="label"
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
              <j-layer-viewer-icon v-if="item.icon" :icon="item.icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
              {{ item.label }}
            </span>
          </v-chip>
          <span v-else >
            <j-layer-viewer-icon v-if="item.icon" span_style="margin-right: 4px" :icon="item.icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
            {{ item.label }}
          </span>
        </div>
      </template>
      <template v-slot:prepend-item>
        <v-list-item
          v-for="create_new_item in create_new_items"
          ripple
          @mousedown.prevent
          @click="() => {$emit('update:create_new_selected', create_new_item.label)}"
        >
          <v-list-item-action>
            <v-icon>
              mdi-plus-box-outline
            </v-icon>
          </v-list-item-action>
          <v-list-item-content>
            <v-list-item-title>
              Create {{ create_new_item.label }} Viewer...
            </v-list-item-title>
          </v-list-item-content>
        </v-list-item>
        <v-list-item
          v-if="multiselect && items.length > 0"
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
            <j-layer-viewer-icon span_style='margin-right: 4px' :icon="data.item.icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
            {{ data.item.label }}
          </span>
        </div>
      </template>
    </v-select>
    </v-row>
  </div>
  </div>
  </div>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'label', 'hint', 'rules', 'show_if_single_entry', 'multiselect',
          'create_new_items', 'create_new_selected',
          'new_label_value', 'new_label_default', 'new_label_auto', 'new_label_invalid_msg',
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
