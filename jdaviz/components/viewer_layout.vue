<template>
  <div ref="host" class="jdz-viewer-layout" :class="{ 'jdz-viewer-layout--dragging': gesture?.active }"
       :style="cssVariables" @pointermove="move" @pointercancel="cancel" @lostpointercapture="lostCapture">
    <section v-for="pane in geometry.panes" :key="pane.key" class="jdz-viewer-layout__pane" :style="boxStyle(pane)">
      <header v-if="hasHeaders" class="jdz-viewer-layout__header">
        <div :ref="(element) => setTabElement(pane.key, element)" class="jdz-viewer-layout__tabs" role="tablist">
          <template v-for="(id, index) in pane.node.viewers" :key="id">
            <div v-if="dropsTabAt(pane, index)" class="jdz-viewer-layout__tab-placeholder"></div>
            <div class="jdz-viewer-layout__tab"
                 :class="{ 'jdz-viewer-layout__tab--active': id === pane.node.activeViewerId }">
              <button type="button" class="jdz-viewer-layout__tab-label" role="tab"
                      :data-viewer-tab-id="id" :aria-selected="id === pane.node.activeViewerId"
                      :tabindex="id === pane.node.activeViewerId ? 0 : -1" :title="title(id)"
                      @click="select(id)" @keydown="tabKey($event, pane.node, id)"
                      @pointerdown="start($event, { id })" @auxclick.middle.prevent="close(id)">{{ title(id) }}</button>
              <button v-if="metadata.get(id)?.closable !== false" type="button"
                      :aria-label="`Close ${title(id)}`" @pointerdown.stop @click.stop="close(id)">×</button>
            </div>
          </template>
          <div v-if="dropsTabAt(pane, pane.node.viewers.length)" class="jdz-viewer-layout__tab-placeholder"></div>
        </div>
        <button type="button" class="jdz-viewer-layout__maximize"
                :aria-label="current.maximizedViewerId ? 'Restore viewer' : 'Maximize viewer'"
                @click="maximize(pane.node.activeViewerId)">{{ current.maximizedViewerId ? '▣' : '□' }}</button>
      </header>
    </section>
    <div v-for="(splitter, index) in geometry.splitters" :key="index" class="jdz-viewer-layout__splitter"
         :style="boxStyle(splitter)" role="separator" tabindex="0"
         :aria-orientation="splitter.axis === 'row' ? 'vertical' : 'horizontal'"
         @pointerdown="start($event, { splitter })" @keydown="splitKey($event, splitter)"></div>
    <div v-for="viewer in viewers" :key="viewer.id" :ref="(element) => setViewerElement(viewer.id, element)"
         class="jdz-viewer-layout__viewer" :data-viewer-id="viewer.id">
      <jupyter-widget :widget="viewer.widget" :key="viewer.widget || viewer.id"></jupyter-widget>
    </div>
    <div v-if="gesture?.active && !gesture.splitter" class="jdz-viewer-layout__ghost" :style="boxStyle(ghost)">
      <div class="jdz-viewer-layout__ghost-title">{{ title(gesture.id) }}</div>
    </div>
    <div v-if="drop" class="jdz-viewer-layout__drop" :class="{ 'jdz-viewer-layout__drop--tab': drop.tab }"
         :style="boxStyle(drop.preview)"></div>
  </div>
</template>

<script>
// Pure layout helpers, shared by all instances. A plain <script> block must
// contain an import or export, or ipyvue rewrites it as a bare options object.
export default { name: 'JViewerLayout' }

// Pixel sizes. BORDER and HEADER add up to the header band of a pane.
const GAP = 5
const BORDER = 1
const HEADER = 27
const TAB_DROP_WIDTH = 100
const MIN_PANE_SIZE = 50
const cloneLayout = (layout) => JSON.parse(JSON.stringify(layout))
const sum = (values) => values.reduce((a, b) => a + b, 0)

// Docking beside a target splits along the side's axis, before or after it.
const splitSide = (side) => ({
  axis: ['left', 'right'].includes(side) ? 'row' : 'column',
  before: ['left', 'top'].includes(side),
})

// Shrink a box to the half facing the drop side.
function halfBox(box, side) {
  const { axis, before } = splitSide(side)
  const [position, dimension] = axis === 'row' ? ['left', 'width'] : ['top', 'height']
  const half = box[dimension] / 2
  return { ...box, [dimension]: half, [position]: box[position] + (before ? 0 : half) }
}

function findStack(node, id, parent = null) {
  if (!node) return null
  if (node.type === 'stack') return node.viewers.includes(id) ? { node, parent } : null
  for (const child of node.children) {
    const found = findStack(child, id, node)
    if (found) return found
  }
  return null
}

// Mirrors _normalize_weights in core/viewer_layout.py: sibling weights sum to
// one with twelve-digit precision, and none become zero.
function normalizeWeights(children) {
  const weights = children.map((child) => child.weight ?? 1)
  const scale = Math.max(...weights)
  const scaled = weights.map((weight) => weight / scale)
  const total = sum(scaled)
  const normalized = scaled.map((weight) => Math.max(+(weight / total).toFixed(12), 1e-12))
  const largest = normalized.indexOf(Math.max(...normalized))
  normalized[largest] = +(normalized[largest] + (1 - sum(normalized))).toFixed(12)
  children.forEach((child, i) => { child.weight = normalized[i] })
}

// The Python boundary validates input. Edits only need pruning, defaults, and
// the same weight normalization as the canonical model.
function normalizeLayout(layout) {
  function prune(node) {
    if (!node) return null
    if (node.type === 'stack') {
      if (!node.viewers.length) return null
      if (!node.viewers.includes(node.activeViewerId)) node.activeViewerId = node.viewers[0]
    } else {
      node.children = node.children.map(prune).filter(Boolean)
      if (!node.children.length) return null
      if (node.children.length === 1) {
        const child = node.children[0]
        child.weight = node.weight
        return child
      }
      normalizeWeights(node.children)
    }
    // Keep field order stable for comparisons with Python's normalized replies.
    return node.type === 'stack'
      ? { type: node.type, weight: node.weight, viewers: node.viewers, activeViewerId: node.activeViewerId }
      : { type: node.type, weight: node.weight, children: node.children }
  }
  const result = { version: layout.version, root: prune(cloneLayout(layout.root)) }
  if (result.root) delete result.root.weight
  if (layout.maximizedViewerId !== undefined) {
    const stack = findStack(result.root, layout.maximizedViewerId)
    if (stack) result.maximizedViewerId = stack.node.activeViewerId
  }
  return result
}

// Preserve selection next to the removed tab, including maximized stacks.
function removeTab(stack, id) {
  const index = stack.viewers.indexOf(id)
  if (index < 0) return
  stack.viewers.splice(index, 1)
  if (stack.activeViewerId === id) stack.activeViewerId = stack.viewers[Math.max(0, index - 1)]
}

// Edit helpers take a normalized layout and return a draft for publish().
function closeViewer(layout, id) {
  const result = cloneLayout(layout)
  const found = findStack(result.root, id)
  if (!found) return result
  removeTab(found.node, id)
  if (result.maximizedViewerId === id) result.maximizedViewerId = found.node.activeViewerId
  return result
}

// Root-edge docking places a new pane beside the entire remaining layout.
function dockViewerAtRoot(layout, id, side) {
  let result = cloneLayout(layout)
  const source = findStack(result.root, id)
  if (!source || !['left', 'right', 'top', 'bottom'].includes(side)) return result
  removeTab(source.node, id)
  delete result.maximizedViewerId
  // Prune the source before choosing how to split the remaining root.
  result = normalizeLayout(result)
  const stack = { type: 'stack', viewers: [id], activeViewerId: id, weight: 0.5 }
  const { axis, before } = splitSide(side)
  if (!result.root) result.root = stack
  else if (result.root.type === axis) {
    result.root.children.forEach((child) => { child.weight /= 2 })
    result.root.children.splice(before ? 0 : result.root.children.length, 0, stack)
  } else {
    result.root.weight = 0.5
    result.root = { type: axis, children: before ? [stack, result.root] : [result.root, stack] }
  }
  return result
}

function dockViewer(layout, id, targetId, side = 'center', index) {
  const result = cloneLayout(layout)
  const foundSource = findStack(result.root, id), foundTarget = findStack(result.root, targetId)
  if (!foundSource || !foundTarget) return result
  const source = foundSource.node
  const { node: target, parent } = foundTarget
  if (source === target && target.viewers.length === 1) return result
  const oldIndex = source.viewers.indexOf(id)
  removeTab(source, id)
  delete result.maximizedViewerId
  if (side === 'center') {
    let insertion = index ?? target.viewers.length
    if (index !== undefined && source === target && oldIndex < index) insertion--
    target.viewers.splice(insertion, 0, id)
    target.activeViewerId = id
  } else {
    const { axis, before } = splitSide(side)
    const stack = { type: 'stack', viewers: [id], activeViewerId: id }
    if (parent?.type === axis) {
      target.weight /= 2
      stack.weight = target.weight
      parent.children.splice(parent.children.indexOf(target) + (before ? 0 : 1), 0, stack)
    } else {
      const split = { type: axis, weight: target.weight, children: before ? [stack, target] : [target, stack] }
      target.weight = stack.weight = 1
      if (parent) parent.children.splice(parent.children.indexOf(target), 1, split)
      else result.root = split
    }
  }
  return result
}

// Pixel constraints affect only this projection, never the stored weights.
function layoutGeometry(layout, width, height) {
  const panes = [], splitters = []
  function minimum(node, axis) {
    if (node.type === 'stack') return MIN_PANE_SIZE
    const values = node.children.map((child) => minimum(child, axis))
    return node.type === axis ? sum(values) + GAP * (values.length - 1) : Math.max(...values)
  }
  function place(node, box, key) {
    if (!node) return
    if (node.type === 'stack') {
      panes.push({ ...box, node, key })
      return
    }
    const position = node.type === 'row' ? 'left' : 'top'
    const dimension = node.type === 'row' ? 'width' : 'height'
    const total = Math.max(0, box[dimension] - GAP * (node.children.length - 1))
    const minima = node.children.map((child) => minimum(child, node.type))
    let sizes = node.children.map((child) => total * child.weight)
    const deficit = sizes.reduce((sum, size, i) => sum + Math.max(0, minima[i] - size), 0)
    const slack = sizes.reduce((sum, size, i) => sum + Math.max(0, size - minima[i]), 0)
    const minTotal = sum(minima)
    if (deficit) sizes = slack >= deficit
      ? sizes.map((size, i) => Math.max(size, minima[i]) - Math.max(0, size - minima[i]) * deficit / slack)
      : minima.map((size) => total * size / minTotal)
    let offset = 0
    node.children.forEach((child, index) => {
      place(child, { ...box, [position]: box[position] + offset, [dimension]: sizes[index] }, `${key}-${index}`)
      offset += sizes[index]
      if (index < node.children.length - 1) {
        splitters.push({ ...box, [position]: box[position] + offset, [dimension]: GAP,
          axis: node.type, node, index, sizes, minima })
        offset += GAP
      }
    })
  }
  const root = (layout.maximizedViewerId && findStack(layout.root, layout.maximizedViewerId)?.node) || layout.root
  place(root, { left: 0, top: 0, width, height }, 'root')
  return { panes, splitters }
}
</script>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'

const props = defineProps({
  layout: { type: Object, required: true },
  viewers: { type: Array, required: true },
  hasHeaders: { type: Boolean, default: true },
  layoutReset: { type: Number, default: 0 },
})
const emit = defineEmits(['update:layout', 'viewer-close'])
const host = ref(null)
// Hosts belong to the registry, never to a pane. Moving a tab only changes CSS.
const viewerElements = new Map()
const tabElements = new Map()
// The style block reads these, so each size is defined once.
const cssVariables = {
  '--jdz-viewer-layout-border-width': `${BORDER}px`,
  '--jdz-viewer-layout-header-height': `${HEADER}px`,
  '--jdz-viewer-layout-tab-drop-width': `${TAB_DROP_WIDTH}px`,
}
function setViewerElement(id, element) {
  if (element) {
    if (viewerElements.get(id) === element) return
    viewerElements.set(id, element)
    schedulePlacement()
  } else viewerElements.delete(id)
}
function setTabElement(key, element) {
  if (element) tabElements.set(key, element)
  else tabElements.delete(key)
}
// Horizontal scrolling keeps the active label reachable, without scrolling
// the notebook or surrounding application.
function scrollActiveTabsIntoView() {
  for (const element of tabElements.values()) {
    const tab = element.querySelector('[aria-selected="true"]')
    if (!tab) continue
    const box = tab.getBoundingClientRect(), viewport = element.getBoundingClientRect()
    if (box.left < viewport.left) element.scrollLeft -= viewport.left - box.left
    else if (box.right > viewport.right) element.scrollLeft += box.right - viewport.right
  }
}
const current = ref(normalizeLayout(props.layout))
const size = ref({ width: 0, height: 0 })
const gesture = shallowRef(null)
const drop = shallowRef(null)
const ghost = shallowRef({ left: 0, top: 0, width: 300, height: 200 })
const metadata = computed(() => new Map(props.viewers.map((viewer) => [viewer.id, viewer])))
const headerHeight = computed(() => (props.hasHeaders ? BORDER + HEADER : 0))
const dropsTabAt = (pane, index) => drop.value?.tab?.paneKey === pane.key && drop.value.tab.index === index
// Detach only in the visual projection until drop; cancellation and Python
// synchronization still have the complete tree, and widget hosts stay mounted.
const displayedLayout = computed(() => {
  const edit = gesture.value
  if (!edit?.active || edit.splitter) return current.value
  const detached = closeViewer(current.value, edit.id)
  delete detached.maximizedViewerId
  return normalizeLayout(detached)
})
const geometry = computed(() => layoutGeometry(displayedLayout.value, size.value.width, size.value.height))
let observer, placementQueued = false, disposed = false
const pendingLayouts = []
const title = (id) => metadata.value.get(id)?.reference || metadata.value.get(id)?.name || id
const boxStyle = (box) => Object.fromEntries(['left', 'top', 'width', 'height'].map((key) => [key, `${box[key]}px`]))

function publish(layout, viewerId) {
  const next = normalizeLayout(layout)
  const key = JSON.stringify(next)
  const changed = key !== (pendingLayouts.at(-1) ?? JSON.stringify(normalizeLayout(props.layout)))
  current.value = next
  if (viewerId || changed) pendingLayouts.push(key)
  if (viewerId) emit('viewer-close', { viewerId, layout: cloneLayout(next) })
  else if (changed) emit('update:layout', cloneLayout(next))
}

function select(id) {
  if (!findStack(current.value.root, id)) return
  const next = cloneLayout(current.value)
  findStack(next.root, id).node.activeViewerId = id
  publish(next)
}
function close(id) {
  const source = findStack(current.value.root, id)
  if (!source || metadata.value.get(id)?.closable === false) return
  const remaining = source.node.viewers.filter((viewer) => viewer !== id)
  const next = closeViewer(current.value, id)
  const active = remaining.length ? findStack(next.root, remaining[0]).node.activeViewerId : null
  publish(next, id)
  focusTab(active)
}
// Focus a tab once rendered; without an ID, focus any selected tab.
function focusTab(id) {
  nextTick(() => {
    if (disposed || !host.value) return
    host.value.querySelector(id
      ? `[role=tab][data-viewer-tab-id="${CSS.escape(id)}"]`
      : '[role=tab][aria-selected="true"]')?.focus()
  })
}
function maximize(id) {
  const next = cloneLayout(current.value)
  if (next.maximizedViewerId) delete next.maximizedViewerId
  else next.maximizedViewerId = id
  publish(next)
}
function tabKey(event, stack, id) {
  if (gesture.value) return
  let index = stack.viewers.indexOf(id)
  if (event.key === 'ArrowRight') index++
  else if (event.key === 'ArrowLeft') index--
  else if (event.key === 'Home') index = 0
  else if (event.key === 'End') index = stack.viewers.length - 1
  else if (!['Enter', ' '].includes(event.key)) return
  event.preventDefault()
  id = stack.viewers[(index + stack.viewers.length) % stack.viewers.length]
  select(id)
  focusTab(id)
}

function start(event, detail) {
  if (gesture.value || !event.isPrimary || event.button !== 0) return
  host.value.setPointerCapture(event.pointerId)
  gesture.value = { ...detail, pointerId: event.pointerId, x: event.clientX, y: event.clientY,
    original: cloneLayout(current.value), active: false }
}

function splitBounds({ index, sizes, minima }) {
  const total = sizes[index] + sizes[index + 1]
  const factor = Math.min(1, total / (minima[index] + minima[index + 1] || 1))
  const min = Math.min(total, minima[index] * factor)
  return { total, min, max: Math.max(min, total - minima[index + 1] * factor) }
}
function resizeSplit(splitter, delta) {
  const { node, index } = splitter
  const sizes = [...splitter.sizes]
  const { total, min, max } = splitBounds(splitter)
  sizes[index] = Math.max(min, Math.min(max, sizes[index] + delta))
  sizes[index + 1] = total - sizes[index]
  // Start from displayed sizes so minimum-size projection cannot move other dividers.
  const available = sum(sizes) || 1
  node.children.forEach((child, i) => { child.weight = Math.max(1e-12, sizes[i] / available) })
}
function splitKey(event, splitter) {
  if (gesture.value) return
  const keys = splitter.axis === 'row' ? ['ArrowLeft', 'ArrowRight'] : ['ArrowUp', 'ArrowDown']
  if (!keys.includes(event.key)) return
  event.preventDefault()
  resizeSplit(splitter, event.key === keys[0] ? -10 : 10)
  publish(current.value)
}

async function move(event) {
  let edit = gesture.value
  if (!edit || event.pointerId !== edit.pointerId) return
  const dx = event.clientX - edit.x, dy = event.clientY - edit.y
  if (!edit.active && Math.hypot(dx, dy) < 6) return
  if (!edit.active) {
    edit = gesture.value = { ...edit, active: true }
    if (!edit.splitter) {
      // Header insertion needs the remaining panes' DOM as well as geometry.
      await nextTick()
      if (gesture.value !== edit) return
    }
  }
  if (edit.splitter) {
    resizeSplit(edit.splitter, edit.splitter.axis === 'row' ? dx : dy)
    return
  }
  updateDrop(event, edit)
}

function updateDrop(event, edit) {
  const rect = host.value.getBoundingClientRect()
  const x = event.clientX - rect.left, y = event.clientY - rect.top
  ghost.value = { left: x + 12, top: y + 12, width: Math.min(300, rect.width), height: Math.min(200, rect.height) }
  drop.value = null
  if (x < 0 || y < 0 || x > rect.width || y > rect.height) return
  if (current.value.root?.type === 'stack' && current.value.root.viewers.length === 1) return
  drop.value = rootEdgeDrop(x, y, rect) ?? paneDrop(event, edit, x, y, rect)
}

// A narrow band at the outer border wins over individual pane targets.
// Choose the nearest edge at corners, so all four remain reachable.
function rootEdgeDrop(x, y, rect) {
  const [[side, distance]] = [['left', x], ['right', rect.width - x], ['top', y], ['bottom', rect.height - y]]
    .sort((a, b) => a[1] - b[1])
  if (distance >= Math.min(8, rect.width / 8, rect.height / 8)) return null
  return { root: true, side, preview: halfBox({ left: 0, top: 0, width: rect.width, height: rect.height }, side) }
}

// Dropping on a header inserts a tab; dropping on content docks by quarter.
function paneDrop(event, edit, x, y, rect) {
  const pane = geometry.value.panes.find((box) =>
    x >= box.left && x <= box.left + box.width && y >= box.top && y <= box.top + box.height)
  if (!pane || (pane.node.viewers.length === 1 && pane.node.viewers[0] === edit.id)) return null
  const targetId = pane.node.viewers[0]
  const contentTop = pane.top + headerHeight.value
  if (y < contentTop) {
    const tab = tabDrop(event, edit, pane, rect)
    return tab && { targetId, side: 'center', ...tab }
  }
  const verticalEdge = (pane.top + pane.height - contentTop) / 4
  let side = 'center'
  if (x - pane.left < pane.width / 4) side = 'left'
  else if (pane.left + pane.width - x < pane.width / 4) side = 'right'
  else if (y - contentTop < verticalEdge) side = 'top'
  else if (pane.top + pane.height - y < verticalEdge) side = 'bottom'
  const box = { left: pane.left, top: pane.top, width: pane.width, height: pane.height }
  return { targetId, side, preview: side === 'center' ? box : halfBox(box, side) }
}

function tabDrop(event, edit, pane, rect) {
  const container = tabElements.get(pane.key)
  if (!container) return null
  const tabs = []
  let shift = 0
  // Measure without the rendered gap so insertion cannot oscillate. Read
  // the DOM rather than drop state: a same-turn release can precede rendering.
  for (const element of container.children) {
    const box = element.getBoundingClientRect()
    if (element.classList.contains('jdz-viewer-layout__tab-placeholder')) shift += box.width
    else tabs.push({ left: box.left - shift, width: box.width })
  }
  let index = tabs.findIndex((box) => event.clientX < box.left + box.width / 2)
  if (index < 0) index = tabs.length
  const tab = { paneKey: pane.key, index }
  const insertionX = index < tabs.length ? tabs[index].left : tabs.at(-1).left + tabs.at(-1).width
  const viewport = container.getBoundingClientRect()
  const preview = {
    left: Math.max(viewport.left, Math.min(insertionX, viewport.right - TAB_DROP_WIDTH)) - rect.left,
    top: pane.top, width: Math.min(TAB_DROP_WIDTH, viewport.width), height: BORDER + HEADER,
  }
  // dockViewer accepts insertion indices from before source removal.
  const source = findStack(current.value.root, edit.id).node
  if (source.viewers.includes(pane.node.viewers[0]) && source.viewers.indexOf(edit.id) <= index) index++
  return { index, tab, preview }
}

async function finish(event) {
  const edit = gesture.value
  if (!edit || edit.pointerId !== event.pointerId) return
  if (edit.active) {
    if (edit.splitter) {
      resizeSplit(edit.splitter, edit.splitter.axis === 'row' ? event.clientX - edit.x : event.clientY - edit.y)
      publish(current.value)
    } else {
      // Detaching the tab may still be rendering the remaining headers on release.
      await nextTick()
      if (gesture.value !== edit) return
      updateDrop(event, edit)
      if (drop.value) publish(drop.value.root
        ? dockViewerAtRoot(current.value, edit.id, drop.value.side)
        : dockViewer(current.value, edit.id, drop.value.targetId, drop.value.side, drop.value.index))
      else current.value = edit.original
    }
  } else if (!edit.splitter) select(edit.id)
  gesture.value = drop.value = null
  if (host.value.hasPointerCapture(event.pointerId)) host.value.releasePointerCapture(event.pointerId)
}
function cancel() {
  const edit = gesture.value
  gesture.value = drop.value = null
  if (edit) {
    current.value = edit.original
    if (host.value.hasPointerCapture(edit.pointerId)) host.value.releasePointerCapture(edit.pointerId)
  }
}
function lostCapture(event) {
  // Lab can lose capture just before pointerup reaches a sibling plot widget.
  if (event.pointerId === gesture.value?.pointerId && event.buttons) cancel()
}
function escape(event) { if (event.key === 'Escape') cancel() }

watch(() => props.layout, (layout) => {
  const next = normalizeLayout(layout)
  const acknowledged = pendingLayouts.indexOf(JSON.stringify(next))
  if (acknowledged !== -1) {
    pendingLayouts.splice(0, acknowledged + 1)
    return // A Python echo must not cancel or rewind a newer local edit.
  }
  pendingLayouts.length = 0
  cancel()
  current.value = next
}, { deep: true })
// A rejected edit can leave Python's layout unchanged. Its reset counter makes
// that rejection observable even when the canonical tree did not change.
watch(() => props.layoutReset, () => {
  pendingLayouts.length = 0
  cancel()
  current.value = normalizeLayout(props.layout)
})
function applyPlacement() {
  if (disposed || !host.value) return
  // Clip widgets immediately, even while plots are still redrawing. Registry
  // and layout messages may arrive separately; new host refs also trigger this.
  const placements = new Map()
  const header = headerHeight.value
  for (const pane of geometry.value.panes) {
    const width = Math.max(0, pane.width - 2 * BORDER)
    const height = Math.max(0, pane.height - header - 2 * BORDER)
    placements.set(pane.node.activeViewerId, {
      ...boxStyle({ left: pane.left + BORDER, top: pane.top + header + BORDER, width, height }),
      display: width > 0 && height > 0 ? 'block' : 'none',
    })
  }
  for (const [id, element] of viewerElements) {
    Object.assign(element.style, placements.get(id) || { display: 'none' })
  }
  scrollActiveTabsIntoView()
}
function schedulePlacement() {
  if (placementQueued || disposed) return
  placementQueued = true
  nextTick(() => {
    placementQueued = false
    applyPlacement()
  })
}
watch(geometry, schedulePlacement, { deep: true, flush: 'post' })
// Only header changes and widget replacements need work beyond geometry updates.
watch(() => props.hasHeaders, schedulePlacement, { flush: 'post' })
watch(() => props.viewers.map(({ id, widget, reference, name, closable }) =>
  [id, widget, reference, name, closable]), schedulePlacement, { flush: 'post' })
onMounted(() => {
  observer = new ResizeObserver(() => {
    const width = host.value.clientWidth, height = host.value.clientHeight
    if (width !== size.value.width || height !== size.value.height) size.value = { width, height }
    schedulePlacement()
  })
  observer.observe(host.value)
  schedulePlacement()
  window.addEventListener('keydown', escape)
  window.addEventListener('blur', cancel)
  window.addEventListener('pointerup', finish, true)
})
onBeforeUnmount(() => {
  disposed = true
  cancel()
  observer.disconnect()
  window.removeEventListener('keydown', escape)
  window.removeEventListener('blur', cancel)
  window.removeEventListener('pointerup', finish, true)
  for (const element of viewerElements.values()) element.style.display = 'none'
})
</script>

<style>
.jdz-viewer-layout {
  position: relative; height: 100%; overflow: hidden;
  color: var(--jdz-viewer-layout-ink); font: 13px sans-serif;
  --jdz-viewer-layout-surface: #fff; --jdz-viewer-layout-header: #eee; --jdz-viewer-layout-ink: #333;
  --jdz-viewer-layout-border-color: #bbb; --jdz-viewer-layout-hover: #ddd; --jdz-viewer-layout-accent: #4477aa;
}
.theme--dark .jdz-viewer-layout, .v-theme--dark .jdz-viewer-layout {
  --jdz-viewer-layout-surface: #212121; --jdz-viewer-layout-header: #303030; --jdz-viewer-layout-ink: #eee;
  --jdz-viewer-layout-border-color: #666; --jdz-viewer-layout-hover: #454545; --jdz-viewer-layout-accent: #90caf9;
}
/* Every child is a box placed by boxStyle(); later children paint on top. */
.jdz-viewer-layout > * { position: absolute; box-sizing: border-box; }
.jdz-viewer-layout--dragging { cursor: grabbing; }
.jdz-viewer-layout--dragging > * { pointer-events: none; }
.jdz-viewer-layout__viewer { display: none; overflow: hidden; z-index: 1; }
.jdz-viewer-layout__viewer > * { width: 100%; height: 100%; }
.jdz-viewer-layout__pane {
  border: var(--jdz-viewer-layout-border-width) solid var(--jdz-viewer-layout-border-color);
  background: var(--jdz-viewer-layout-surface);
}
.jdz-viewer-layout__header {
  display: flex; height: var(--jdz-viewer-layout-header-height);
  background: var(--jdz-viewer-layout-header); user-select: none;
}
/* :where() keeps this reset below the single-class rules that follow it. */
.jdz-viewer-layout__header :where(button) {
  border: 0; padding: 0 4px; background: transparent; color: inherit; font: inherit; cursor: pointer;
}
.jdz-viewer-layout__header button:hover { background: var(--jdz-viewer-layout-hover); }
.jdz-viewer-layout__header :focus-visible, .jdz-viewer-layout__splitter:focus-visible {
  outline: 2px solid var(--jdz-viewer-layout-accent); outline-offset: -2px;
}
.jdz-viewer-layout__tabs { display: flex; flex: 1; min-width: 0; overflow-x: auto; scrollbar-width: thin; }
.jdz-viewer-layout__tab {
  display: flex; flex-shrink: 0; align-items: center; padding: 2px 3px; white-space: nowrap;
  border-right: 1px solid var(--jdz-viewer-layout-border-color);
}
.jdz-viewer-layout__tab--active {
  background: var(--jdz-viewer-layout-surface); box-shadow: inset 0 2px var(--jdz-viewer-layout-accent);
}
.jdz-viewer-layout__tab-label { height: 100%; cursor: grab; touch-action: none; }
.jdz-viewer-layout__tab-placeholder { flex: 0 0 var(--jdz-viewer-layout-tab-drop-width); }
.jdz-viewer-layout__maximize { flex: 0 0 25px; font-size: 18px; }
.jdz-viewer-layout__splitter { z-index: 2; touch-action: none; background: var(--jdz-viewer-layout-hover); }
.jdz-viewer-layout__splitter[aria-orientation="vertical"] { cursor: col-resize; }
.jdz-viewer-layout__splitter[aria-orientation="horizontal"] { cursor: row-resize; }
.jdz-viewer-layout__splitter:hover { background: var(--jdz-viewer-layout-accent); }
.jdz-viewer-layout__ghost {
  z-index: 3; pointer-events: none; border: 1px solid var(--jdz-viewer-layout-accent);
  background: color-mix(in srgb, var(--jdz-viewer-layout-surface) 75%, transparent); box-shadow: 2px 2px 4px #0003;
}
.jdz-viewer-layout__ghost-title {
  box-sizing: border-box; height: var(--jdz-viewer-layout-header-height); padding: 5px 8px;
  overflow: hidden; white-space: nowrap; text-overflow: ellipsis;
  background: var(--jdz-viewer-layout-header); border-bottom: 1px solid var(--jdz-viewer-layout-border-color);
}
.jdz-viewer-layout__drop {
  z-index: 4; pointer-events: none; border: 1px dashed var(--jdz-viewer-layout-accent);
  background: color-mix(in srgb, var(--jdz-viewer-layout-accent) 18%, transparent);
}
.jdz-viewer-layout__drop--tab { border-style: solid; }
</style>
