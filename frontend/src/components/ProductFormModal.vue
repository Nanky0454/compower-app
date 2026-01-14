<script setup>
import { ref, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Loader2 } from 'lucide-vue-next'

// --- Props y Emits ---
// defineProps define los datos que este componente RECIBE
const props = defineProps({
  open: { type: Boolean, default: false },
  categories: { type: Array, default: () => [] }
})

// defineEmits define los eventos que este componente ENVÍA
const emit = defineEmits(['update:open', 'productCreated'])

// --- Lógica Interna ---
const { getAccessTokenSilently } = useAuth0()
const isSubmitting = ref(false)
const error = ref(null)
const formData = ref({
  sku: '',
  name: '',
  unit_of_measure: 'UND',
  category_id: null
})

// Resetea el formulario cuando se cierra el modal
watch(() => props.open, (newVal) => {
  if (newVal === false) {
    error.value = null
    formData.value = { sku: '', name: '', unit_of_measure: 'UND', category_id: null }
  }
})

async function handleFormSubmit() {
  isSubmitting.value = true
  error.value = null

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/products`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(formData.value)
    })

    const newProduct = await response.json()
    if (!response.ok) throw new Error(newProduct.error || 'Error al guardar el producto.')

    // ¡Éxito!
    emit('productCreated', newProduct) // 1. Envía el evento con el producto nuevo
    emit('update:open', false)       // 2. Cierra el modal

  } catch (e) {
    error.value = e.message
  } finally {
    isSubmitting.value = false
  }
}

function closeModal() {
  emit('update:open', false)
}
</script>

<template>
  <Dialog :open="open" @update:open="closeModal">
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>Crear Nuevo Producto</DialogTitle>
      </DialogHeader>

      <div v-if="error" class="text-red-500 text-sm">{{ error }}</div>

      <div class="grid gap-4 py-4">
        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="sku" class="text-right">SKU</Label>
          <Input id="sku" v-model="formData.sku" class="col-span-3" />
        </div>
        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="name" class="text-right">Nombre</Label>
          <Input id="name" v-model="formData.name" class="col-span-3" />
        </div>
        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="um" class="text-right">UM (Ej. UND, M)</Label>
          <Input id="um" v-model="formData.unit_of_measure" class="col-span-3" />
        </div>
        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="category" class="text-right">Categoría</Label>
          <Select v-model="formData.category_id">
            <SelectTrigger class="col-span-3">
              <SelectValue placeholder="Selecciona una categoría..." />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem v-for="cat in categories" :key="cat.id" :value="cat.id">
                  {{ cat.name }}
                </SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>
      </div>
      <DialogFooter>
        <Button variant="secondary" @click="closeModal">Cancelar</Button>
        <Button @click="handleFormSubmit" :disabled="isSubmitting">
          <Loader2 v-if="isSubmitting" class="h-4 w-4 animate-spin mr-2" />
          Guardar Producto
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
