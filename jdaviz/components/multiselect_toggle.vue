<template>
  <div>
    <v-row>
      <div style="width: calc(100% - 32px)">
      </div>
      <div style="width: 32px">
        <j-tooltip :tooltipcontent="tooltip || 'Toggle multiselect'">
          <v-btn
            icon
            style="opacity: 0.7"
            @click="() => $emit('update:multiselect', !multiselect)"
          >
            <img :src="multiselect ? icon_checktoradial : icon_radialtocheck" width="24" class="invert-if-dark"/>
          </v-btn>
        </j-tooltip>
      </div>
    </v-row>
  </div>
</template>

<script>
module.exports = {
  props: ['multiselect', 'icon_checktoradial', 'icon_radialtocheck', 'tooltip']
};
</script>

<style scoped>
</style>
