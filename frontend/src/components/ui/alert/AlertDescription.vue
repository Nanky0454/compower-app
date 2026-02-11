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
  <div :class="cn('text-sm [&_p]:leading-relaxed', props.class)" v-bind="delegatedProps">
    <slot />
  </div>
</template>