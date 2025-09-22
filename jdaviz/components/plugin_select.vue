<template>
  <v-row v-if="items.length > 1 || selected.length===0 || show_if_single_entry || api_hints_enabled">
    <v-select
      :menu-props="{ left: true }"
      attach
      :items="filtered_items"
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
      :search-input="search_enabled ? search_query : undefined"
      @update:search-input="on_search_input"
    >
      <template #prepend-item>
        <div v-if="search_enabled">
          <v-text-field
            v-model="search_query"
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
            @click="toggle_select_all"
          >
            <v-list-item-action>
              <v-icon>
                {{ selected.length === items.length ? 'mdi-close-box' : selected.length ? 'mdi-minus-box' : 'mdi-checkbox-blank-outline' }}
              </v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>
                <template v-if="search_enabled && search_query">
                  {{ selected.length < filtered_items.length ? 'Select All from Search' : 'Clear All from Search' }}
                </template>
                <template v-else>
                  {{ selected.length < items.length ? 'Select All' : 'Clear All' }}
                </template>
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
      search_query: '',
    }
  },
  computed: {
    search_enabled() {
      return !!this.search;
    },
    filtered_items() {
      if (!this.search_enabled || !this.search_query) {
        return this.items;
      }
      const query = this.search_query.toLowerCase().trim();
      const selected_set = new Set(
        Array.isArray(this.selected) ? this.selected.map(sel => (typeof sel === 'string' ? sel : sel.label || sel.text || sel)) : [this.selected]
      );
      let filtered;
      // Wildcard matching: if query contains * or ?
      if (/[*?]/.test(query)) {
        // Escape regex special chars except * and ?
        let regex_str = query.replace(/([.+^${}()|\[\]\\])/g, '\$1');
        regex_str = regex_str.replace(/\*/g, '.*').replace(/\?/g, '.');
        // Remove ^ and $ anchors for partial match
        const regex = new RegExp(regex_str, 'i');
        filtered = this.items.filter(item => {
          const label = (typeof item === 'string') ? item : (item.label || item.text || '');
          return regex.test(label);
        });
      } else {
        filtered = this.items.filter(item => {
          const label = (typeof item === 'string') ? item : (item.label || item.text || '');
          return label.toLowerCase().includes(query);
        });
      }
      // Add back any selected items not in filtered
      const all_labels = new Set(filtered.map(item => (typeof item === 'string' ? item : item.label || item.text || '')));
      this.items.forEach(item => {
        const label = (typeof item === 'string') ? item : (item.label || item.text || '');
        if (selected_set.has(label) && !all_labels.has(label)) {
          filtered.push(item);
        }
      });
      return filtered;
    },
  },
  methods: {
    on_search_input(value) {
      this.search_query = value;
    },
    toggle_select_all() {
      if (this.search_enabled && this.search_query) {
        // When search is active, select/clear only filtered items
        const filtered_labels = this.filtered_items.map(item => item.label || item.text || item);
        const selected_set = new Set(this.selected);
        if (filtered_labels.some(label => !selected_set.has(label))) {
          // Select all filtered items (add to selection)
          let new_selected = Array.isArray(this.selected) ? [...this.selected] : [];
          filtered_labels.forEach(label => {
            if (!selected_set.has(label)) {
              new_selected.push(label);
            }
          });
          this.$emit('update:selected', new_selected);
        } else {
          // Clear all filtered items from selection
          let new_selected = Array.isArray(this.selected) ? this.selected.filter(label => !filtered_labels.includes(label)) : [];
          this.$emit('update:selected', new_selected);
        }
      } else {
        // No search: select/clear all items
        if (this.selected.length < this.items.length) {
          this.$emit('update:selected', this.items.map(item => item.label || item.text || item));
        } else {
          this.$emit('update:selected', []);
        }
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
