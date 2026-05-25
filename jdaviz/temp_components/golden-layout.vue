<template>
  <div class="gl-compat-root" :data-jdz-gl-layout-id="layoutId">
    <div ref="hostElement" class="gl-compat-canvas"></div>
    <div class="gl-compat-definitions">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { markRaw, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { GoldenLayout as GoldenLayoutCore } from 'https://esm.sh/golden-layout@2.6.0?bundle'

const props = defineProps({
  hasHeaders: { type: Boolean, default: true },
  state: { type: Object, default: null },
})

const emit = defineEmits(['state'])

const hostElement = ref(null)
const layoutInstance = shallowRef(null)
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
let settleResizeFrames = []
let dragCleanupFrame = null
let suppressCloseEvents = false
let suppressCloseReleaseFrame = null

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

function clearSuppressCloseReleaseFrame() {
  if (suppressCloseReleaseFrame !== null) {
    cancelAnimationFrame(suppressCloseReleaseFrame)
    suppressCloseReleaseFrame = null
  }
}

function suppressClosesUntilNextFrame(callback) {
  clearSuppressCloseReleaseFrame()
  suppressCloseEvents = true
  try {
    callback()
  } finally {
    suppressCloseReleaseFrame = requestAnimationFrame(() => {
      suppressCloseReleaseFrame = null
      suppressCloseEvents = false
    })
  }
}

function suppressCloses(callback) {
  clearSuppressCloseReleaseFrame()
  suppressCloseEvents = true
  try {
    callback()
  } finally {
    suppressCloseEvents = false
  }
}

function cancelCloseSuppression() {
  clearSuppressCloseReleaseFrame()
  suppressCloseEvents = false
}

function isStateCompatible(state, componentConfigIds = new Set()) {
  if (!state || typeof state !== 'object' || !state.root) {
    return false
  }

  const walk = (item) => {
    if (!item || typeof item !== 'object') {
      return true
    }

    if (item.type === 'component') {
      const rawId = item.id
      const configId = Array.isArray(rawId) ? (rawId.length ? String(rawId[0]) : null) : (
        rawId !== undefined && rawId !== null ? String(rawId) : null
      )
      return !!configId && componentConfigIds.has(configId)
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

  const gl = markRaw(new GoldenLayoutCore(hostElement.value))

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
      if (suppressCloseEvents) {
        return
      }
      node.emitUserClose && node.emitUserClose()
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
    const saved = stripRuntimeLayoutState(gl.saveLayout())
    lastEmittedStateHash = layoutComparisonHash(saved)
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

function updateRootSize() {
  if (layoutInstance.value) {
    layoutInstance.value.updateRootSize(true)
  }
}

function scheduleSettledRootResize() {
  for (const frame of settleResizeFrames) {
    cancelAnimationFrame(frame)
  }
  settleResizeFrames = []

  const scheduleFrame = (callback) => {
    const frame = requestAnimationFrame(() => {
      settleResizeFrames = settleResizeFrames.filter((value) => value !== frame)
      callback()
    })
    settleResizeFrames.push(frame)
  }

  nextTick(() => {
    updateRootSize()
    scheduleFrame(() => {
      updateRootSize()
      scheduleFrame(() => {
        updateRootSize()
      })
    })
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
      if (!config.componentState || typeof config.componentState !== 'object') {
        config.componentState = {}
      }
      config.componentState.__nodeId = node.id
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

function stripRuntimeItemState(item) {
  if (!item || typeof item !== 'object') {
    return item
  }

  const stripped = cloneValue(item)
  delete stripped.__nodeId

  for (const key of ['componentState', 'state']) {
    if (stripped[key] && typeof stripped[key] === 'object') {
      delete stripped[key].__nodeId
      if (Object.keys(stripped[key]).length === 0) {
        delete stripped[key]
      }
    }
  }

  if (Array.isArray(stripped.content)) {
    stripped.content = stripped.content
      .map((child) => stripRuntimeItemState(child))
      .filter((child) => !!child)
  }

  return stripped
}

function stripRuntimeLayoutState(layout) {
  const stripped = cloneValue(layout) || {}
  if (stripped.root) {
    stripped.root = stripRuntimeItemState(stripped.root)
  }
  return stripped
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

function runtimeNodeId(item) {
  return item && item.componentState && item.componentState.__nodeId
    ? String(item.componentState.__nodeId)
    : null
}

function collectTemplateComponentMaps(root) {
  const byConfigId = new Map()
  const components = []

  const walk = (item) => {
    if (!item || typeof item !== 'object') {
      return
    }

    if (item.type === 'component') {
      const cloned = cloneValue(item)
      components.push(cloned)
      const configId = normalizedConfigId(cloned)
      if (configId) {
        byConfigId.set(configId, cloned)
      }
      return
    }

    const content = Array.isArray(item.content) ? item.content : []
    for (const child of content) {
      walk(child)
    }
  }

  walk(root)
  return { byConfigId, components }
}

function reconcileStateItem(item, templateMaps) {
  if (!item || typeof item !== 'object') {
    return null
  }

  if (item.type === 'component') {
    const configId = normalizedConfigId(item)
    const templateComponent = configId ? templateMaps.byConfigId.get(configId) : null

    if (!templateComponent) {
      return null
    }

    const reconciled = cloneValue(item)
    const templateNodeId = runtimeNodeId(templateComponent)
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
      if (configId) {
        keys.add(`id:${configId}`)
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

function countLayoutStacks(item) {
  if (!item || typeof item !== 'object') {
    return 0
  }

  const content = Array.isArray(item.content) ? item.content : []
  const nestedCount = content.reduce((total, child) => total + countLayoutStacks(child), 0)
  return (item.type === 'stack' ? 1 : 0) + nestedCount
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
    if (configId && existingKeys.has(`id:${configId}`)) {
      return false
    }
    return true
  })

  if (missingComponents.length) {
    if (countLayoutStacks(templateLayout.root) > countLayoutStacks(reconciledRoot)) {
      return cloneValue(templateLayout)
    }

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

function normalizeAndSanitizeLayout(layout) {
  const normalizedLayout = normalizeLayoutForLoad(layout)
  forceSanitizeItemSizes(normalizedLayout.root)
  return normalizedLayout
}

function normalizeLayoutForComparison(layout) {
  const normalizedLayout = normalizeAndSanitizeLayout(layout)
  if (normalizedLayout.root) {
    normalizedLayout.root = stripRuntimeItemState(normalizedLayout.root)
  }
  normalizedLayout.header = { show: normalizeHeaderShow(normalizedLayout.header && normalizedLayout.header.show) }
  return normalizedLayout
}

function layoutComparisonHash(layout) {
  return safeHash(normalizeLayoutForComparison(layout))
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

  const normalizedLayout = normalizeAndSanitizeLayout(layoutConfig)

  suppressClosesUntilNextFrame(() => {
    layoutInstance.value.loadLayout(normalizedLayout)
  })
  scheduleSettledRootResize()
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
    const externalStateHash = layoutComparisonHash(externalState)
    const normalizedExternalState = externalState ? normalizeLayoutForLoad(externalState) : null
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
      && isStateCompatible(normalizedExternalState, componentConfigIds)
    ) {
      lastLoadedExternalStateHash = externalStateHash
      baseState = normalizedExternalState
    } else if (layoutInstance.value) {
      const liveState = normalizeLayoutForLoad(layoutInstance.value.saveLayout())
      if (isStateCompatible(liveState, componentConfigIds)) {
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
  window.addEventListener('resize', scheduleRootResize)
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

    const stateHash = layoutComparisonHash(nextState)
    const liveStateHash = layoutInstance.value ? layoutComparisonHash(layoutInstance.value.saveLayout()) : ''
    if (stateHash && stateHash === liveStateHash) {
      return
    }
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

  for (const frame of settleResizeFrames) {
    cancelAnimationFrame(frame)
  }
  settleResizeFrames = []

  if (dragCleanupFrame !== null) {
    cancelAnimationFrame(dragCleanupFrame)
    dragCleanupFrame = null
  }

  cancelCloseSuppression()

  window.removeEventListener('mouseup', scheduleDragProxyCleanup)
  window.removeEventListener('pointerup', scheduleDragProxyCleanup)
  window.removeEventListener('pointercancel', scheduleDragProxyCleanup)
  window.removeEventListener('touchend', scheduleDragProxyCleanup)
  window.removeEventListener('touchcancel', scheduleDragProxyCleanup)
  window.removeEventListener('dragend', scheduleDragProxyCleanup)
  window.removeEventListener('blur', scheduleDragProxyCleanup)
  window.removeEventListener('resize', scheduleRootResize)

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
    suppressCloses(() => {
      layoutInstance.value.destroy()
      layoutInstance.value = null
    })
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
