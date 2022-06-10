<template>
  <div style="display: contents">
    <div>
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
    </div>

    <j-tooltip :tooltipcontent="'data label: '+item.name" span_style="font-size: 12pt; padding-top: 6px; padding-left: 6px; width: calc(100% - 80px); cursor: default;">
      <div class="text-ellipsis-middle">
        <span>
          {{itemNamePrefix}}
        </span>
        <span>
          {{itemNameExtension}}
        </span>
      </div>
    </j-tooltip>


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
    itemNamePrefix() {
      if (this.$props.item.name.indexOf("[") !== -1) {
        // return everything BEFORE the LAST [
        return this.$props.item.name.split('[').slice(0, -1).join()
      } else {
        return this.$props.item.name
      }
    },
    itemNameExtension() {
      if (this.$props.item.name.indexOf("[") !== -1) {
        // return the LAST [ and everything FOLLOWING
        return '['+this.$props.item.name.split('[').slice(-1)
      } else {
        return ''
      }
    },
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

<style>
  .text-ellipsis-middle {
    display: inline-flex;
    flex-wrap: nowrap;
    max-width: 100%;
  }

  .text-ellipsis-middle > span:first-child {
    flex: 0 1 auto;
    text-overflow: ellipsis;
    overflow:hidden;
    white-space:nowrap;
  }

  .text-ellipsis-middle > span + span {
    flex: 1 0 auto;
    white-space: nowrap;
  }
</style>
