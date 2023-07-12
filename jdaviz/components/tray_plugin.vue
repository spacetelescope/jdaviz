<template>
  <v-container class="tray-plugin" style="padding-left: 24px; padding-right: 24px; padding-top: 12px">
    <v-row>
      <div style="width: calc(100% - 32px)">
        <j-docs-link :link="link">{{ description }}</j-docs-link>
      </div>
      <div style="width: 32px">
        <j-plugin-popout :popout_button="popout_button"></j-plugin-popout>
      </div>
    </v-row>
    
    <v-row v-if="isDisabled()">
      <span> {{ getDisabledMsg() }}</span>
    </v-row>
    <div v-else>
      <v-row v-if="has_previews">
        <v-switch
          v-model="persistent_previews"
          @change="$emit('update:persistent_previews', $event)"
          label="persistent live-preview"
          hint="show live-preview even when plugin is not opened"
          persistent-hint>
        </v-switch>
      </v-row>
      <slot></slot>
    </div>
  </v-container>
</template>

<script>
module.exports = {
  props: ['disabled_msg', 'description', 'link', 'popout_button',
          'has_previews', 'plugin_ping', 'persistent_previews'],
  methods: {
    isDisabled() {
      return this.getDisabledMsg().length > 0
    },
    getDisabledMsg() {
      return this.disabled_msg || ''
    },
    sendPing() {
      if (!this.$el.isConnected) {
        return
      }
      this.$emit('update:plugin_ping', Date.now())
      setTimeout(() => {
        this.sendPing()
      }, 100)  // ms
    }
  },
  mounted() {
    this.sendPing();
  },
};
</script>

<style scoped>
  .row {
    margin-bottom: 12px !important;
  }

  .row-min-bottom-padding {
    margin-bottom: 4px !important;
  }

  .row-no-outside-padding .col:first-of-type {
    padding-left: 0px !important;
  }

  .row-no-vertical-padding-margin {
    padding-top: 0px !important;
    padding-bottom: 0px !important;
    margin-bottom: 0px !important;
    margin-top: 0px !important;
  }

  .row-no-outside-padding .col:last-of-type {
    padding-right: 0px !important;
  }

  .row-no-padding > .col {
    padding-left: 0px !important;
    padding-right: 0px !important;
  }

  .v-expansion-panel-header {
    /* tighten default padding on any sub expansion headers */
    padding: 6px !important;
  }
  
  .v-expansion-panel-header .row {
    /* override margin from above and replace with equal top and bottom margins
    for the text in the panel header */
    margin-top: 2px !important;
    margin-bottom: 2px !important;
  }
</style>
