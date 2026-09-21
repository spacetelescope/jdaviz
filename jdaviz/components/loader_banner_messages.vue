<template>
  <div v-if="items.length > 0" style="margin-top: 12px">
    <j-flex-row v-for="(item, index) in items" :key="index">
      <v-alert :type="item.color" dense>
        {{ item.text }}
      </v-alert>
    </j-flex-row>
  </div>
</template>

<script>

export default {
  props: {
    items: {
      type: Array,
      default: () => [],
    },
  },
};
</script>
