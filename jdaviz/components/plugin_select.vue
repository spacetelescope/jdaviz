<template>
  <v-row v-if="items.length > 1 || selected.length===0 || show_if_single_entry || api_hints_enabled">
    <v-select
      :menu-props="{ left: true }"
      attach
      :items="filteredItems"
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
      :search-input="searchEnabled ? searchQuery : undefined"
      @update:search-input="onSearchInput"
    >
      <template #prepend-item>
        <div v-if="searchEnabled">
          <v-text-field
            v-model="searchQuery"
            prepend-inner-icon="mdi-magnify"
            label="Search"
            single-line
            hide-details
            autofocus
            style="margin: 8px;"
          />
          <v-divider class="mt-2"></v-divider>
        </div>
        <div v-if="multiselect">
          <v-list-item
            ripple
            @mousedown.prevent
            @click="toggleSelectAll"
          >
            <v-list-item-action>
              <v-icon>
                {{ selected.length === items.length ? 'mdi-close-box' : selected.length ? 'mdi-minus-box' : 'mdi-checkbox-blank-outline' }}
              </v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>
                {{ selected.length < items.length ? 'Select All' : 'Clear All' }}
              </v-list-item-title>
            </v-list-item-content>
          </v-list-item>
          <v-divider class="mt-2"></v-divider>
        </div>
      </template>
      <template #selection="{ item, index }">
        <div class="single-line" style="width: 100%">
          <span v-if="api_hints_enabled && index === 0" class="api-hint">
            {{ multiselect ? selected : `'${selected}'` }}
          </span>
          <v-chip v-else-if="multiselect" style="width: calc(100% - 10px)">
            <span>{{ item }}</span>
          </v-chip>
          <span v-else>{{ item }}</span>
        </div>
      </template>
      <template #item="{ item }">
        <span style="margin-top: 8px; margin-bottom: 0px">
          {{ typeof item === 'string' ? item : (item.label || item.text) }}
        </span>
      </template>
    </v-select>
    <slot> </slot>
  </v-row>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'label', 'hint', 'rules', 'show_if_single_entry', 'multiselect',
          'api_hint', 'api_hints_enabled', 'dense', 'disabled', 'search'],
  data() {
    return {
      searchQuery: '',
    }
  },
  computed: {
    searchEnabled() {
      return !!this.search;
    },
    filteredItems() {
      if (!this.searchEnabled || !this.searchQuery) {
        return this.items;
      }
      const query = this.searchQuery.toLowerCase();
      // Get selected items (as objects or strings)
      const selectedSet = new Set(
        Array.isArray(this.selected) ? this.selected.map(sel => (typeof sel === 'string' ? sel : sel.label || sel.text || sel)) : [this.selected]
      );
      // Filter items by search
      const filtered = this.items.filter(item => {
        const label = (typeof item === 'string') ? item : (item.label || item.text || '');
        return label.toLowerCase().includes(query);
      });
      // Add back any selected items not in filtered
      const allLabels = new Set(filtered.map(item => (typeof item === 'string' ? item : item.label || item.text || '')));
      this.items.forEach(item => {
        const label = (typeof item === 'string') ? item : (item.label || item.text || '');
        if (selectedSet.has(label) && !allLabels.has(label)) {
          filtered.push(item);
        }
      });
      return filtered;
    },
  },
  methods: {
    onSearchInput(value) {
      this.searchQuery = value;
    },
    toggleSelectAll() {
      if (this.selected.length < this.items.length) {
        this.$emit('update:selected', this.items.map(item => item.label || item.text || item));
      } else {
        this.$emit('update:selected', []);
      }
    },
  },
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
