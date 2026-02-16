<script setup>
import { ref, watch, computed } from 'vue'
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
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Calendar as CalendarIcon, Search } from 'lucide-vue-next'
import { cn } from '@/lib/utils'
import { format } from 'date-fns'
import { useToast } from '@/components/ui/toast/use-toast'

const props = defineProps({
  isOpen: Boolean,
  detailToEdit: Object // { id, date, provider_id, issuer_ruc, issuer_name, invoice_series, invoice_number, description, amount }
})

const emit = defineEmits(['update:isOpen', 'detail-saved'])
const { getAccessTokenSilently } = useAuth0()
const { toast } = useToast()

const detailForm = ref({
  id: null,
  date: new Date(),
  provider_id: null,
  issuer_ruc: '',
  issuer_name: '',
  invoice_series: '',
  invoice_number: '',
  description: '',
  amount: 0
})
const isLoading = ref(false)
const rucSearchTerm = ref('') // Used for searching provider by RUC
const selectedProvider = ref(null) // Provider found by RUC search
const isDatePopoverOpen = ref(false) // Control for date picker popover

const dialogTitle = computed(() => (props.detailToEdit ? 'Editar Detalle de Rendición' : 'Agregar Detalle de Rendición'))

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    resetDetailForm()
    if (props.detailToEdit) {
      detailForm.value = { ...props.detailToEdit, date: new Date(props.detailToEdit.date) }
      if (props.detailToEdit.issuer_ruc) {
        rucSearchTerm.value = props.detailToEdit.issuer_ruc
        selectedProvider.value = {
            ruc: props.detailToEdit.issuer_ruc,
            name: props.detailToEdit.issuer_name
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
    detailForm.value.issuer_name = ''
  }
})

function resetDetailForm() {
  detailForm.value = {
    id: null,
    date: new Date(),
    provider_id: null,
    issuer_ruc: '',
    issuer_name: '',
    invoice_series: '',
    invoice_number: '',
    description: '',
    amount: 0
  }
  rucSearchTerm.value = ''
  selectedProvider.value = null
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
      detailForm.value.provider_id = provider.id
      detailForm.value.issuer_name = provider.name
    } else {
      selectedProvider.value = null
      detailForm.value.provider_id = null
      detailForm.value.issuer_name = ''
      toast({
        title: 'RUC no encontrado',
        description: 'No se encontró un proveedor con ese RUC.',
        variant: 'warning'
      })
    }
  } catch (error) {
    console.error('Error searching provider by RUC:', error)
    selectedProvider.value = null
    detailForm.value.provider_id = null
    detailForm.value.issuer_name = ''
    toast({
      title: 'Error de conexión',
      description: 'No se pudo buscar el proveedor por RUC.',
      variant: 'destructive'
    })
  }
}

function handleSaveDetail() {
  emit('detail-saved', { ...detailForm.value, date: format(detailForm.value.date, 'yyyy-MM-dd') })
  emit('update:isOpen', false)
}
</script>

<template>
  <Dialog :open="isOpen" @update:open="(val) => emit('update:isOpen', val)">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ dialogTitle }}</DialogTitle>
        <DialogDescription>
          Ingresa los detalles de la rendición.
        </DialogDescription>
      </DialogHeader>

      <form @submit.prevent="handleSaveDetail" class="grid gap-4 py-4">
        <div>
          <Label for="detail-date" class="text-left">Fecha</Label>
          <Popover v-model:open="isDatePopoverOpen">
            <PopoverTrigger as-child>
              <Button
                variant="outline"
                :class="cn(
                  'w-full justify-start text-left font-normal',
                  !detailForm.date && 'text-muted-foreground',
                )"
                @click.stop
              >
                <CalendarIcon class="mr-2 h-4 w-4" />
                {{ detailForm.date ? format(detailForm.date, 'PPP') : 'Selecciona una fecha' }}
              </Button>
            </PopoverTrigger>
            <PopoverContent class="w-auto p-0">
              <Calendar
                v-model="detailForm.date"
                @update:modelValue="isDatePopoverOpen = false"
              />
            </PopoverContent>
          </Popover>
        </div>
            
        <div>
            <Label for="detail-provider-ruc" class="text-left">RUC Proveedor</Label>
            <div class="flex gap-2">
                <Input id="detail-provider-ruc" v-model="rucSearchTerm" placeholder="RUC del proveedor" class="flex-grow" @input="searchProviderByRUC(rucSearchTerm)" />
                <Button type="button" @click="searchProviderByRUC(rucSearchTerm)" variant="outline" size="icon">
                    <Search class="w-4 h-4" />
                </Button>
            </div>
        </div>

        <div>
            <Label for="detail-provider-name" class="text-left">Razón Social</Label>
            <Input id="detail-provider-name" v-model="detailForm.issuer_name" class="w-full" />
        </div>

        <div class="grid grid-cols-2 gap-2">
            <div>
                <Label for="detail-series" class="text-left">Serie Factura</Label>
                <Input id="detail-series" v-model="detailForm.invoice_series" class="w-full" />
            </div>
            <div>
                <Label for="detail-number" class="text-left">Nro Factura</Label>
                <Input id="detail-number" v-model="detailForm.invoice_number" class="w-full" />
            </div>
        </div>

        <div>
            <Label for="detail-description" class="text-left">Descripción</Label>
            <Textarea id="detail-description" v-model="detailForm.description" class="w-full" />
        </div>

        <div>
            <Label for="detail-amount" class="text-left">Monto</Label>
            <Input id="detail-amount" v-model.number="detailForm.amount" type="number" step="0.01" class="w-full" />
        </div>

        <DialogFooter class="mt-4">
          <Button type="button" variant="outline" @click="emit('update:isOpen', false)">
            Cancelar
          </Button>
          <Button type="submit" :disabled="isLoading">
            {{ isLoading ? 'Guardando...' : 'Guardar Detalle' }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
