<template>
    <v-row justify="end" class="row-no-outside-padding">
        <div v-if="api_hints_enabled && api_hint">
            <span class="api-hint" style="margin-right: 6px">{{ api_hint }}</span>
        </div>
        <span v-if="api_hints_enabled && api_hint && selected === 'Any'" class="api-hint">'Any'</span>

        <div v-for="item in items">
            <j-tooltip v-if="item.label !== 'Any'" :tooltipcontent="'Show only '+item.label+' '+tooltip_suffix">
                <v-btn
                rounded="0"
                :elevation=0
                size="small"
                density="compact"
                :color="selected === item.label ? 'turquoise' : undefined"
                :theme="selected === item.label ? 'dark' : 'light'"
                @click="() => {if (selected === item.label) {$emit('update:selected', 'Any')} else {$emit('update:selected', item.label)}}"
                >
                    <span v-if="api_hints_enabled && api_hint && selected === item.label" style="text-transform: none">'{{ item.label }}'</span>
                    <span v-else>
                        <img v-if="item.icon && !item.icon.startsWith('mdi')" :src="item.icon" width="16" class="invert-if-dark" style="margin-right: 2px"/>
                        <v-icon v-if="item.icon && item.icon.startsWith('mdi')">{{ item.icon }}</v-icon>
                        {{ item.label }}
                    </span>
                </v-btn>
            </j-tooltip>
        </div>
    </v-row>
</template>

<script>
export default {
  props: ['items', 'selected', 'tooltip_suffix', 'api_hint', 'api_hints_enabled'],
}
</script>