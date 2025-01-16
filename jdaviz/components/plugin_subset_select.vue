<template>
  <div>
  <v-row v-if="items.length > 1 || selected.length===0 || show_if_single_entry || api_hints_enabled">
    <v-select
      v-if="!rename_mode"
      :menu-props="{ left: true }"
      attach
      :items="items"
      v-model="selected"
      @change="$emit('update:selected', $event)"
      :label="api_hints_enabled && api_hint ? api_hint : (label ? label : 'Subset')"
      :class="api_hints_enabled && api_hint ? 'api-hint' : null"
      :hint="hint ? hint : 'Select subset.'"
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
          <v-chip v-else-if="multiselect" style="width: calc(100% - 10px)">
            <span>
              <v-icon v-if="item.color" left :color="item.color">
                {{ item.type=='spectral' ? 'mdi-chart-bell-curve' : 'mdi-chart-scatter-plot' }}
              </v-icon>
              {{ item.label }}
            </span>
          </v-chip>
          <span v-else>
            <v-icon v-if="item.color" left :color="item.color">
              {{ item.type=='spectral' ? 'mdi-chart-bell-curve' : 'mdi-chart-scatter-plot' }}
            </v-icon>
            {{ item.label }}
          </span>
        </div>
      </template>
      <template v-slot:append v-if="selected !== 'Create New'">
        <v-icon style="cursor: pointer">mdi-menu-down</v-icon>
        <j-tooltip tooltipcontent="rename" v-if="api_hint_rename">
          <v-icon style="cursor: pointer" @click="() => {rename_new_label = selected; rename_mode = true}">mdi-pencil</v-icon>
        </j-tooltip>
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
          <v-icon v-if="data.item.color" left :color="data.item.color">
            {{ data.item.type=='spectral' ? 'mdi-chart-bell-curve' : 'mdi-chart-scatter-plot' }}
          </v-icon>
          <span>
            {{ data.item.label }}
          </span>
        </div>
      </template>
    </v-select>
    <v-text-field
      v-if="rename_mode"
      v-model="rename_new_label"
      :label="textFieldLabel"
      :class="textFieldClass"
      hint="Rename subset."
      persistent-hint
    >
      <template v-slot:append>
        <j-tooltip v-if="items.length > 0" tooltipcontent="Cancel change">
          <v-icon style="cursor: pointer" @click="() => {rename_new_label = ''; rename_mode = false}">mdi-close</v-icon>
        </j-tooltip>
        <j-tooltip tooltipcontent="Accept change">
          <v-icon style="cursor: pointer" @click="() => {$emit('rename-subset', {'old_label': selected, 'new_label': rename_new_label}); rename_mode = false}">mdi-check</v-icon>
        </j-tooltip>
      </template>
    </v-text-field>
  </v-row>
  <v-row v-if="has_subregions_warning && has_subregions">
    <span class="v-messages v-messages__message text--secondary" style="color: red !important">
        {{ has_subregions_warning }}
    </span>
  </v-row>
  </div>
</template>

<script>
module.exports = {
  data: function () {
    return {
      rename_mode: false,
      rename_new_label: ''
    }
  },
  props: ['items', 'selected', 'label', 'has_subregions', 'has_subregions_warning', 'hint', 'rules', 'show_if_single_entry', 'multiselect',
          'api_hint', 'api_hints_enabled', 'api_hint_rename'
  ],
  computed: {
    textFieldLabel() {
      if (this.api_hints_enabled && this.rename_mode && this.api_hint_rename) {
        return this.api_hint_rename+'(\''+this.selected+'\', \''+this.rename_new_label+'\')';
      } else {
        return this.label || 'Subset';
      }
    },
    textFieldClass() {
      if (this.api_hints_enabled && this.rename_mode && this.api_hint_rename) {
        return 'api-hint';
      } else {
        return null;
      }
    }
  }
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
