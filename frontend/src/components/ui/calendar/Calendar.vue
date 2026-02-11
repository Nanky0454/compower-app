<script setup lang="ts">
import { Calendar as VCalendar } from 'v-calendar'
import 'v-calendar/dist/style.css' // import VCalendar style
import { useAttrs } from 'vue'

const props = defineProps<{
  modelValue?: any
}>()

const emits = defineEmits(['update:modelValue'])
const attrs = useAttrs() // Get all fallthrough attributes
</script>

<template>
  <VCalendar
    v-bind="attrs"
    :model-value="modelValue"
    @update:model-value="(val) => emits('update:modelValue', val)"
  />
</template>