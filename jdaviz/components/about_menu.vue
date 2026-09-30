<template>
  <v-menu
    ref="aboutMenu"
    v-model="popup_open"
    location="bottom"
    absolute
    style="max-width: 600px"
    :close-on-content-click="false"
  >
    <template v-slot:activator="{ props }">
      <j-tooltip tooltipcontent="Show app information and docs">
        <v-btn
          variant="text"
          v-bind="props"

          color="white"
          style="font-family: monospace; font-size: 10pt; text-transform: lowercase; margin-left: 4px; margin-right: 6px; padding: 2px">
        v{{ jdaviz_version }}
        <span
          v-if="downstream_packages && downstream_packages.length > 0"
          style="margin-left: 4px; border-radius: 10px; padding: 0 4px; font-size: 9pt; line-height: 1.6"
        >
          + {{ downstream_packages.length == 1 ? downstream_packages[0].abbreviation : downstream_packages.length }}
        </span>
        </v-btn>
      </j-tooltip>
    </template>

    <v-card ref="aboutContent">
      <span v-if="api_hints_enabled" class="api-hint" style="font-weight: bold; margin-left: 12px">plg = {{  api_hints_obj }}.plugins['About']</span>
      <jupyter-widget v-if="about_widget" :widget="about_widget" :key="about_widget"></jupyter-widget>
    </v-card>
  </v-menu>
</template>

<script>
  export default {
    props: ['jdaviz_version', 'api_hints_obj', 'api_hints_enabled', 'about_widget', 'force_open_about', 'downstream_packages'],
    data: function () {
      return {
        popup_open: false,
      }
    },
    async mounted() {
      // Vuetify resolves its activator element after mounting.
      await this.$nextTick();
      let element = this.$refs.aboutMenu.activatorEl
      if (!element) {
        return
      }
      while (element["tagName"] !== "BODY") {
        if (["auto", "scroll"].includes(window.getComputedStyle(element).overflowY)) {
          element.addEventListener("scroll", this.onScroll);
        }
        element = element.parentElement;
      }
      this._visibilityObserver = new IntersectionObserver(([entry]) => {
        this._activatorVisible = entry.isIntersecting && entry.intersectionRatio >= 0.01;
        this.onScroll();
      }, { threshold: 0.01 });
      this._visibilityObserver.observe(this.$refs.aboutMenu.activatorEl);
    },
    beforeUnmount() {
      this._visibilityObserver?.disconnect();
      let element = this.$refs.aboutMenu.activatorEl
      if (!element) {
        return
      }
      while (element["tagName"] !== "BODY") {
        if (["auto", "scroll"].includes(window.getComputedStyle(element).overflowY)) {
          element.removeEventListener("scroll", this.onScroll);
        }
        element = element.parentElement;
      }
    },
    methods: {
      onScroll(e) {
        if (this.popup_open && this.$refs.aboutMenu.activatorEl) {
          const menuContent = this.$refs.aboutContent?.$el;
          if (!menuContent || menuContent.parentElement === null) {
            return;
          }

          const labCellHidden = this._activatorVisible === false;
          menuContent.parentElement.style.display = labCellHidden ? "none" : "";
        }
      },
    },
    watch: {
      force_open_about: function (val) {
        if (val) {
          this.popup_open = true;
          this.$emit('update:force_open_about', false);
        }
      }
    },
  }
</script>
