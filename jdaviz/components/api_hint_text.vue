<template>
  <span class="api-hint">
    <template v-for="parts in [segments()]" :key="0">
      <slot v-if="parts === null"></slot>
      <template v-else>
        <template v-for="(part, i) in parts" :key="i"><wbr v-if="i > 0">{{ part }}</template>
      </template>
    </template>
  </span>
</template>

<script>
export default {
  methods: {
    segments() {
      if (!this.$slots.default) {
        return [];
      }
      const text = this.collectText(this.$slots.default());
      return text === null ? null : this.splitHint(text);
    },
    collectText(vnodes) {
      // returns null if the slot contains anything other than plain text
      let text = '';
      for (const vnode of vnodes) {
        if (vnode == null || typeof vnode === 'boolean') {
          continue;
        }
        if (typeof vnode === 'string' || typeof vnode === 'number') {
          text += vnode;
        } else if (vnode.type === Symbol.for('v-cmt')) {
          continue;
        } else if (vnode.type === Symbol.for('v-txt')) {
          text += vnode.children;
        } else if (vnode.type === Symbol.for('v-fgt') && Array.isArray(vnode.children)) {
          const inner = this.collectText(vnode.children);
          if (inner === null) {
            return null;
          }
          text += inner;
        } else {
          return null;
        }
      }
      return text;
    },
    splitHint(text) {
      // break after '.', '(', '[', ',' and '/' (but not within decimals); fall back to '_' for long chunks
      return text
        .split(/(?<=\.)(?!\d)|(?<=[(\[,/])/)
        .flatMap((part) => part.length > 20 ? part.split(/(?<=[A-Za-z0-9]_)(?=[A-Za-z0-9])/) : [part]);
    },
  },
};
</script>
