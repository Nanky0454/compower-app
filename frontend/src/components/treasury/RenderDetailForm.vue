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
import { Input } from '@/components/ui/input' // Keep Input for type="date"
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Search } from 'lucide-vue-next' // Keep Search icon
import { useToast } from '@/components/ui/toast/use-toast'

const props = defineProps({
  isOpen: Boolean,
  detailToEdit: Object
})

const emit = defineEmits(['update:isOpen', 'detail-saved'])
const { getAccessTokenSilently } = useAuth0()
const { toast } = useToast()

// Unified state for the form
const detailForm = ref({
  id: null,
  date: new Date().toISOString().split('T')[0], // Store date as YYYY-MM-DD string
  provider_id: null,
  issuer_ruc: '',
  issuer_name: '',
  invoice_series: '',
  invoice_number: '',
  description: '',
  amount: 0
})

const isLoading = ref(false)

const dialogTitle = computed(() => (props.detailToEdit ? 'Editar Detalle de Rendición' : 'Agregar Detalle de Rendición'))

// Watcher to populate form for editing or reset for new
watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    if (props.detailToEdit) {
      const d = props.detailToEdit;
      detailForm.value.id = d.id;
      detailForm.value.date = d.date ? new Date(d.date).toISOString().split('T')[0] : ''; // Format to YYYY-MM-DD
      detailForm.value.provider_id = d.provider_id;
      detailForm.value.issuer_ruc = d.issuer_ruc || '';
      detailForm.value.issuer_name = d.issuer_name || '';
      detailForm.value.invoice_series = d.invoice_series || '';
      detailForm.value.invoice_number = d.invoice_number || '';
      detailForm.value.description = d.description || '';
      detailForm.value.amount = d.amount || 0;
    } else {
      resetDetailForm();
    }
  }
});

// Watcher for auto-searching RUC
watch(() => detailForm.value.issuer_ruc, (newVal) => {
  if (newVal && newVal.length === 11) {
    searchProviderByRUC();
  }
});

function resetDetailForm() {
  detailForm.value = {
    id: null,
    date: new Date().toISOString().split('T')[0], // Store date as YYYY-MM-DD string
    provider_id: null,
    issuer_ruc: '',
    issuer_name: '',
    invoice_series: '',
    invoice_number: '',
    description: '',
    amount: 0
  }
}

async function searchProviderByRUC() {
  const ruc = detailForm.value.issuer_ruc;
  if (!ruc || ruc.length !== 11) {
    toast({ title: 'RUC inválido', description: 'El RUC debe tener 11 dígitos.', variant: 'warning' });
    return;
  }
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/lookup-provider/${ruc}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.ok) {
      const provider = await response.json()
      detailForm.value.provider_id = provider.id
      detailForm.value.issuer_name = provider.name
    } else {
      toast({
        title: 'RUC no encontrado',
        description: 'Puedes ingresar la Razón Social manualmente.',
        variant: 'warning'
      })
    }
  } catch (error) {
    console.error('Error searching provider by RUC:', error)
    toast({
      title: 'Error de conexión',
      description: 'No se pudo buscar el proveedor por RUC.',
      variant: 'destructive'
    })
  }
}

function handleSaveDetail() {
  emit('detail-saved', { ...detailForm.value })
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
          <Input id="detail-date" type="date" v-model="detailForm.date" class="w-full" />
        </div>
            
        <div>
            <Label for="detail-provider-ruc" class="text-left">RUC Proveedor</Label>
            <div class="flex gap-2">
                <Input id="detail-provider-ruc" v-model="detailForm.issuer_ruc" placeholder="RUC del proveedor" class="flex-grow" />
                <Button type="button" @click="searchProviderByRUC" variant="outline" size="icon">
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
