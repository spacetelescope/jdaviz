<template>
  <v-toolbar-items>
    <v-btn tile depressed color="primary" @click="onClicked">
      Import
      <div v-show=false id="file-uploader">
        <g-file-import></g-file-import>
      </div>
      <v-icon right>mdi-plus</v-icon>
    </v-btn>
  </v-toolbar-items>
</template>

<script>
  module.exports = {
    name: "g-file-import",
    props: [],

    methods: {
      onClicked(event) {
        let uploadButton = document.getElementById("file-uploader").firstElementChild.children[0];
        uploadButton.click();
      },
    },
  };
</script>
