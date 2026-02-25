<script setup>
import { ref, watch, onMounted, computed } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { PlusCircle, Edit, Trash2 } from 'lucide-vue-next' // Added Trash2 icon for details
import { format } from 'date-fns'
import { useToast } from '@/components/ui/toast/use-toast'

import RenderDetailForm from './RenderDetailForm.vue' // New import

const props = defineProps({
  isOpen: Boolean,
  allocationId: Number,
  renderToEdit: Object // { id, amount, description, cost_center_id, details: [...] }
})

const emit = defineEmits(['update:isOpen', 'render-saved'])
const { getAccessTokenSilently } = useAuth0()
const { toast } = useToast()

const form = ref({
  correlative: '',
  amount: 0,
  description: '',
  cost_center_id: null,
  details: [] // Initialize details array
})
const isLoading = ref(false)
const costCenters = ref([])

// State for RenderDetailForm
const isDetailFormOpen = ref(false)
const detailToEdit = ref(null) // Holds the detail object being edited, or null for new

const dialogTitle = computed(() => (props.renderToEdit ? 'Editar Rendición' : 'Nueva Rendición'))

const totalDetailsAmount = computed(() => {
  return form.value.details.reduce((sum, detail) => sum + (Number(detail.amount) || 0), 0)
})

watch(totalDetailsAmount, (newVal) => {
  form.value.amount = newVal
})

// --- Watchers ---
watch(() => props.isOpen, (newVal) => {
      if (newVal) {
      resetForm()
      if (props.renderToEdit) {
        // Populate form for editing
        form.value = {
          correlative: props.renderToEdit.correlative || '',
          amount: props.renderToEdit.amount,
          description: props.renderToEdit.description,
          cost_center_id: props.renderToEdit.cost_center_id,
          details: props.renderToEdit.details ? props.renderToEdit.details.map(d => ({ ...d, date: new Date(d.date) })) : []
        }
      }
    }
  })
  
  const selectedCostCenterCode = computed(() => {
    const selected = costCenters.value.find(cc => cc.id === form.value.cost_center_id)
    return selected ? selected.code : 'Selecciona un centro de costo'
  })
  
  // --- Methods ---
  function openDetailFormForNew() {
    detailToEdit.value = null // For new detail
    isDetailFormOpen.value = true
  }

  function openDetailFormForEdit(detail) {
    detailToEdit.value = { ...detail } // Clone for editing
    isDetailFormOpen.value = true
  }
  
  function removeDetailItem(index) {
    form.value.details.splice(index, 1)
  }

  function handleDetailSaved(savedDetail) {
    if (savedDetail.id) {
        // Update existing detail
        const index = form.value.details.findIndex(d => d.id === savedDetail.id)
        if (index !== -1) {
            form.value.details[index] = savedDetail
        }
    } else {
        // Add new detail
        // Assign a temporary ID for client-side tracking if it's a new item without a backend ID yet
        // In a real app, you might use a UUID or ensure backend assigns IDs upon creation
        form.value.details.push({ ...savedDetail, id: Date.now() }) 
    }
    isDetailFormOpen.value = false
    detailToEdit.value = null // Clear edit state
  }
  
  function resetForm() {
    form.value = {
      correlative: '',
      amount: 0,
      description: '',
      cost_center_id: null,
      details: []
    }
  }

async function fetchCostCenters() {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/cost-centers/`, { // Assuming this endpoint exists
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.ok) {
      costCenters.value = await response.json()
    } else {
      console.error('Error fetching cost centers:', await response.json())
    }
  } catch (error) {
    console.error('Error fetching cost centers:', error)
  }
}

async function handleSubmit() {
  console.log('handleSubmit triggered')
  isLoading.value = true
  try {
    const token = await getAccessTokenSilently()
    const url = props.renderToEdit
      ? `${import.meta.env.VITE_API_URL}/api/treasury/renders/${props.renderToEdit.id}`
      : `${import.meta.env.VITE_API_URL}/api/treasury/transactions/${props.allocationId}/renders`
    const method = props.renderToEdit ? 'PUT' : 'POST'

    const payload = {
      correlative: form.value.correlative,
      amount: form.value.amount,
      description: form.value.description,
      cost_center_id: form.value.cost_center_id,
      document: null, // Document feature removed
      details: form.value.details.map(d => {
          const detailPayload = {
              ...d,
              date: d.date.getFullYear() + '-' + String(d.date.getMonth() + 1).padStart(2, '0') + '-' + String(d.date.getDate()).padStart(2, '0'),
              provider_id: d.provider_id || null,
          };
          // Remove temporary ID if it was assigned client-side
          if (typeof detailPayload.id === 'number' && detailPayload.id > 1000000000000) { // Assuming Date.now() IDs are large numbers
              delete detailPayload.id;
          }
          return detailPayload;
      })
    }

    console.log('Payload:', payload)

    const response = await fetch(url, {
      method: method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })

    console.log('API response OK:', response.ok)

    if (response.ok) {
      emit('render-saved')
      emit('update:isOpen', false)
    } else {
      const errorData = await response.json()
      toast({
        title: 'Error',
        description: errorData.error || 'No se pudo guardar la rendición.',
        variant: 'destructive'
      })
    }
  } catch (error) {
    console.error('Error saving render:', error)
    toast({
      title: 'Error de conexión',
      description: 'Ocurrió un error al conectar con el servidor.',
      variant: 'destructive'
    })
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchCostCenters()
})
</script>

<template>
  <Dialog :open="isOpen" @update:open="(val) => emit('update:isOpen', val)">
    <DialogContent class="sm:max-w-4xl">
      <DialogHeader>
        <DialogTitle>{{ dialogTitle }}</DialogTitle>
        <DialogDescription>
          Completa los detalles de la rendición.
        </DialogDescription>
      </DialogHeader>

      <form @submit.prevent="handleSubmit" class="grid grid-cols-2 gap-4 py-4">
        <div class="space-y-2">
          <Label for="description" class="text-left">Descripción</Label>
          <Textarea id="description" v-model="form.description" class="w-full" required />
        </div>
        <div class="space-y-2">
          <Label for="correlative" class="text-left">Correlativo</Label>
          <Input id="correlative" v-model="form.correlative" class="w-full" required />
        </div>
        <div class="space-y-2">
          <Label for="amount" class="text-left">Monto</Label>
          <Input id="amount" v-model.number="form.amount" type="number" step="0.01" class="w-full" required readonly />
        </div>
        <div class="space-y-2">
          <Label for="cost_center" class="text-left">Centro de Costo</Label>
          <Select v-model="form.cost_center_id" class="w-full">
            <SelectTrigger>
              <SelectValue>{{ selectedCostCenterCode }}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="cc in costCenters" :key="cc.id" :value="cc.id">
                {{ cc.code }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>


        <!-- Details Section -->
        <div class="col-span-2">
            <h4 class="text-md font-semibold mt-4 border-b pb-2">Detalles de Rendición</h4>
            <div v-if="form.details.length" class="space-y-2 mt-2">
                <div v-for="(detail, index) in form.details" :key="detail.id || index" class="flex items-center justify-between border p-2 rounded-md">
                    <span>
                        {{ detail.description }} - {{ detail.amount }}
                    </span>
                    <div class="flex gap-2">
                        <Button type="button" variant="ghost" size="sm" @click="openDetailFormForEdit(detail)">
                            <Edit class="w-4 h-4" />
                        </Button>
                        <Button type="button" variant="destructive" size="sm" @click="removeDetailItem(index)">
                            <Trash2 class="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            </div>
            <p v-else class="text-muted-foreground mt-2">No hay detalles agregados.</p>
            <Button type="button" variant="outline" class="mt-4" @click="openDetailFormForNew">
                <PlusCircle class="w-4 h-4 mr-2" /> Agregar Detalle
            </Button>
        </div>
        
        <DialogFooter class="col-span-2 mt-4">
          <Button type="button" variant="outline" @click="emit('update:isOpen', false)">
            Cancelar
          </Button>
          <Button type="submit" :disabled="isLoading">
            {{ isLoading ? 'Guardando...' : 'Guardar Rendición' }}
          </Button>
        </DialogFooter>
      </form>

      <RenderDetailForm 
        v-model:isOpen="isDetailFormOpen"
        :detail-to-edit="detailToEdit"
        @detail-saved="handleDetailSaved"
      />
    </DialogContent>
  </Dialog>
</template>
