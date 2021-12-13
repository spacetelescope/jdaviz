<template>
  <span>
    <a :href="link" target="__blank" style="color: #A75000">
      <b>{{ linktext || "Learn More" }}</b>
      <v-icon x-small color="#A75000">mdi-open-in-new</v-icon>
    </a> 
    
  </span>
</template>

<script>
module.exports = {
  props: {link: String, 
          linktext: String
        },
};
</script>
