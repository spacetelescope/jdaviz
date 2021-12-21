<template>
  <div class="v-messages">
    <div class="v-messages__wrapper" style="margin-top: 2px; margin-bottom: 2px">
      <div class="v-messages__message text--secondary" style="margin-bottom: 8px">
          <slot></slot>
        <div v-if="link">
          <j-external-link :link="link" :linktext="linktext"/>
        </div>
      </div>
    </div>
    <div v-if="divider" style="margin-bottom: 12px">
      <v-divider></v-divider>
    </div>
  </div>
</template>

<script>
module.exports = {
  props: {link: String, 
          linktext: String, 
          divider: Boolean
        },
};
</script>
