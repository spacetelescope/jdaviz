<template>
    <v-row justify="end" class="row-no-outside-padding" style="margin-bottom: -6px !important">
        <div v-for="item in items">
            <j-tooltip v-if="item.label !== 'Any'" :tooltipcontent="'Show only '+item.label+' '+tooltip_suffix">
                <v-btn
                tile
                :elevation=0
                x-small
                dense 
                :color="selected === item.label ? 'turquoise' : 'transparent'"
                :dark="selected === item.label"
                style="padding-left: 8px; padding-right: 6px;"
                @click="() => {if (selected === item.label) {$emit('update:selected', 'Any')} else {$emit('update:selected', item.label)}}"
                >
                    <img v-if="item.icon" :src="item.icon" width="16" class="invert-if-dark" style="margin-right: 2px"/>
                    {{ item.label }}
                </v-btn>
            </j-tooltip>
        </div>
    </v-row>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'tooltip_suffix'],
}
</script>