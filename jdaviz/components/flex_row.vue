<template>
  <component
    :is="tag"
    v-bind="forwardedAttrs"
    :class="classes"
    :style="styles"
  >
    <slot></slot>
  </component>
</template>

<script>
export default {
  inheritAttrs: false,
  props: {
    tag: {
      type: String,
      default: 'div',
    },
    justify: {
      type: String,
      default: null,
    },
    align: {
      type: String,
      default: null,
    },
    alignContent: {
      type: String,
      default: null,
    },
    noGutters: {
      type: Boolean,
      default: false,
    },
    alignCenter: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    forwardedAttrs() {
      const attrs = { ...this.$attrs };
      delete attrs.class;
      delete attrs.style;
      return attrs;
    },
    normalizedAlign() {
      if (this.align) {
        return this.align;
      }
      if (this.alignCenter) {
        return 'center';
      }
      return null;
    },
    classes() {
      return [
        'j-flex-row',
        'd-flex',
        this.justify ? `justify-${this.justify}` : null,
        this.normalizedAlign ? `align-${this.normalizedAlign}` : null,
        this.alignContent ? `align-content-${this.alignContent}` : null,
        this.$attrs.class,
      ];
    },
    styles() {
      return [
        {
          flex: '1 1 auto',
          flexWrap: 'wrap',
          marginRight: this.noGutters ? 0 : '-12px',
          marginLeft: this.noGutters ? 0 : '-12px',
        },
        this.$attrs.style,
      ];
    },
  },
};
</script>
