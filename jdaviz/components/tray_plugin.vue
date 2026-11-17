<template>
  <v-container
    class="tray-plugin"
    style="padding-left: 24px; padding-right: 24px; padding-top: 12px" >
    <j-flex-row>
      <div style="width: calc(100% - 32px)">
        <j-docs-link :link="link">{{ description }}</j-docs-link>
      </div>

      <div style="width: 32px">
        <j-plugin-popout :popout_button="popout_button"></j-plugin-popout>
      </div>
    </j-flex-row>

    <j-flex-row v-if="isDisabled()">
      <span> {{ getDisabledMsg() }}</span>
    </j-flex-row>
    <div v-else>
      <j-flex-row v-if="uses_active_status && keep_active !== undefined" style="padding-bottom: 24px">
        <!-- TODO: update:keep_active is not working!!! -->
        <plugin-switch
          :value="keep_active"
          @update:value="$emit('update:keep_active', $event)"
          label="Keep active"
          api_hint="plg.keep_active = "
          :api_hints_enabled="api_hints_enabled"
          hint="Consider plugin active (showing any previews and enabling all keypress events) even when not opened"
        />
      </j-flex-row>

      <slot></slot>
    </div>
  </v-container>
</template>

<script>
export default {
  props: ['config', 'plugin_key', 'irrelevant_msg', 'disabled_msg', 'description',
          'api_hints_enabled', 'link', 'popout_button',
          'uses_active_status', 'keep_active', 'scroll_to'],
  methods: {
    boolToString(b) {
      if (b) {
        return 'True'
      } else {
        return 'False'
      }
    },
    isDisabled() {
      return this.getDisabledMsg().length > 0
    },
    getDisabledMsg() {
      return this.irrelevant_msg || this.disabled_msg || ''
    },
    reportVisibility(visible) {
      if (visible !== this._visible) {
        this._visible = visible
        this.$emit('plugin-visibility', {view_id: this._viewId, visible})
      }
    },
    updateVisibility() {
      if (this._disposed) {
        return
      }
      const style = this._window.getComputedStyle(this.$el)
      const visible = !this._pageHidden && !this._document.hidden
        && this.$el.isConnected && this.$el.getClientRects().length > 0
        && style.visibility !== 'hidden' && style.visibility !== 'collapse'
      this.reportVisibility(visible)
      this.scrollIfRequested()
    },
    scrollIfRequested() {
      if (this.scroll_to && this._visible) {
        this.$emit('update:scroll_to', false)
        this.$el.scrollIntoView({behavior: "smooth", block: "nearest", inline: "start"});
      }
    },
  },
  watch: {
    scroll_to() {
      this.$nextTick(() => this.scrollIfRequested())
    },
  },
  mounted() {
    this._document = this.$el.ownerDocument
    this._window = this._document.defaultView
    this._viewId = Array.from(this._window.crypto.getRandomValues(new Uint32Array(4))).join('-')
    this._visible = false
    this._pageHidden = false
    this._disposed = false
    this._onVisibilityChange = () => this.updateVisibility()
    this._onPageHide = () => {
      this._pageHidden = true
      this.updateVisibility()
    }
    this._onPageShow = () => {
      this._pageHidden = false
      this.updateVisibility()
    }
    // Notebook outputs can be detached without unmounting Vue. Also watch ancestors
    // for CSS hiding (e.g. inactive notebook/sidecar tabs), but not viewport intersection.
    this._visibilityObserver = new this._window.MutationObserver(records => {
      if (records.some(record => record.type === 'attributes'
        ? record.target.contains(this.$el)
        : [...record.addedNodes, ...record.removedNodes].some(node => node.contains(this.$el)))) {
        this.updateVisibility()
      }
    })
    this._visibilityObserver.observe(this._document.documentElement, {
      subtree: true, childList: true, attributes: true,
      attributeFilter: ['class', 'style', 'hidden'],
    })
    this._resizeObserver = new this._window.ResizeObserver(this._onVisibilityChange)
    this._resizeObserver.observe(this.$el)
    this._document.addEventListener('visibilitychange', this._onVisibilityChange)
    this._window.addEventListener('pagehide', this._onPageHide)
    this._window.addEventListener('pageshow', this._onPageShow)
    this.updateVisibility()
  },
  beforeUnmount() {
    this._disposed = true
    this.reportVisibility(false)
    this._visibilityObserver.disconnect()
    this._resizeObserver.disconnect()
    this._document.removeEventListener('visibilitychange', this._onVisibilityChange)
    this._window.removeEventListener('pagehide', this._onPageHide)
    this._window.removeEventListener('pageshow', this._onPageShow)
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

  .v-expansion-panel-title {
    /* tighten default padding on any sub expansion headers */
    padding: 6px !important;
  }

  .v-expansion-panel-title .row {
    /* override margin from above and replace with equal top and bottom margins
    for the text in the panel header */
    margin-top: 2px !important;
    margin-bottom: 2px !important;
  }
</style>
