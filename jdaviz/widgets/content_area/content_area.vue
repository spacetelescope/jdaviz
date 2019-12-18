<template>
  <v-content>
    <v-container
      fluid
      class="fill-height py-0"
    >
      <v-row
        align="center"
        justify="center">
        <v-col
          class="center fill-height pa-0">
          <golden-layout style="height: 100vh">
            <gl-row>
              <gl-stack>
                <gl-component
                        title="component2"
                        v-for="(viewer, i) in active_viewers"
                        @resize="on_component_resized"
                >
                  <component v-bind:is="viewer.binding"></component>
                </gl-component>
              </gl-stack>
            </gl-row>
          </golden-layout>
        </v-col>
      </v-row>
    </v-container>
  </v-content>
</template>
