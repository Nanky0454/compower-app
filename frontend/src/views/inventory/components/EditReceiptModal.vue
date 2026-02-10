<script setup>
import { ref, onMounted, reactive, watch } from 'vue'
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Loader2, Search } from 'lucide-vue-next'
import { useAuth0 } from '@auth0/auth0-vue'

const props = defineProps({
  open: Boolean,
  receipt: Object
})

const emit = defineEmits(['update:open', 'receipt-updated'])

const { getAccessTokenSilently } = useAuth0()
const FLASK_API_URL = `${import.meta.env.VITE_API_URL}/api`

const formData = reactive({
  id: null,
  invoice_number: '',
  provider_id: null,
  cost_center_id: null,
  provider_search: ''
})

const costCenters = ref([])
const providerResults = ref([])
const showProviderResults = ref(false)
const isSearchingProvider = ref(false)
const isSubmitting = ref(false)
let searchTimeout = null

// Load catalogs when component is mounted
onMounted(async () => {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/purchases/catalogs`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      const catalogs = await res.json()
      costCenters.value = catalogs.cost_centers
    }
  } catch (e) {
    console.error('Error loading cost centers:', e)
  }
})

// Watch for changes in the receipt prop to populate the form
watch(() => props.receipt, (newReceipt) => {
  if (newReceipt) {
    formData.id = newReceipt.id
    formData.invoice_number = newReceipt.invoice_number
    formData.provider_id = newReceipt.provider_id // Assuming this is available
    formData.cost_center_id = newReceipt.cost_center_id // Assuming this is available
    formData.provider_search = newReceipt.provider_name
  }
}, { immediate: true })

function handleProviderSearch() {
  const q = formData.provider_search.trim()
  if (!q) {
    providerResults.value = []
    showProviderResults.value = false
    return
  }
  isSearchingProvider.value = true

  if (searchTimeout) clearTimeout(searchTimeout)

  searchTimeout = setTimeout(async () => {
    try {
      const token = await getAccessTokenSilently()
      const res = await fetch(`${FLASK_API_URL}/purchases/providers?q=${q}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (res.ok) {
        providerResults.value = await res.json()
        showProviderResults.value = providerResults.value.length > 0
      }
    } catch (e) {
      console.error(e)
      providerResults.value = []
      showProviderResults.value = false
    } finally {
      isSearchingProvider.value = false
    }
  }, 400)
}

function selectProvider(p) {
  formData.provider_id = p.id
  formData.provider_search = p.name
  showProviderResults.value = false
}

async function handleUpdate() {
  isSubmitting.value = true
  try {
    const token = await getAccessTokenSilently()
    const payload = {
      invoice_number: formData.invoice_number,
      provider_id: formData.provider_id,
      cost_center_id: formData.cost_center_id,
    }
    const response = await fetch(`${FLASK_API_URL}/inventory/receipts/${formData.id}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })
    if (!response.ok) {
      throw new Error('Failed to update receipt')
    }
    emit('receipt-updated')
    emit('update:open', false)
  } catch (error) {
    console.error('Error updating receipt:', error)
    // Optionally show an error message to the user
  } finally {
    isSubmitting.value = false
  }
}

</script>

<template>
  <Dialog :open="open" @update:open="(value) => emit('update:open', value)">
    <DialogContent class="sm:max-w-[425px]">
      <DialogHeader>
        <DialogTitle>Editar Recepción</DialogTitle>
        <DialogDescription>
          Modifica los detalles de la recepción. Haz clic en 'Guardar Cambios' cuando termines.
        </DialogDescription>
      </DialogHeader>
      <div class="grid gap-4 py-4">
        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="invoice" class="text-right">
            N° Factura
          </Label>
          <Input id="invoice" v-model="formData.invoice_number" class="col-span-3" />
        </div>

        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="provider" class="text-right">
            Proveedor
          </Label>
          <div class="col-span-3 relative">
            <Search class="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
            <Input id="provider" v-model="formData.provider_search" @input="handleProviderSearch" placeholder="Buscar por RUC o nombre..." class="pl-9" />
            <Loader2 v-if="isSearchingProvider" class="absolute right-3 top-2.5 h-4 w-4 animate-spin text-gray-400" />
             <div v-if="showProviderResults" class="absolute z-10 w-full bg-white border rounded-md shadow-lg mt-1 max-h-60 overflow-y-auto">
                <div v-for="p in providerResults" :key="p.id" @click="selectProvider(p)" class="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-0">
                    <div class="font-bold text-sm">{{ p.name }}</div>
                    <div class="text-xs text-gray-500">RUC: {{ p.ruc }}</div>
                </div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="cost-center" class="text-right">
            Centro de Costo
          </Label>
           <Select v-model="formData.cost_center_id" class="col-span-3">
             <SelectTrigger><SelectValue placeholder="Seleccione..." /></SelectTrigger>
             <SelectContent>
                <SelectItem v-for="cc in costCenters" :key="cc.id" :value="cc.id">
                  {{ cc.code }} - {{ cc.name }}
                </SelectItem>
             </SelectContent>
           </Select>
        </div>

      </div>
      <DialogFooter>
        <DialogClose as-child>
          <Button type="button" variant="secondary">
            Cancelar
          </Button>
        </DialogClose>
        <Button @click="handleUpdate" :disabled="isSubmitting">
          <Loader2 v-if="isSubmitting" class="w-4 h-4 mr-2 animate-spin" />
          Guardar Cambios
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>