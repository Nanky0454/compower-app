<script setup lang="ts">
import { cn } from '@/lib/utils'
import { HTMLAttributes, computed } from 'vue'

interface Props {
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()

const delegatedProps = computed(() => {
  const { class: _, ...rest } = props
  return rest
})
</script>

<template>
  <h5 :class="cn('mb-1 font-medium leading-none tracking-tight', props.class)" v-bind="delegatedProps">
    <slot />
  </h5>
</template>