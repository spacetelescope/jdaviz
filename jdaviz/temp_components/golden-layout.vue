<template>
  <div class="gl-compat-root" :data-jdz-gl-layout-id="layoutId">
    <div ref="hostElement" class="gl-compat-canvas"></div>
    <div class="gl-compat-definitions">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { GoldenLayout as GoldenLayoutCore } from 'https://esm.sh/golden-layout@2.6.0?bundle'

const props = defineProps({
  hasHeaders: { type: Boolean, default: true },
  state: { type: Object, default: null },
})

const emit = defineEmits(['state'])

const hostElement = ref(null)
const layoutInstance = ref(null)
const nodes = new Map()
const componentNodes = new Map()
const componentNodesByConfigId = new Map()
const registryVersion = ref(0)
const layoutId = `jdz-gl-layout-${Math.random().toString(36).slice(2)}`

let orderCounter = 0
let reloadQueued = false
let lastEmittedStateHash = ''
let lastLoadedExternalStateHash = ''
let sizeObserver = null
let resizeFrame = null
let dragCleanupFrame = null

const GL_COMPONENT_TYPE = '__jdz_gl_component__'
const STALE_DRAG_PROXY_SELECTOR = 'body > .lm_dragProxy'

function getGlobalLayoutRegistry() {
  if (typeof window === 'undefined') {
    return null
  }

  if (!window.__jdz_gl_layout_contexts__) {
    window.__jdz_gl_layout_contexts__ = {}
  }

  return window.__jdz_gl_layout_contexts__
}

function safeHash(value) {
  try {
    return JSON.stringify(value)
  } catch (error) {
    return ''
  }
}

function isStateCompatible(state, componentNodeIds, componentConfigIds = new Set()) {
  if (!state || typeof state !== 'object' || !state.root) {
    return false
  }

  const walk = (item) => {
    if (!item || typeof item !== 'object') {
      return true
    }

    if (item.type === 'component') {
      const nodeId = item.componentState && item.componentState.__nodeId
      const rawId = item.id
      const configId = Array.isArray(rawId) ? (rawId.length ? String(rawId[0]) : null) : (
        rawId !== undefined && rawId !== null ? String(rawId) : null
      )
      return (
        (!!nodeId && componentNodeIds.has(String(nodeId)))
        || (!!configId && componentConfigIds.has(configId))
      )
    }

    const content = Array.isArray(item.content) ? item.content : []
    return content.every(walk)
  }

  return walk(state.root)
}

function touch() {
  registryVersion.value += 1
}

const layoutContext = {
  registerNode(node) {
    nodes.set(node.id, node)
    touch()
    return () => {
      nodes.delete(node.id)
      touch()
    }
  },
  touch,
  nextOrder() {
    orderCounter += 1
    return orderCounter
  },
}

const globalLayoutRegistry = getGlobalLayoutRegistry()
if (globalLayoutRegistry) {
  globalLayoutRegistry[layoutId] = layoutContext
}

function ensureLayout() {
  if (layoutInstance.value || !hostElement.value) {
    return
  }

  const gl = new GoldenLayoutCore(hostElement.value)

  function extractNodeId(factoryArg, container) {
    if (factoryArg && typeof factoryArg === 'object') {
      if (factoryArg.__nodeId) {
        return factoryArg.__nodeId
      }
      if (factoryArg.componentState && factoryArg.componentState.__nodeId) {
        return factoryArg.componentState.__nodeId
      }
      if (factoryArg.state && factoryArg.state.__nodeId) {
        return factoryArg.state.__nodeId
      }
    }
    if (container && container.initialState && container.initialState.__nodeId) {
      return container.initialState.__nodeId
    }
    return null
  }

  function extractConfigId(factoryArg) {
    if (!factoryArg || typeof factoryArg !== 'object') {
      return null
    }
    const rawId = factoryArg.id
    if (rawId === undefined || rawId === null) {
      return null
    }
    if (Array.isArray(rawId)) {
      return rawId.length ? String(rawId[0]) : null
    }
    return String(rawId)
  }

  gl.registerComponentFactoryFunction(GL_COMPONENT_TYPE, (container, factoryArg) => {
    const nodeId = extractNodeId(factoryArg, container)
    const configId = extractConfigId(factoryArg)
    const node = (
      (nodeId ? componentNodes.get(nodeId) : null)
      || (configId ? componentNodesByConfigId.get(configId) : null)
    )

    if (!node) {
      container.element.textContent = 'Missing component binding'
      return {
        __cleanup() {
          container.element.textContent = ''
        },
      }
    }

    node.setTarget(container.element)

    const handleResize = () => {
      node.emitResize && node.emitResize({ width: container.width, height: container.height })
    }

    const handleClose = () => {
      node.emitDestroy && node.emitDestroy({ $root: true, __nodeId: nodeId })
    }

    container.on('resize', handleResize)
    container.on('close', handleClose)
    nextTick(() => handleResize())

    return {
      __cleanup() {
        container.off('resize', handleResize)
        container.off('close', handleClose)
        node.setTarget(null)
      },
    }
  })

  gl.on('beforeComponentRelease', (boundComponent) => {
    if (boundComponent && typeof boundComponent.__cleanup === 'function') {
      boundComponent.__cleanup()
    }
  })

  gl.on('stateChanged', () => {
    const saved = gl.saveLayout()
    lastEmittedStateHash = safeHash(saved)
    // Allow re-applying the same external saved state after local edits.
    lastLoadedExternalStateHash = ''
    emit('state', saved)
  })

  layoutInstance.value = gl
}

function scheduleRootResize() {
  if (resizeFrame !== null) {
    cancelAnimationFrame(resizeFrame)
  }

  resizeFrame = requestAnimationFrame(() => {
    resizeFrame = null
    if (layoutInstance.value) {
      layoutInstance.value.updateRootSize(true)
    }
  })
}

function removeStaleDragProxies() {
  // GoldenLayout appends drag proxies to document.body, outside Vue's lifecycle.
  for (const element of document.querySelectorAll(STALE_DRAG_PROXY_SELECTOR)) {
    element.remove()
  }
}

function scheduleDragProxyCleanup() {
  if (dragCleanupFrame !== null) {
    cancelAnimationFrame(dragCleanupFrame)
  }

  dragCleanupFrame = requestAnimationFrame(() => {
    dragCleanupFrame = null
    removeStaleDragProxies()
  })
}

function buildTemplateLayout() {
  componentNodes.clear()
  componentNodesByConfigId.clear()

  const childrenByParent = new Map()

  for (const node of nodes.values()) {
    const parentId = node.parentId || null
    if (!childrenByParent.has(parentId)) {
      childrenByParent.set(parentId, [])
    }
    childrenByParent.get(parentId).push(node)
  }

  for (const siblings of childrenByParent.values()) {
    siblings.sort((left, right) => left.order - right.order)
  }

  const rootNodes = childrenByParent.get(null) || []
  if (rootNodes.length === 0) {
    return null
  }

  const buildNode = (node) => {
    const childNodes = childrenByParent.get(node.id) || []
    const childConfigs = childNodes.map((childNode) => buildNode(childNode))
    const config = node.getConfig(childConfigs)

    if (node.kind === 'component') {
      componentNodes.set(node.id, node)
      const configId = config && config.id !== undefined && config.id !== null
        ? (Array.isArray(config.id) ? config.id[0] : config.id)
        : null
      if (configId !== null && configId !== undefined) {
        componentNodesByConfigId.set(String(configId), node)
      }
    }

    return config
  }

  let rootConfig
  if (rootNodes.length === 1) {
    rootConfig = buildNode(rootNodes[0])
  } else {
    rootConfig = {
      type: 'row',
      content: rootNodes.map((rootNode) => buildNode(rootNode)),
      isClosable: false,
    }
  }

  return {
    root: rootConfig,
    header: { show: props.hasHeaders ? 'top' : false },
  }
}

function cloneValue(value) {
  if (value === null || value === undefined) {
    return value
  }

  try {
    return JSON.parse(JSON.stringify(value))
  } catch (error) {
    return value
  }
}

function normalizedConfigId(item) {
  if (!item || typeof item !== 'object') {
    return null
  }

  const rawId = item.id
  if (rawId === undefined || rawId === null) {
    return null
  }
  if (Array.isArray(rawId)) {
    return rawId.length ? String(rawId[0]) : null
  }
  return String(rawId)
}

function normalizedNodeId(item) {
  if (!item || typeof item !== 'object') {
    return null
  }

  if (item.componentState && item.componentState.__nodeId) {
    return String(item.componentState.__nodeId)
  }
  if (item.state && item.state.__nodeId) {
    return String(item.state.__nodeId)
  }
  if (item.__nodeId) {
    return String(item.__nodeId)
  }
  return null
}

function collectTemplateComponentMaps(root) {
  const byConfigId = new Map()
  const byNodeId = new Map()
  const components = []

  const walk = (item) => {
    if (!item || typeof item !== 'object') {
      return
    }

    if (item.type === 'component') {
      const cloned = cloneValue(item)
      components.push(cloned)
      const configId = normalizedConfigId(cloned)
      const nodeId = normalizedNodeId(cloned)
      if (configId) {
        byConfigId.set(configId, cloned)
      }
      if (nodeId) {
        byNodeId.set(nodeId, cloned)
      }
      return
    }

    const content = Array.isArray(item.content) ? item.content : []
    for (const child of content) {
      walk(child)
    }
  }

  walk(root)
  return { byConfigId, byNodeId, components }
}

function reconcileStateItem(item, templateMaps) {
  if (!item || typeof item !== 'object') {
    return null
  }

  if (item.type === 'component') {
    const configId = normalizedConfigId(item)
    const nodeId = normalizedNodeId(item)
    const templateComponent = (
      (configId ? templateMaps.byConfigId.get(configId) : null)
      || (nodeId ? templateMaps.byNodeId.get(nodeId) : null)
    )

    if (!templateComponent) {
      return null
    }

    const reconciled = cloneValue(item)
    const templateNodeId = normalizedNodeId(templateComponent)
    if (templateNodeId) {
      if (!reconciled.componentState || typeof reconciled.componentState !== 'object') {
        reconciled.componentState = {}
      }
      reconciled.componentState.__nodeId = templateNodeId
    }
    return reconciled
  }

  const cloned = cloneValue(item)
  const children = Array.isArray(cloned.content) ? cloned.content : []
  const nextChildren = children
    .map((child) => reconcileStateItem(child, templateMaps))
    .filter((child) => !!child)

  if (nextChildren.length === 0) {
    return null
  }

  cloned.content = nextChildren
  return cloned
}

function findFirstStack(item) {
  if (!item || typeof item !== 'object') {
    return null
  }
  if (item.type === 'stack') {
    return item
  }
  const content = Array.isArray(item.content) ? item.content : []
  for (const child of content) {
    const nested = findFirstStack(child)
    if (nested) {
      return nested
    }
  }
  return null
}

function collectExistingComponentKeys(root) {
  const keys = new Set()

  const walk = (item) => {
    if (!item || typeof item !== 'object') {
      return
    }

    if (item.type === 'component') {
      const configId = normalizedConfigId(item)
      const nodeId = normalizedNodeId(item)
      if (configId) {
        keys.add(`id:${configId}`)
      }
      if (nodeId) {
        keys.add(`node:${nodeId}`)
      }
      return
    }

    const content = Array.isArray(item.content) ? item.content : []
    for (const child of content) {
      walk(child)
    }
  }

  walk(root)
  return keys
}

function reconcileLayoutState(baseState, templateLayout) {
  if (!templateLayout || !templateLayout.root) {
    return baseState
  }

  const templateMaps = collectTemplateComponentMaps(templateLayout.root)
  const baseRoot = baseState && baseState.root ? baseState.root : null
  let reconciledRoot = baseRoot ? reconcileStateItem(baseRoot, templateMaps) : null

  if (!reconciledRoot) {
    return cloneValue(templateLayout)
  }

  const existingKeys = collectExistingComponentKeys(reconciledRoot)
  const missingComponents = templateMaps.components.filter((component) => {
    const configId = normalizedConfigId(component)
    const nodeId = normalizedNodeId(component)
    if (configId && existingKeys.has(`id:${configId}`)) {
      return false
    }
    if (nodeId && existingKeys.has(`node:${nodeId}`)) {
      return false
    }
    return true
  })

  if (missingComponents.length) {
    let targetStack = findFirstStack(reconciledRoot)

    if (!targetStack) {
      targetStack = {
        type: 'stack',
        isClosable: false,
        content: [],
      }
      if (Array.isArray(reconciledRoot.content)) {
        reconciledRoot.content.push(targetStack)
      } else {
        reconciledRoot = {
          type: 'row',
          isClosable: false,
          content: [reconciledRoot, targetStack],
        }
      }
    }

    if (!Array.isArray(targetStack.content)) {
      targetStack.content = []
    }
    for (const component of missingComponents) {
      targetStack.content.push(cloneValue(component))
    }
  }

  return {
    root: reconciledRoot,
    header: { show: props.hasHeaders ? 'top' : false },
  }
}

function normalizeHeaderShow(value) {
  if (value === false) {
    return false
  }
  if (value === 'top' || value === 'left' || value === 'right' || value === 'bottom') {
    return value
  }
  return 'top'
}

function normalizeSizeText(value, defaultUnit, allowedUnits) {
  if (value === undefined || value === null) {
    return null
  }

  if (typeof value === 'number') {
    return Number.isFinite(value) ? `${value}${defaultUnit}` : null
  }

  if (typeof value === 'string') {
    const text = value.trim()
    if (!text) {
      return null
    }

    const withUnit = /^-?\d+(\.\d+)?\s*(fr|%|px|em)$/.exec(text)
    if (withUnit) {
      const unit = withUnit[2]
      if (allowedUnits.has(unit)) {
        return `${Number(withUnit[0].replace(unit, '').trim())}${unit}`
      }
      return null
    }

    const bare = /^-?\d+(\.\d+)?$/.exec(text)
    if (bare) {
      return `${Number(text)}${defaultUnit}`
    }

    return null
  }

  if (typeof value === 'object') {
    const nestedSize = Object.prototype.hasOwnProperty.call(value, 'size') ? value.size : null
    const nestedUnit = (
      Object.prototype.hasOwnProperty.call(value, 'sizeUnit')
      && typeof value.sizeUnit === 'string'
      ? value.sizeUnit
      : defaultUnit
    )
    return normalizeSizeText(nestedSize, nestedUnit, allowedUnits)
  }

  return null
}

function normalizeItemForLoad(item) {
  if (!item || typeof item !== 'object') {
    return item
  }

  const normalized = cloneValue(item)
  const sizeUnit = typeof normalized.sizeUnit === 'string' ? normalized.sizeUnit : '%'
  const minSizeUnit = typeof normalized.minSizeUnit === 'string' ? normalized.minSizeUnit : 'px'

  const normalizedSize = normalizeSizeText(normalized.size, sizeUnit, new Set(['fr', '%']))
  if (normalizedSize) {
    normalized.size = normalizedSize
  } else {
    delete normalized.size
  }

  const normalizedMinSize = normalizeSizeText(normalized.minSize, minSizeUnit, new Set(['px']))
  if (normalizedMinSize) {
    normalized.minSize = normalizedMinSize
  } else {
    delete normalized.minSize
  }

  if (Array.isArray(normalized.id)) {
    normalized.id = normalized.id.length ? normalized.id[0] : ''
  }

  delete normalized.sizeUnit
  delete normalized.minSizeUnit

  if (Array.isArray(normalized.content)) {
    normalized.content = normalized.content
      .map((child) => normalizeItemForLoad(child))
      .filter((child) => !!child)
  }

  return normalized
}

function normalizeLayoutForLoad(layout) {
  const source = cloneValue(layout) || {}
  const normalized = {}

  if (source.root) {
    normalized.root = normalizeItemForLoad(source.root)
  }

  const header = source.header && typeof source.header === 'object'
    ? cloneValue(source.header)
    : {}
  header.show = normalizeHeaderShow(header.show)
  normalized.header = header

  return normalized
}

function forceSanitizeItemSizes(item) {
  if (!item || typeof item !== 'object') {
    return
  }

  if (Object.prototype.hasOwnProperty.call(item, 'size') && typeof item.size !== 'string') {
    const normalizedSize = normalizeSizeText(item.size, '%', new Set(['fr', '%']))
    if (normalizedSize) {
      item.size = normalizedSize
    } else {
      delete item.size
    }
  }

  if (Object.prototype.hasOwnProperty.call(item, 'minSize') && typeof item.minSize !== 'string') {
    const normalizedMinSize = normalizeSizeText(item.minSize, 'px', new Set(['px']))
    if (normalizedMinSize) {
      item.minSize = normalizedMinSize
    } else {
      delete item.minSize
    }
  }

  const content = Array.isArray(item.content) ? item.content : []
  for (const child of content) {
    forceSanitizeItemSizes(child)
  }
}

function loadLayout(layoutConfig) {
  if (!layoutConfig) {
    return
  }

  removeStaleDragProxies()
  ensureLayout()
  if (!layoutInstance.value) {
    return
  }

  const normalizedLayout = normalizeLayoutForLoad(layoutConfig)
  forceSanitizeItemSizes(normalizedLayout.root)

  layoutInstance.value.loadLayout(normalizedLayout)
  nextTick(() => {
    if (layoutInstance.value) {
      layoutInstance.value.updateRootSize(true)
    }
  })
}

function queueTemplateReload() {
  if (reloadQueued) {
    return
  }

  reloadQueued = true
  Promise.resolve().then(() => {
    reloadQueued = false
    const templateLayout = buildTemplateLayout()
    if (!templateLayout) {
      return
    }

    const externalState = props.state
    const externalStateHash = safeHash(externalState)
    const normalizedExternalState = externalState ? normalizeLayoutForLoad(externalState) : null
    const componentNodeIds = new Set(
      Array.from(nodes.values())
        .filter((node) => node.kind === 'component')
        .map((node) => node.id),
    )
    const componentConfigIds = new Set(
      Array.from(nodes.values())
        .filter((node) => node.kind === 'component')
        .map((node) => {
          const config = node.getConfig()
          const rawId = config && config.id
          if (rawId === undefined || rawId === null) {
            return null
          }
          if (Array.isArray(rawId)) {
            return rawId.length ? String(rawId[0]) : null
          }
          return String(rawId)
        })
        .filter((value) => !!value),
    )
    let baseState = null

    if (
      externalState
      && externalStateHash
      && externalStateHash !== lastEmittedStateHash
      && externalStateHash !== lastLoadedExternalStateHash
      && normalizedExternalState
      && isStateCompatible(normalizedExternalState, componentNodeIds, componentConfigIds)
    ) {
      lastLoadedExternalStateHash = externalStateHash
      baseState = normalizedExternalState
    } else if (layoutInstance.value) {
      const liveState = normalizeLayoutForLoad(layoutInstance.value.saveLayout())
      if (isStateCompatible(liveState, componentNodeIds, componentConfigIds)) {
        baseState = liveState
      }
    }

    if (!baseState) {
      loadLayout(templateLayout)
      return
    }

    const reconciledState = reconcileLayoutState(baseState, templateLayout)
    loadLayout(reconciledState)
  })
}

onMounted(() => {
  removeStaleDragProxies()

  if (typeof ResizeObserver !== 'undefined' && hostElement.value) {
    sizeObserver = new ResizeObserver(() => {
      scheduleRootResize()
    })
    sizeObserver.observe(hostElement.value)
  }

  queueTemplateReload()

  window.addEventListener('mouseup', scheduleDragProxyCleanup)
  window.addEventListener('pointerup', scheduleDragProxyCleanup)
  window.addEventListener('pointercancel', scheduleDragProxyCleanup)
  window.addEventListener('touchend', scheduleDragProxyCleanup)
  window.addEventListener('touchcancel', scheduleDragProxyCleanup)
  window.addEventListener('dragend', scheduleDragProxyCleanup)
  window.addEventListener('blur', scheduleDragProxyCleanup)
})

watch(
  () => registryVersion.value,
  () => {
    queueTemplateReload()
  },
)

watch(
  () => props.hasHeaders,
  () => {
    queueTemplateReload()
  },
)

watch(
  () => props.state,
  (nextState) => {
    if (!nextState) {
      return
    }

    const stateHash = safeHash(nextState)
    if (!stateHash || stateHash === lastEmittedStateHash || stateHash === lastLoadedExternalStateHash) {
      return
    }

    queueTemplateReload()
  },
  { deep: true },
)

onBeforeUnmount(() => {
  if (resizeFrame !== null) {
    cancelAnimationFrame(resizeFrame)
    resizeFrame = null
  }

  if (dragCleanupFrame !== null) {
    cancelAnimationFrame(dragCleanupFrame)
    dragCleanupFrame = null
  }

  window.removeEventListener('mouseup', scheduleDragProxyCleanup)
  window.removeEventListener('pointerup', scheduleDragProxyCleanup)
  window.removeEventListener('pointercancel', scheduleDragProxyCleanup)
  window.removeEventListener('touchend', scheduleDragProxyCleanup)
  window.removeEventListener('touchcancel', scheduleDragProxyCleanup)
  window.removeEventListener('dragend', scheduleDragProxyCleanup)
  window.removeEventListener('blur', scheduleDragProxyCleanup)

  if (sizeObserver) {
    sizeObserver.disconnect()
    sizeObserver = null
  }

  const registry = getGlobalLayoutRegistry()
  if (registry && registry[layoutId]) {
    delete registry[layoutId]
  }

  for (const node of nodes.values()) {
    if (node.kind === 'component' && node.setTarget) {
      node.setTarget(null)
    }
  }

  if (layoutInstance.value) {
    layoutInstance.value.destroy()
    layoutInstance.value = null
  }

  removeStaleDragProxies()
})
</script>

<style>
@import url("https://unpkg.com/golden-layout@2.6.0/dist/css/goldenlayout-base.css");
@import url("https://unpkg.com/golden-layout@2.6.0/dist/css/themes/goldenlayout-light-theme.css");

.gl-compat-root {
  position: relative;
  width: 100%;
  height: 100%;
}

.gl-compat-canvas {
  width: 100%;
  height: 100%;
}

.gl-compat-definitions {
  display: none;
}
</style>
