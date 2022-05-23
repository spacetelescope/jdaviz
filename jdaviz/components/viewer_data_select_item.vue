<template>
  <div style="display: contents">
    <j-tooltip :tipid="multi_select ? 'viewer-data-select' : 'viewer-data-radio'">
      <v-btn 
        icon
        :color="isSelected ? 'accent' : 'default'"
        @click="$emit('data-item-selected', {
          id: viewer.id,
          item_id: item.id,
          checked: !isSelected,
          replace: !multi_select
        })">
          <v-icon v-if="multi_select">{{isSelected ? "mdi-checkbox-marked" : "mdi-checkbox-blank-outline"}}</v-icon>
          <v-icon v-else>{{isSelected ? "mdi-radiobox-marked" : "mdi-radiobox-blank"}}</v-icon>
      </v-btn>
    </j-tooltip>

    <span style="overflow-wrap: anywhere; font-size: 12pt; padding-top: 6px; padding-left: 6px">
      {{item.name}}
    </span>

    <div v-if="isDeletable" style="position: absolute; right: 10px">
      <j-tooltip tipid='viewer-data-delete'>
        <v-btn
          icon
          @click="$emit('data-item-remove', {item_name: item.name})"
        ><v-icon>mdi-delete</v-icon></v-btn>
      </j-tooltip>
    </div>
  </div>
</template>

<script>

module.exports = {
  props: ['item', 'multi_select', 'viewer'],
  computed: {
    isSelected() {
      return this.$props.viewer.selected_data_items.includes(this.$props.item.id)
    }, 
    isDeletable() {
      // only allow deleting products from plugins.  We might want to allow some non-plugin
      // data to also be deleted in the future, but would probably need more advanced logic
      // to ensure essential data isn't removed that would break the app.
      if (this.$props.item.meta.Plugin === undefined) {
        return false
      }
      // for any exceptions not above, enable deleting
      return true
    },
  }
};
</script>
