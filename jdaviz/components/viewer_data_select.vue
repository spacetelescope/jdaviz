<template>
  <v-list style="max-height: 500px; width: 350px;" class="overflow-y-auto">
    <v-row v-for="item in data_items" :key="item.id" style="padding-left: 25px">
      <j-tooltip tipid='viewer-data-select-toggle'>
        <v-btn 
          icon
          :color="viewer.selected_data_items.includes(item.id) ? 'accent' : 'default'"
          @click="$emit('data-item-selected', {
            id: viewer.id,
            item_id: item.id,
            checked: !viewer.selected_data_items.includes(item.id)
          })">
            <v-icon>{{viewer.selected_data_items.includes(item.id) ? "mdi-eye" : "mdi-eye-off"}}</v-icon>
        </v-btn>
      </j-tooltip>

      <span class='text--primary' style="overflow-wrap: anywhere; font-size: 12pt; padding-top: 6px; padding-left: 6px">
        {{item.name}}
      </span>

      <div style="position: absolute; right: 10px">
        <j-tooltip tipid='viewer-data-select-delete'>
          <v-btn
            icon
            @click="$emit('data-item-remove', {item_name: item.name})"
          ><v-icon>mdi-delete</v-icon></v-btn>
        </j-tooltip>
      </div>
    </v-row>
  </v-list>
</template>
<script>

module.exports = {
  props: ['data_items', 'viewer'],
};
</script>
