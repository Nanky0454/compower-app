<script setup lang="ts">
import type { VariantProps } from 'class-variance-authority'
import { cva } from 'class-variance-authority'
import { HTMLAttributes, computed } from 'vue'
import { cn } from '@/lib/utils'

type AlertVariants = VariantProps<typeof alertVariants>

interface Props {
  variant?: AlertVariants['variant']
  class?: HTMLAttributes['class']
}

const props = defineProps<Props>()

const alertVariants = cva(
  'relative w-full rounded-lg border p-4 [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:text-foreground',
  {
    variants: {
      variant: {
        default: 'bg-background text-foreground',
        destructive:
          'border-destructive/50 text-destructive dark:border-destructive [&>svg]:text-destructive',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

const delegatedProps = computed(() => {
  const { class: _, variant, ...rest } = props
  return rest
})
</script>

<template>
  <div
    role="alert"
    :class="cn(alertVariants({ variant }), props.class)"
    v-bind="delegatedProps"
  >
    <slot />
  </div>
</template>