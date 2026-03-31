<template>
  <v-menu
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
          id="about-scroll-target"
          v-bind="props"

          color="white"
          style="font-family: monospace; font-size: 10pt; text-transform: lowercase; margin-left: 4px; margin-right: 6px; padding: 2px">
        v{{ jdaviz_version }}
        </v-btn>
      </j-tooltip>
    </template>

    <v-card id="about-scroll-content">
      <span v-if="api_hints_enabled" class="api-hint" style="font-weight: bold">plg = {{  api_hints_obj }}.plugins['About']</span>
      <jupyter-widget v-if="about_widget" :widget="about_widget" :key="about_widget"></jupyter-widget>
    </v-card>
  </v-menu>
</template>

<script>
  export default {
    props: ['jdaviz_version', 'api_hints_obj', 'api_hints_enabled', 'about_widget', 'force_open_about'],
    data: function () {
      return {
        popup_open: false,
      }
    },
    mounted() {
      let element = document.getElementById('about-scroll-target')
      if (element === null) {
        return
      }
      while (element["tagName"] !== "BODY") {
        if (["auto", "scroll"].includes(window.getComputedStyle(element).overflowY)) {
          element.addEventListener("scroll", this.onScroll);
        }
        element = element.parentElement;
      }
      this.jupyterLabCell = this.$el.closest(".jp-Notebook-cell");
    },
    beforeUnmount() {
      let element = document.getElementById('about-scroll-target')
      if (element === null) {
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
        if (this.popup_open && document.getElementById('about-scroll-target')) {
          const top = document.getElementById('about-scroll-target').getBoundingClientRect().y + document.body.parentElement.scrollTop;
          const menuContent = document.getElementById('about-scroll-content');
          if (menuContent === null || menuContent.parentElement === null) {
            return;
          }
          menuContent.parentElement.style.top = top + "px";

          /* since Jupyter Lab 4.2 cells outside the view port get a height of 0, causing the menu to be visible when
           * that happens. This workaround hides the menu when it's parent cell is not in the viewport. */
          const labCellHidden = this.jupyterLabCell && window.getComputedStyle(this.jupyterLabCell).height === "0px";
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
