<template>
  <span>
    <a :href="link" target="__blank" :style="{color: themeAccentColor}">
      <b>{{ linktext || "Learn More" }}</b>
      <v-icon x-small :color="themeAccentColor">mdi-open-in-new</v-icon>
    </a>
    
  </span>
</template>

<script>
module.exports = {
  props: {link: String, 
          linktext: String
        },
  computed: {
    themeAccentColor() {
      return this.$vuetify.theme.dark ? this.$vuetify.theme.themes.dark.accent : this.$vuetify.theme.themes.light.accent;
    }
  }
};
</script>
