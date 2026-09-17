<template>
  <div ref="markerEl" :data-jdz-gl-node-id="nodeId" style="display: none">
    <slot />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  closable: { type: Boolean, default: true },
  id: { type: [String, Number], default: undefined },
  size: { type: [String, Number], default: undefined },
  minSize: { type: [String, Number], default: undefined },
  width: { type: [String, Number], default: undefined },
  height: { type: [String, Number], default: undefined },
})

let layoutContext = null
const nodeId = `gl-row-${Math.random().toString(36).slice(2)}`
const markerEl = ref(null)

let unregister = null

function isNumberLike(value) {
  return value !== null && value !== undefined && value !== ''
}

function normalizeSize(value, defaultUnit) {
  if (!isNumberLike(value)) {
    return null
  }

  const text = String(value).trim()
  if (/^-?\d+(\.\d+)?(fr|%|px)$/.test(text)) {
    return text
  }

  const numberValue = Number(text)
  if (!Number.isFinite(numberValue)) {
    return null
  }

  return `${numberValue}${defaultUnit}`
}

function resolveParentNodeId() {
  let current = markerEl.value ? markerEl.value.parentElement : null
  while (current) {
    const candidate = current.getAttribute && current.getAttribute('data-jdz-gl-node-id')
    if (candidate) {
      return candidate
    }
    current = current.parentElement
  }
  return null
}

function resolveLayoutContext() {
  if (typeof window === 'undefined') {
    return null
  }

  const registry = window.__jdz_gl_layout_contexts__
  if (!registry) {
    return null
  }

  let current = markerEl.value
  while (current) {
    const layoutId = current.getAttribute && current.getAttribute('data-jdz-gl-layout-id')
    if (layoutId && registry[layoutId]) {
      return registry[layoutId]
    }
    current = current.parentElement
  }

  return null
}

onMounted(() => {
  layoutContext = resolveLayoutContext()
  if (!layoutContext) {
    return
  }

  unregister = layoutContext.registerNode({
    id: nodeId,
    parentId: resolveParentNodeId(),
    kind: 'row',
    order: layoutContext.nextOrder(),
    getConfig(children) {
      const config = {
        type: 'row',
        content: children,
        isClosable: props.closable,
      }

      if (props.id !== undefined && props.id !== null) {
        config.id = String(props.id)
      }
      const normalizedSize = normalizeSize(props.size, '%')
      if (normalizedSize) {
        config.size = normalizedSize
      }
      const normalizedMinSize = normalizeSize(props.minSize, 'px')
      if (normalizedMinSize) {
        config.minSize = normalizedMinSize
      }
      if (isNumberLike(props.width)) {
        config.width = Number(props.width)
      }
      if (isNumberLike(props.height)) {
        config.height = Number(props.height)
      }

      return config
    },
  })
})

onBeforeUnmount(() => {
  if (unregister) {
    unregister()
    unregister = null
  }
})

watch(
  () => [props.closable, props.id, props.size, props.minSize, props.width, props.height],
  () => {
    layoutContext && layoutContext.touch()
  },
)
</script>
