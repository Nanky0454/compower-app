import { ref } from 'vue'

const toasts = ref([])

function toast({ title, description, variant = 'default', duration = 3000 }) {
    const id = Math.random().toString(36).substring(2, 9)
    const newToast = { id, title, description, variant, open: true }
    toasts.value.push(newToast)

    if (duration !== Infinity) {
        setTimeout(() => {
            dismiss(id)
        }, duration)
    }

    return {
        id,
        dismiss: () => dismiss(id),
        update: (props) => update(id, props)
    }
}

function dismiss(id) {
    const t = toasts.value.find((t) => t.id === id)
    if (t) t.open = false
    // Optional: remove from array after animation
    setTimeout(() => {
        toasts.value = toasts.value.filter((t) => t.id !== id)
    }, 300)
}

function update(id, props) {
    const index = toasts.value.findIndex((t) => t.id === id)
    if (index !== -1) {
        toasts.value[index] = { ...toasts.value[index], ...props }
    }
}

export { useToast, toasts }

function useToast() {
    return {
        toast,
        dismiss,
        toasts
    }
}
