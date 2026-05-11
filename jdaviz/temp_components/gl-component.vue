<template>
  <div style="display: none">
    <div ref="markerEl" :data-jdz-gl-node-id="nodeId"></div>
    <Teleport v-if="teleportTarget" :to="teleportTarget">
      <div class="gl-vue-content">
        <slot />
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { Teleport, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  tabId: { type: [String, Number], default: undefined },
  id: { type: [String, Number], default: undefined },
  closable: { type: Boolean, default: true },
  reorderEnabled: { type: Boolean, default: true },
  size: { type: [String, Number], default: undefined },
  minSize: { type: [String, Number], default: undefined },
  width: { type: [String, Number], default: undefined },
  height: { type: [String, Number], default: undefined },
})

const emit = defineEmits(['resize', 'destroy'])

let layoutContext = null
const nodeId = `gl-component-${Math.random().toString(36).slice(2)}`
const markerEl = ref(null)
const teleportTarget = ref(null)

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
    kind: 'component',
    order: layoutContext.nextOrder(),
    setTarget(target) {
      teleportTarget.value = target
    },
    emitResize(payload) {
      emit('resize', payload)
    },
    emitDestroy(payload) {
      emit('destroy', payload)
    },
    getConfig() {
      const tabId = props.tabId !== undefined && props.tabId !== null ? String(props.tabId) : null
      const fallbackId = props.id !== undefined && props.id !== null ? String(props.id) : null

      const config = {
        type: 'component',
        componentType: '__jdz_gl_component__',
        componentState: { __nodeId: nodeId },
        title: props.title || tabId || fallbackId || '',
        isClosable: props.closable,
        reorderEnabled: props.reorderEnabled,
      }

      if (tabId) {
        config.id = tabId
      } else if (fallbackId) {
        config.id = fallbackId
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
  teleportTarget.value = null
})

watch(
  () => [props.title, props.tabId, props.id, props.closable, props.reorderEnabled, props.size, props.minSize, props.width, props.height],
  () => {
    layoutContext && layoutContext.touch()
  },
)
</script>

<style>
.gl-vue-content {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
}
</style>
