<template>
  <v-toolbar-items>
    <v-btn tile depressed color="accent" @click="onClicked">
      Import
      <v-icon right>mdi-plus</v-icon>
    </v-btn>
    <g-file-import v-show=false id="file-uploader"></g-file-import>
  </v-toolbar-items>
</template>

<script>
    module.exports = {
        name: "g-file-import",
        props: [],

        methods: {
            onClicked(event) {
                let uploadButton = document.getElementById("file-uploader").firstElementChild;
                uploadButton.click();
            },
        },
    };
</script>
