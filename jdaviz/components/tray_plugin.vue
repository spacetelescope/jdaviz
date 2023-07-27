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
      <v-row v-if="uses_active_status && keep_active !== undefined">
        <v-switch
          v-model="keep_active"
          @change="$emit('update:keep_active', $event)"
          label="keep active"
          hint="consider plugin active (showing any previews and enabling all keypress events) even when not opened"
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
          'uses_active_status', 'keep_active'],
  methods: {
    isDisabled() {
      return this.getDisabledMsg().length > 0
    },
    getDisabledMsg() {
      return this.disabled_msg || ''
    },
    sendPing(recursive) {
      if (!this.$el.isConnected) {
        return
      }
      if (!document.hidden) {
        this.$emit('plugin-ping', Date.now())
      }
      if (!recursive) {
        return
      }
      setTimeout(() => {
        this.sendPing(true)          
      }, 200)  // ms
    }
  },
  mounted() {
    this.sendPing(true);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        this.sendPing(false)
      }
    });
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
