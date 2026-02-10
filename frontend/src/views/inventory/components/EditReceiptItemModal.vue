<script setup>
import { ref, reactive, watch } from 'vue'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader2 } from 'lucide-vue-next'

const props = defineProps({
  open: Boolean,
  item: Object
})

const emit = defineEmits(['update:open', 'save'])

const formData = reactive({
  id: null,
  product_name: '',
  quantity: 0,
  unit_price: 0
})

const isSubmitting = ref(false)

watch(() => props.item, (newItem) => {
  if (newItem) {
    formData.id = newItem.id
    formData.product_name = newItem.product_name
    formData.quantity = newItem.quantity
    formData.unit_price = newItem.unit_price
  }
}, { immediate: true, deep: true })

function handleSubmit() {
    isSubmitting.value = true
    // Pass only the fields that should be updated
    const payload = {
        id: formData.id,
        quantity: formData.quantity,
        unit_price: formData.unit_price
    }
    emit('save', payload)
    // The parent will handle closing the dialog on success
    isSubmitting.value = false
}

</script>

<template>
  <Dialog :open="open" @update:open="(value) => emit('update:open', value)">
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>Editar Ítem de Recepción</DialogTitle>
        <DialogDescription>
          Ajusta la cantidad y/o el precio unitario para el ítem:
          <span class="font-semibold">{{ formData.product_name }}</span>.
        </DialogDescription>
      </DialogHeader>
      <div class="grid gap-4 py-4">

        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="quantity" class="text-right">
            Cantidad
          </Label>
          <Input id="quantity" type="number" v-model.number="formData.quantity" class="col-span-3" />
        </div>

        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="unit_price" class="text-right">
            P. Unitario
          </Label>
          <Input id="unit_price" type="number" v-model.number="formData.unit_price" class="col-span-3" />
        </div>

      </div>
      <DialogFooter>
        <DialogClose as-child>
          <Button type="button" variant="secondary">
            Cancelar
          </Button>
        </DialogClose>
        <Button @click="handleSubmit" :disabled="isSubmitting">
          <Loader2 v-if="isSubmitting" class="w-4 h-4 mr-2 animate-spin" />
          Guardar Cambios
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>