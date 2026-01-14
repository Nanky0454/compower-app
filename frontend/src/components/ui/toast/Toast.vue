<script setup>
import { computed } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  toast: Object
})

const emit = defineEmits(['close'])

const variantClasses = computed(() => {
  switch (props.toast.variant) {
    case 'destructive':
      return 'bg-red-600 text-white border-red-600'
    default:
      return 'bg-white text-gray-900 border-gray-200'
  }
})
</script>

<template>
  <div
    v-if="toast.open"
    class="pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 pr-8 shadow-lg transition-all data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=move]:transition-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-bottom-full"
    :class="variantClasses"
  >
    <div class="grid gap-1">
      <div v-if="toast.title" class="text-sm font-semibold">
        {{ toast.title }}
      </div>
      <div v-if="toast.description" class="text-sm opacity-90">
        {{ toast.description }}
      </div>
    </div>
    <button
      @click="$emit('close')"
      class="absolute right-2 top-2 rounded-md p-1 text-foreground/50 opacity-0 transition-opacity hover:text-foreground focus:opacity-100 focus:outline-none focus:ring-2 group-hover:opacity-100"
      :class="toast.variant === 'destructive' ? 'text-red-100 hover:text-white' : 'text-gray-500 hover:text-gray-900'"
    >
      <X class="h-4 w-4" />
    </button>
  </div>
</template>
