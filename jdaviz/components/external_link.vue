<template>
  <div style="margin-top: 4px">
    <a :href="link" target="__blank" style="color: #A75000">
      <b>{{ linktext || "Learn More" }}</b>
      <v-icon x-small color="#A75000">mdi-open-in-new</v-icon>
    </a>
  </div>
</template>

<script>
module.exports = {
  props: {link: String,
    linktext: String
  },
};
</script>
