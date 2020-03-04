<template>
  <golden-layout
    class="fill-height"
    style="width: 100%"
    :showPopoutIcon="false"
    :showMaximiseIcon="false"
    :showCloseIcon="false"
    @state="(e) => console.log(e)"
  >
    <gl-stack>
      <gl-component title="Data">
        <v-list dense>
          <v-list-item link>
            <v-list-item-action>
              <v-icon>mdi-home</v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>Home</v-list-item-title>
            </v-list-item-content>
          </v-list-item>
          <v-list-item link>
            <v-list-item-action>
              <v-icon>mdi-contact-mail</v-icon>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title>Contact</v-list-item-title>
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </gl-component>
    </gl-stack>
  </golden-layout>
</template>