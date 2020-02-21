<template>
  <v-app id="web-app">
    <div v-if="loadRemoteCSS()"></div>

    <v-navigation-drawer v-model="drawer" app>
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
    </v-navigation-drawer>

    <v-app-bar flat dense app color="indigo" dark>
      <v-app-bar-nav-icon @click.stop="drawer = !drawer" />
      <v-toolbar-title>Application</v-toolbar-title>
    </v-app-bar>

    <v-content>
      <v-container class="fill-height pa-0" fluid>
        <v-row align="center" justify="center" class="fill-height pa-0 ma-0" >
          <v-col cols="12" class="fill-height pa-0 ma-0">
            <golden-layout class="fill-height">
              <gl-row>
                <gl-component title="component1" class="fill-height">
                  <h1>Component 1</h1>
                </gl-component>
                <gl-stack>
                  <gl-component title="component2" class="fill-height">
                    <h1>Component 2</h1>
                  </gl-component>
                  <gl-component title="component3" class="fill-height">
                    <h1>Component 3</h1>
                  </gl-component>
                </gl-stack>
              </gl-row>
            </golden-layout>
          </v-col>
        </v-row>
      </v-container>
    </v-content>
  </v-app>
</template>
