<template>
  <v-row v-if="items.length > 1 || selected.length===0 || show_if_single_entry || api_hints_enabled">
    <v-select
      :menu-props="{ left: true }"
      attach
      :items="items"
      v-model="selected"
      @change="$emit('update:selected', $event)"
      :label="api_hints_enabled && api_hint ? api_hint : label"
      :class="api_hints_enabled && api_hint ? 'api-hint' : null"
      :hint="hint"
      :rules="rules ? rules : []"
      :multiple="multiselect"
      :chips="multiselect && !api_hints_enabled"
      :disabled="disabled"
      :dense="dense"
      item-text="label"
      item-value="label"
      persistent-hint
      style="width: 100%"
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
              {{ item }}
            </span>
          </v-chip>
          <span v-else>
            {{ item }}
          </span>
        </div>
      </template>
      <template v-slot:prepend-item v-if="multiselect">
        <v-list-item
        ripple
        @mousedown.prevent
        @click="() => {if (selected.length < items.length) { $emit('update:selected', items.map((item) => {item.label || item.text}))} else {$emit('update:selected', [])}}"
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
      <template v-slot:item="{ item }">
        <span style="margin-top: 8px; margin-bottom: 0px">
          {{ item }}
        </span>
      </template>
    </v-select>
    <slot> </slot>
  </v-row>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'label', 'hint', 'rules', 'show_if_single_entry', 'multiselect',
          'api_hint', 'api_hints_enabled', 'dense', 'disabled']
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
