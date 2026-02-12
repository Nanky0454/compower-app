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
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Calendar as CalendarIcon, Search } from 'lucide-vue-next'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'
import { useToast } from '@/components/ui/toast/use-toast'
import { Checkbox } from '@/components/ui/checkbox'

const props = defineProps({
  isOpen: Boolean,
  allocationId: Number,
  renderToEdit: Object // { id, amount, description, cost_center_id, document: { ... } }
})

const emit = defineEmits(['update:isOpen', 'render-saved'])
const { getAccessTokenSilently } = useAuth0()
const { toast } = useToast()

const form = ref({
  amount: 0,
  description: '',
  cost_center_id: null,
  document: {
    document_type_id: null,
    series: '',
    number: '',
    issuer_ruc: '',
    issuer_name: '',
    issue_date: new Date(),
    amount: 0
  }
})
const isLoading = ref(false)
const costCenters = ref([])
const documentTypes = ref([])
const rucSearchTerm = ref('')
const rucSearchResults = ref([])
const selectedProvider = ref(null) // Provider found by RUC search

const isDocumentFormOpen = ref(false)

const dialogTitle = computed(() => (props.renderToEdit ? 'Editar Rendición' : 'Nueva Rendición'))

// --- Watchers ---
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    resetForm()
    if (props.renderToEdit) {
      // Populate form for editing
      form.value = {
        amount: props.renderToEdit.amount,
        description: props.renderToEdit.description,
        cost_center_id: props.renderToEdit.cost_center_id,
        document: props.renderToEdit.document ? { ...props.renderToEdit.document } : {
          document_type_id: null,
          series: '',
          number: '',
          issuer_ruc: '',
          issuer_name: '',
          issue_date: new Date(),
          amount: 0
        }
      }
      if (props.renderToEdit.document) {
        form.value.document.issue_date = new Date(props.renderToEdit.document.issue_date)
        isDocumentFormOpen.value = true
        if (props.renderToEdit.document.issuer_ruc) {
          selectedProvider.value = {
            ruc: props.renderToEdit.document.issuer_ruc,
            name: props.renderToEdit.document.issuer_name
          }
        }
      }
    }
  }
})

watch(rucSearchTerm, (newVal) => {
  if (newVal.length === 11) { // Assuming RUC is 11 digits
    searchProviderByRUC(newVal)
  } else {
    selectedProvider.value = null
    form.value.document.issuer_name = ''
  }
})

const selectedCostCenterCode = computed(() => {
  const selected = costCenters.value.find(cc => cc.id === form.value.cost_center_id)
  return selected ? selected.code : 'Selecciona un centro de costo'
})

// --- Methods ---
function resetForm() {
  form.value = {
    amount: 0,
    description: '',
    cost_center_id: null,
    document: {
      document_type_id: null,
      series: '',
      number: '',
      issuer_ruc: '',
      issuer_name: '',
      issue_date: new Date(),
      amount: 0
    }
  }
  rucSearchTerm.value = ''
  rucSearchResults.value = []
  selectedProvider.value = null
  isDocumentFormOpen.value = false
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

async function fetchDocumentTypes() {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/document-types`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.ok) {
      documentTypes.value = await response.json()
    } else {
      console.error('Error fetching document types:', await response.json())
    }
  } catch (error) {
    console.error('Error fetching document types:', error)
  }
}

async function searchProviderByRUC(ruc) {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/lookup-provider/${ruc}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.ok) {
      const provider = await response.json()
      selectedProvider.value = provider
      form.value.document.issuer_name = provider.name
      form.value.document.issuer_ruc = provider.ruc
    } else {
      selectedProvider.value = null
      form.value.document.issuer_name = ''
      form.value.document.issuer_ruc = ruc // Keep RUC if not found, user might type manually
      toast({
        title: 'RUC no encontrado',
        description: 'No se encontró un proveedor con ese RUC. Puedes ingresar el nombre manualmente.',
        variant: 'warning'
      })
    }
  } catch (error) {
    console.error('Error searching provider by RUC:', error)
    selectedProvider.value = null
    form.value.document.issuer_name = ''
    form.value.document.issuer_ruc = ruc
    toast({
      title: 'Error de conexión',
      description: 'No se pudo buscar el proveedor por RUC.',
      variant: 'destructive'
    })
  }
}

async function handleSubmit() {
  isLoading.value = true
  try {
    const token = await getAccessTokenSilently()
    const url = props.renderToEdit
      ? `${import.meta.env.VITE_API_URL}/api/treasury/renders/${props.renderToEdit.id}`
      : `${import.meta.env.VITE_API_URL}/api/treasury/transactions/${props.allocationId}/renders`
    const method = props.renderToEdit ? 'PUT' : 'POST'

    // Only send document if the form is open and data is present
    const payload = {
      amount: form.value.amount,
      description: form.value.description,
      cost_center_id: form.value.cost_center_id,
      document: isDocumentFormOpen.value ? {
        document_type_id: form.value.document.document_type_id,
        series: form.value.document.series,
        number: form.value.document.number,
        issuer_ruc: form.value.document.issuer_ruc,
        issuer_name: form.value.document.issuer_name,
        issue_date: form.value.document.issue_date ? format(form.value.document.issue_date, 'yyyy-MM-dd') : null,
        amount: form.value.document.amount
      } : null
    }

    const response = await fetch(url, {
      method: method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })

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
  fetchDocumentTypes()
})
</script>

<template>
  <Dialog :open="isOpen" @update:open="(val) => emit('update:isOpen', val)">
    <DialogContent class="sm:max-w-[700px]">
      <DialogHeader>
        <DialogTitle>{{ dialogTitle }}</DialogTitle>
        <DialogDescription>
          Completa los detalles de la rendición.
        </DialogDescription>
      </DialogHeader>

      <form @submit.prevent="handleSubmit" class="grid gap-4 py-4">
        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="description" class="text-right">Descripción</Label>
          <Textarea id="description" v-model="form.description" class="col-span-3" required />
        </div>
        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="amount" class="text-right">Monto</Label>
          <Input id="amount" v-model.number="form.amount" type="number" step="0.01" class="col-span-3" required />
        </div>
        <div class="grid grid-cols-4 items-center gap-4">
          <Label for="cost_center" class="text-right">Centro de Costo</Label>
          <Select v-model="form.cost_center_id" class="col-span-3">
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

        <!-- Document Section -->
        <div class="col-span-4 flex items-center mt-4">
            <Checkbox id="hasDocument" v-model:checked="isDocumentFormOpen" />
            <Label for="hasDocument" class="ml-2">Asociar Documento</Label>
        </div>

        <template v-if="isDocumentFormOpen">
            <h4 class="col-span-4 text-md font-semibold mt-4 border-b pb-2">Detalles del Documento</h4>
            
            <div class="grid grid-cols-4 items-center gap-4">
                <Label for="doc_type" class="text-right">Tipo Doc.</Label>
                <Select v-model="form.document.document_type_id" class="col-span-3" :required="isDocumentFormOpen">
                    <SelectTrigger>
                        <SelectValue placeholder="Selecciona tipo de documento" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem v-for="dt in documentTypes" :key="dt.id" :value="dt.id">
                            {{ dt.name }}
                        </SelectItem>
                    </SelectContent>
                </Select>
            </div>

            <div class="grid grid-cols-4 items-center gap-4">
                <Label for="doc_series" class="text-right">Serie</Label>
                <Input id="doc_series" v-model="form.document.series" class="col-span-1" :required="isDocumentFormOpen" />
                <Label for="doc_number" class="text-right">Número</Label>
                <Input id="doc_number" v-model="form.document.number" class="col-span-1" :required="isDocumentFormOpen" />
            </div>

            <div class="grid grid-cols-4 items-center gap-4">
                <Label for="issuer_ruc" class="text-right">RUC Emisor</Label>
                <div class="col-span-3 flex gap-2">
                    <Input id="issuer_ruc" v-model="rucSearchTerm" placeholder="RUC del emisor" class="flex-grow" :required="isDocumentFormOpen" />
                    <Button type="button" @click="searchProviderByRUC(rucSearchTerm)" variant="outline" size="icon">
                        <Search class="w-4 h-4" />
                    </Button>
                </div>
            </div>

            <div class="grid grid-cols-4 items-center gap-4">
                <Label for="issuer_name" class="text-right">Razón Social</Label>
                <Input id="issuer_name" v-model="form.document.issuer_name" class="col-span-3" :required="isDocumentFormOpen" />
            </div>

            <div class="grid grid-cols-4 items-center gap-4">
                <Label for="issue_date" class="text-right">Fecha Emisión</Label>
                <Popover class="col-span-3">
                  <PopoverTrigger as-child>
                    <Button
                      variant="outline"
                      :class="cn(
                        'w-[280px] justify-start text-left font-normal',
                        !form.document.issue_date && 'text-muted-foreground',
                      )"
                      :required="isDocumentFormOpen"
                    >
                      <CalendarIcon class="mr-2 h-4 w-4" />
                      {{ form.document.issue_date ? format(form.document.issue_date, 'PPP') : 'Selecciona una fecha' }}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent class="w-auto p-0">
                    <Calendar
                      v-model="form.document.issue_date"
                      initial-focus
                    />
                  </PopoverContent>
                </Popover>
            </div>

            <div class="grid grid-cols-4 items-center gap-4">
                <Label for="doc_amount" class="text-right">Monto Documento</Label>
                <Input id="doc_amount" v-model.number="form.document.amount" type="number" step="0.01" class="col-span-3" :required="isDocumentFormOpen" />
            </div>
        </template>

        <DialogFooter class="mt-4">
          <Button type="button" variant="outline" @click="emit('update:isOpen', false)">
            Cancelar
          </Button>
          <Button type="submit" :disabled="isLoading">
            {{ isLoading ? 'Guardando...' : 'Guardar Rendición' }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
