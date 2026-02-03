<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { useRouter } from 'vue-router'

// --- UI Components ---
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  Loader2, Plus, Trash2, Search, FileText, Wrench, ArrowLeft, Check,
  Eye, Contact, Download, ListTree, MapPin, Layers, Pencil, Ban, XCircle
} from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()
const router = useRouter()
const FLASK_API_URL = `${import.meta.env.VITE_API_URL}/api`

// --- ESTADOS DE LA VISTA ---
const viewMode = ref('list')
const isLoadingList = ref(true)
const purchaseOrders = ref([])
const downloadingOrderId = ref(null)

// --- DATOS SIMULADOS ---
const coordinators = ref([
  { id: '1', name: 'FABRIZIO ALARCON' },
  { id: '2', name: 'GERSON CALLAÑAUPA' },
  { id: '3', name: 'MARIA AYALA' },
  { id: '4', name: 'BRAULIO CASTILLO' },
  { id: '5', name: 'ROSARIO CUEVAS' },
  { id: '6', name: 'GIANCARLO ZEGARRA' },
  { id: '7', name: 'PIERO NANQUEN' }
])

const getToday = () => {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// =============================================================================
//  LÓGICA DE LISTADO
// =============================================================================
async function fetchOrders() {
  isLoadingList.value = true
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/purchases/`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      purchaseOrders.value = await res.json()
    }
  } catch (e) {
    console.error("Error cargando compras:", e)
  } finally {
    isLoadingList.value = false
  }
}

function formatDate(dateString) {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function getStatusColor(status) {
  switch (status) {
    case 'Emitida': return 'bg-blue-100 text-blue-800'
    case 'Recibida': return 'bg-green-100 text-green-800'
    case 'Anulada': return 'bg-red-100 text-red-800'
    default: return 'bg-gray-100 text-gray-800'
  }
}

async function downloadPdf(order) {
  downloadingOrderId.value = order.id
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${FLASK_API_URL}/purchases/${order.id}/pdf`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error("Error generando PDF")
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Orden_${order.codigo || order.document_number}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (e) {
    alert("Error al descargar: " + e.message)
  } finally {
    downloadingOrderId.value = null
  }
}

function goToDetail(id) {
  router.push({ name: 'PurchaseDetail', params: { id } })
}
function goToEdit(id) {
  router.push({ name: 'EditPurchase', params: { id } })
}

// =============================================================================
//  LÓGICA DE CREACIÓN
// =============================================================================

const isSubmitting = ref(false)
const catalogs = ref({ document_types: [], statuses: [], cost_centers: [] })
const correlativeSeries = ref('026')
const correlativeNumber = ref(1)
const isFetchingCorrelative = ref(false)
const selectedType = ref('OC')

const formData = reactive({
  provider_id: null,
  provider_search: '',
  provider_data: null,
  cost_center_id: null,
  reference: '',
  attention: '',
  provider_contact: '',
  coordinator_id: '',

  // Fechas
  issue_date: getToday(),
  transfer_date: getToday(),
  start_date: getToday(),
  end_date: getToday(),

  payment_condition: '',
  currency: 'PEN',
  site: '',

  items: [],
  os_groups: [],
  service_includes: [],

  // Condiciones
  penalty: '',
  commercial_conditions: [],

  // --- NUEVO: NOTA AL PIE ---
  footer_note: '',

  scope: ''
})

const providerResults = ref([])
const showProviderResults = ref(false)
const isSearchingProvider = ref(false)
let searchTimeout = null

// --- TEXTOS POR DEFECTO ---
const DEFAULT_PENALTY = "Penalidad: 5% por día de atraso, hasta un total de 15%, después del cual la OC será automáticamente anulada y liquidada."
const DEFAULT_CONDITIONS = [
    "El contratista será responsable de proveer los implementos de seguridad, SCTR para su ingreso y documentos de SST para su respectivo llenado a su personal.",
    "Ambas partes acuerdan que toda información y documentación será considerada confidencial, no será divulgada a terceros sin consentimiento, no utilizarla para fines distintos a los establecidos en esta orden de compra.",
    "El contratista se compromete a cumplir con todas la leyes, regulaciones y normas de medio ambiente según apliquen en esta orden de compra.",
    "El número de esta orden de compra deberá estar claramente indicado en las facturas correspondientes al servicio ejecutado. Asimismo el contratista deberá comunicar recibo de esta orden de compra inmediatamente después de su recepción en los correos a mayala@compower.pe, jbarbachan@compower.pe. Cada factura deberá adjuntar su OC y el % de la misma, más el acumulado."
]

// --- NOTA POR DEFECTO ---
const DEFAULT_FOOTER_NOTE = `Nota: La orden de compra es nula sin todas las firmas necesarias.
Toda factura deberá incluir el número de orden de compra y centro de costo correspondiente.
Solo se recibirán documentos de pago (facturas) los días miércoles de 9:00 a 16:00. De enviar el documento fuera de día indicado será programado para la semana siguiente.`

// --- COMPUTED ---
const formattedCorrelative = computed(() => {
  const num = String(correlativeNumber.value).padStart(3, '0')
  return `${correlativeSeries.value}-${num}`
})

const subtotal = computed(() => {
  if (selectedType.value === 'OC') {
    return formData.items.reduce((acc, item) => acc + (parseFloat(item.quantity || 0) * parseFloat(item.unit_price || 0)), 0)
  } else {
    let totalOS = 0
    formData.os_groups.forEach(group => {
      group.items.forEach(item => {
        totalOS += (parseFloat(item.quantity || 0) * parseFloat(item.unit_price || 0))
      })
    })
    return totalOS
  }
})

const igv = computed(() => subtotal.value * 0.18)
const total = computed(() => subtotal.value + igv.value)

// --- CICLO DE VIDA ---
onMounted(async () => {
  await fetchOrders()
  loadCatalogs()
})

// --- MÉTODOS DE VISTA ---
function switchToCreate() {
  viewMode.value = 'create'
  formData.items = []
  formData.os_groups = []
  formData.service_includes = []

  // Cargar valores por defecto
  formData.payment_condition = ""
  formData.penalty = DEFAULT_PENALTY
  formData.commercial_conditions = [...DEFAULT_CONDITIONS]

  // Cargar nota por defecto
  formData.footer_note = DEFAULT_FOOTER_NOTE

  formData.issue_date = getToday()

  if(selectedType.value === 'OC') addItem()
  else addOSGroup()

  fetchNextCorrelative()
}

function switchToList() {
  viewMode.value = 'list'
  fetchOrders()
}

// --- CARGA DE DATOS ---
async function loadCatalogs() {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/purchases/catalogs`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) catalogs.value = await res.json()
  } catch (e) { console.error(e) }
}

async function fetchNextCorrelative() {
  if (!correlativeSeries.value || correlativeSeries.value.length < 3) return
  isFetchingCorrelative.value = true
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/purchases/next-correlative/${correlativeSeries.value}`, {
       headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
        const data = await res.json()
        correlativeNumber.value = data.next_number
    }
  } catch(e) {
      console.warn("No se pudo obtener correlativo automático.")
  } finally {
      isFetchingCorrelative.value = false
  }
}

watch(correlativeSeries, (newVal) => {
    if(newVal.length === 3) fetchNextCorrelative()
})

watch(selectedType, (newType) => {
    if(newType === 'OC' && formData.items.length === 0) addItem()
    if(newType === 'OS' && formData.os_groups.length === 0) addOSGroup()
})

// --- BUSCADOR PROVEEDOR ---
async function handleProviderSearch() {
  const q = formData.provider_search.trim()
  if (!q) return
  isSearchingProvider.value = true
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(async () => {
    try {
      const token = await getAccessTokenSilently()
      if (/^\d{11}$/.test(q)) {
         const localRes = await fetch(`${FLASK_API_URL}/purchases/providers?q=${q}`, { headers: { 'Authorization': `Bearer ${token}` } })
         const localData = await localRes.json()
         if (localData.length > 0) {
            providerResults.value = localData
            showProviderResults.value = true
         } else {
            const sunatRes = await fetch(`${FLASK_API_URL}/purchases/lookup-provider/${q}`, { headers: { 'Authorization': `Bearer ${token}` } })
            if (sunatRes.ok) {
                const sunatData = await sunatRes.json()
                providerResults.value = [sunatData]
                showProviderResults.value = true
            } else { providerResults.value = [] }
         }
      } else {
         const res = await fetch(`${FLASK_API_URL}/purchases/providers?q=${q}`, { headers: { 'Authorization': `Bearer ${token}` } })
         if (res.ok) {
            providerResults.value = await res.json()
            showProviderResults.value = true
         }
      }
    } catch (e) { console.error(e) }
    finally { isSearchingProvider.value = false }
  }, 400)
}

function selectProvider(p) {
  formData.provider_id = p.id
  formData.provider_data = p
  formData.provider_search = p.name || p.razon_social
  formData.provider_contact = p.phone || p.email || ''
  showProviderResults.value = false
}

// --- GESTIÓN DE ITEMS (OC) ---
function addItem() {
  formData.items.push({ invoice_detail_text: '', um: 'UND', quantity: 1, unit_price: 0 })
}
function removeItem(index) {
  formData.items.splice(index, 1)
}

// --- GESTIÓN DE GRUPOS DE SERVICIO (OS) ---
function addOSGroup() {
  formData.os_groups.push({
    title: '',
    items: [ { invoice_detail_text: '', um: 'GLB', quantity: 1, unit_price: 0 } ]
  })
}
function removeOSGroup(index) {
  formData.os_groups.splice(index, 1)
}
function addOSItem(groupIndex) {
  formData.os_groups[groupIndex].items.push({ invoice_detail_text: '', um: 'UND', quantity: 1, unit_price: 0 })
}
function removeOSItem(groupIndex, itemIndex) {
  formData.os_groups[groupIndex].items.splice(itemIndex, 1)
}
function getGroupTotal(group) {
  return group.items.reduce((acc, item) => acc + (parseFloat(item.quantity || 0) * parseFloat(item.unit_price || 0)), 0)
}

// --- GESTIÓN DE "INCLUYE" ---
function addIncludeLine() {
  formData.service_includes.push({ text: '' })
}
function removeIncludeLine(index) {
  formData.service_includes.splice(index, 1)
}

// --- GESTIÓN DE "CONDICIONES COMERCIALES" ---
function addConditionLine() {
  formData.commercial_conditions.push('')
}
function removeConditionLine(index) {
  formData.commercial_conditions.splice(index, 1)
}

// --- GUARDAR ---
async function handleSubmit() {
  if (!formData.provider_search) {
    alert("Seleccione un proveedor.")
    return
  }

  isSubmitting.value = true
  try {
    const token = await getAccessTokenSilently()
    const docTypeName = selectedType.value === 'OC' ? 'Orden de Compra' : 'Orden de Servicio'
    const docType = catalogs.value.document_types.find(d => d.name.includes(docTypeName) || d.name === selectedType.value)
    const docTypeId = docType ? docType.id : 1
    const status = catalogs.value.statuses.find(s => s.name === 'Emitida') || catalogs.value.statuses[0]

    let itemsPayload = []

    if (selectedType.value === 'OC') {
        itemsPayload = formData.items.map(i => ({
            invoice_detail_text: i.invoice_detail_text,
            um: i.um,
            quantity: i.quantity,
            unit_price: i.unit_price
        }))
    } else {
        // OS: Aplanar
        formData.os_groups.forEach(group => {
            group.items.forEach(item => {
                itemsPayload.push({
                    group_name: group.title,
                    invoice_detail_text: item.invoice_detail_text,
                    um: item.um,
                    quantity: item.quantity,
                    unit_price: item.unit_price
                })
            })
        })
    }

    const complexScope = selectedType.value === 'OS' ? JSON.stringify({
        groups: formData.os_groups,
        includes: formData.service_includes
    }) : ''

    const finalConditions = [formData.penalty, ...formData.commercial_conditions].filter(c => c && c.trim() !== '')
    const conditionsJson = JSON.stringify(finalConditions)

    const payload = {
      document_number: formattedCorrelative.value,
      order_type: selectedType.value,
      provider_id: formData.provider_id,
      document_type_id: docTypeId,
      status_id: status.id,
      cost_center_id: formData.cost_center_id,
      reference: formData.reference,
      attention: formData.attention,
      provider_contact: formData.provider_contact,
      coordinator: formData.coordinator_id,
      site: formData.site,

      scope: complexScope,

      // Enviamos datos de textos largos
      commercial_conditions: conditionsJson,
      footer_note: formData.footer_note, // <--- NUEVO CAMPO ENVIADO

      payment_condition: formData.payment_condition,
      currency: formData.currency,

      issue_date: formData.issue_date,
      transfer_date: selectedType.value === 'OC' ? formData.transfer_date : null,
      start_date: selectedType.value === 'OS' ? formData.start_date : null,
      end_date: selectedType.value === 'OS' ? formData.end_date : null,

      items: itemsPayload
    }

    if(!payload.provider_id && formData.provider_data?.id) {
        payload.provider_id = formData.provider_data.id
    }

    const res = await fetch(`${FLASK_API_URL}/purchases/`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Error al guardar')
    }

    alert(`Orden ${formattedCorrelative.value} creada correctamente.`)
    switchToList()

  } catch (e) {
    alert(e.message)
  } finally {
    isSubmitting.value = false
  }
}

// =============================================================================
//  ACCIONES DE ESTADO (APROBAR / ANULAR)
// =============================================================================

async function handleApprove(order) {
  if (!confirm(`¿Estás seguro de APROBAR la orden ${order.codigo || order.document_number}?`)) return

  // Ponemos loading true para evitar doble clic visualmente
  isLoadingList.value = true
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/purchases/aprobar/${order.id}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })

    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error al aprobar la orden')

    alert(data.message)
    await fetchOrders() // Recargamos la lista para ver el cambio de estado

  } catch (e) {
    alert(e.message)
    isLoadingList.value = false // Restauramos loading si hubo error
  }
}

async function handleAnnul(order) {
  if (!confirm(`¿Estás seguro de ANULAR la orden ${order.codigo || order.document_number}?`)) return

  isLoadingList.value = true
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/purchases/anular/${order.id}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })

    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error al anular la orden')

    alert(data.message)
    await fetchOrders() // Recargamos la lista

  } catch (e) {
    alert(e.message)
    isLoadingList.value = false
  }
}

</script>

<template>
  <div class="max-w-7xl mx-auto p-6 space-y-6">

    <div v-if="viewMode === 'list'" class="space-y-6 animate-in fade-in">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-gray-900">Ordenes de Compras y Servicios</h1>
          <p class="text-sm text-gray-500">Historial de adquisiciones y contrataciones.</p>
        </div>
        <Button @click="switchToCreate" class="bg-blue-600 hover:bg-blue-700">
          <Plus class="w-4 h-4 mr-2" /> Nueva Orden
        </Button>
      </div>

      <Card>
        <CardContent class="p-0">
          <Table>
            <TableHeader>
              <TableRow class="bg-gray-50">
                <TableHead class="font-bold">Código</TableHead>
                <TableHead class="font-bold">Fecha</TableHead>
                <TableHead class="font-bold">Proveedor</TableHead>
                <TableHead class="font-bold">Tipo</TableHead>
                <TableHead class="font-bold">Estado</TableHead>
                <TableHead class="text-right font-bold">Total</TableHead>
                <TableHead class="text-center font-bold" >Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="order in purchaseOrders" :key="order.id" class="hover:bg-gray-50/50">
                <TableCell class="font-mono font-medium">{{ order.codigo }}</TableCell>
                <TableCell class="text-xs text-gray-500">{{ formatDate(order.fecha_emision) }}</TableCell>
                <TableCell>
                  <div class="text-sm font-medium">{{ order.provider_name }}</div>
                  <div class="text-xs text-gray-400">RUC: {{ order.ruc }}</div>
                </TableCell>
                <TableCell>
                  <span class="text-xs font-bold px-2 py-1 rounded"
                    :class="order.order_type === 'OS' ? 'bg-orange-50 text-orange-700' : 'bg-blue-50 text-blue-700'">
                    {{ order.order_type || 'OC' }}
                  </span>
                </TableCell>
                <TableCell>
                  <span class="px-2 py-1 rounded-full text-xs font-bold" :class="getStatusColor(order.status)">
                    {{ order.status }}
                  </span>
                </TableCell>
                <TableCell class="text-right font-mono">
                  {{ order.moneda }} {{ order.total_amount.toFixed(2) }}
                </TableCell>
                <TableCell class="text-center flex justify-center gap-2">
                  <Button
                      v-if="order.status === 'Borrador'"
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 text-green-600 hover:bg-green-50 hover:text-green-700"
                      title="Aprobar Orden"
                      @click="handleApprove(order)">
                     <Check class="w-4 h-4" />
                   </Button>

                  <Button
                      v-if="order.status === 'Borrador'"
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 text-blue-600 hover:bg-blue-50"
                      title="Editar Orden"
                      @click="goToEdit(order.id)">
                     <Pencil class="w-4 h-4" />
                   </Button>

                  <Button
                      v-if="order.status !== 'Anulada'"
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 text-red-400 hover:bg-red-50 hover:text-red-600"
                      title="Anular Orden"
                      @click="handleAnnul(order)">
                     <Ban class="w-4 h-4" />
                   </Button>

                  <Button
                      variant="ghost" size="icon"
                      class="h-8 w-8 text-gray-400 hover:text-gray-900"
                      title="Ver Detalle"
                      @click="goToDetail(order.id)">
                     <Eye class="w-4 h-4" />
                   </Button>

                   <Button
                      variant="ghost" size="icon"
                      class="h-8 w-8 text-gray-600 hover:text-gray-900"
                      title="Descargar PDF"
                      @click="downloadPdf(order)"
                      :disabled="downloadingOrderId === order.id"
                   >
                      <Loader2 v-if="downloadingOrderId === order.id" class="w-4 h-4 animate-spin" />
                      <Download v-else class="w-4 h-4" />
                   </Button>
                </TableCell>
              </TableRow>
              <TableRow v-if="!isLoadingList && purchaseOrders.length === 0">
                <TableCell colspan="7" class="h-24 text-center text-gray-500">No hay órdenes registradas aún.</TableCell>
              </TableRow>
              <TableRow v-if="isLoadingList">
                <TableCell colspan="7" class="h-24 text-center"><Loader2 class="w-6 h-6 animate-spin mx-auto text-gray-400"/></TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>

    <div v-else class="animate-in slide-in-from-right-4 duration-300">
      <div class="flex items-center gap-4 mb-6">
        <Button variant="outline" size="icon" @click="switchToList">
           <ArrowLeft class="w-4 h-4" />
        </Button>
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Nueva {{ selectedType === 'OC' ? 'Orden de Compra' : 'Orden de Servicio' }}</h1>
          <p class="text-sm text-gray-500">Complete los datos para generar el documento.</p>
        </div>

        <div class="ml-auto bg-gray-100 p-1 rounded-lg flex items-center shadow-inner">
            <button @click="selectedType = 'OC'"
              class="flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-bold transition-all"
              :class="selectedType === 'OC' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'">
              <FileText class="w-4 h-4" /> OC
            </button>
            <button @click="selectedType = 'OS'"
              class="flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-bold transition-all"
              :class="selectedType === 'OS' ? 'bg-white text-orange-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'">
              <Wrench class="w-4 h-4" /> OS
            </button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <div class="lg:col-span-2 space-y-6">

          <Card>
            <CardHeader class="pb-3 border-b py-3 bg-gray-50/50">
              <div class="flex justify-between items-center">
                <CardTitle class="text-sm font-bold uppercase text-gray-600">1. Datos Generales</CardTitle>
                <div class="flex items-center gap-2">
                    <div class="relative">
                        <Input type="date" v-model="formData.issue_date" class="h-8 w-32 text-xs"/>
                        <span class="absolute -bottom-4 left-0 w-full text-center text-[9px] text-gray-400" >EMISIÓN</span>
                    </div>

                    <div class="h-6 w-px bg-gray-300 mx-1"></div>

                    <div class="relative">
                        <Input v-model="correlativeSeries" class="h-8 w-16 text-center font-mono font-bold bg-blue-50 text-blue-700 border-blue-200" maxlength="3"  disabled />
                        <span class="absolute -bottom-4 left-0 w-full text-center text-[9px] text-gray-400">SERIE</span>
                    </div>
                    <span class="text-blue-300 font-bold">-</span>
                    <div class="relative">
                        <Input v-model="correlativeNumber" type="number" class="h-8 w-20 text-center font-mono font-bold bg-blue-50 text-blue-700 border-blue-200" min="1"  disabled />
                        <span class="absolute -bottom-4 left-0 w-full text-center text-[9px] text-gray-400">CORRELATIVO</span>
                    </div>
                    <Loader2 v-if="isFetchingCorrelative" class="w-4 h-4 animate-spin text-blue-400 ml-2" />
                </div>
              </div>
            </CardHeader>
            <CardContent class="pt-6 grid gap-4">
               <div class="grid grid-cols-2 gap-4">
                  <div class="relative">
                    <Label class="text-xs font-bold text-gray-500 uppercase">Proveedor</Label>
                    <div class="relative mt-1">
                      <Search class="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
                      <Input v-model="formData.provider_search" @input="handleProviderSearch" placeholder="Buscar RUC o Nombre..." class="pl-9"/>
                      <Loader2 v-if="isSearchingProvider" class="absolute right-3 top-2.5 h-4 w-4 animate-spin text-gray-400" />
                    </div>
                    <div v-if="showProviderResults" class="absolute z-10 w-full bg-white border rounded-md shadow-lg mt-1 max-h-60 overflow-y-auto">
                       <div v-for="p in providerResults" :key="p.ruc" @click="selectProvider(p)" class="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-0">
                          <div class="font-bold text-sm">{{ p.name || p.razon_social }}</div>
                          <div class="text-xs text-gray-500">RUC: {{ p.ruc || p.numero_documento }}</div>
                       </div>
                    </div>
                  </div>

                  <div>
                      <Label class="text-xs font-bold text-gray-500 uppercase">Solicitante</Label>
                      <Select v-model="formData.coordinator_id">
                        <SelectTrigger class="mt-1"><SelectValue placeholder="Seleccione..." /></SelectTrigger>
                        <SelectContent>
                          <SelectItem v-for="c in coordinators" :key="c.id" :value="c.name">{{ c.name }}</SelectItem>
                        </SelectContent>
                      </Select>
                  </div>
              </div>

              <div v-if="formData.provider_data" class="bg-blue-50/50 p-3 rounded text-sm space-y-1 border border-blue-100 text-blue-900">
                  <div class="font-bold">{{ formData.provider_data.name || formData.provider_data.razon_social }}</div>
                  <div class="text-xs opacity-75">RUC: {{ formData.provider_data.ruc }}</div>
              </div>

              <div class="bg-gray-50 p-3 rounded-lg border border-gray-100 space-y-3">
                 <Label class="text-xs font-bold text-gray-500 uppercase">Datos de Contacto</Label>
                 <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div class="md:col-span-2">
                        <Input v-model="formData.attention" placeholder="Atención a..." class="bg-white" />
                    </div>
                    <div class="md:col-span-2 relative">
                        <Contact class="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
                        <Input v-model="formData.provider_contact" placeholder="Teléfono / Email" class="pl-9 bg-white" />
                    </div>
                 </div>
              </div>

              <div>
                  <Label>Referencia (Cotización / Proyecto)</Label>
                  <Input v-model="formData.reference" class="mt-1" />
              </div>
            </CardContent>
          </Card>

          <Card v-if="selectedType === 'OC'">
             <CardHeader class="pb-3 border-b bg-gray-50/50 py-2 flex flex-row justify-between items-center">
               <CardTitle class="text-sm font-bold uppercase text-gray-600">2. Detalle de Items (OC)</CardTitle>
               <Button size="xs" variant="outline" @click="addItem"><Plus class="w-3 h-3 mr-1"/> Agregar</Button>
             </CardHeader>
             <CardContent class="p-0">
               <Table>
                 <TableHeader>
                   <TableRow>
                     <TableHead class="w-[40%]">Descripción</TableHead>
                     <TableHead class="w-[15%]">Und</TableHead>
                     <TableHead class="w-[15%] text-right">Cant</TableHead>
                     <TableHead class="w-[20%] text-right">P. Unit</TableHead>
                     <TableHead class="w-[10%]"></TableHead>
                   </TableRow>
                 </TableHeader>
                 <TableBody>
                   <TableRow v-for="(item, idx) in formData.items" :key="idx">
                     <TableCell class="p-2"><Input v-model="item.invoice_detail_text" class="h-8" /></TableCell>
                     <TableCell class="p-2">
                        <Select v-model="item.um">
                          <SelectTrigger class="h-8"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="PZA">PZA</SelectItem>
                            <SelectItem value="GLB">GLB</SelectItem>
                            <SelectItem value="MT">MT</SelectItem>
                            <SelectItem value="KG">KG</SelectItem>
                            <SelectItem value="M2">M2</SelectItem>
                            <SelectItem value="M3">M3</SelectItem>
                            <SelectItem value="JGO">JGO</SelectItem>
                            <SelectItem value="PQT">PQT</SelectItem>
                          </SelectContent>
                        </Select>
                     </TableCell>
                     <TableCell class="p-2"><Input type="number" v-model="item.quantity" class="h-8 text-right" min="1" /></TableCell>
                     <TableCell class="p-2"><Input type="number" v-model="item.unit_price" class="h-8 text-right" min="0" step="0.01" /></TableCell>
                     <TableCell class="p-2 text-center"><Button variant="ghost" size="icon" class="h-8 w-8 text-red-400 hover:text-red-600" @click="removeItem(idx)"><Trash2 class="w-4 h-4" /></Button></TableCell>
                   </TableRow>
                 </TableBody>
               </Table>
             </CardContent>
          </Card>

          <div v-if="selectedType === 'OS'" class="space-y-4 animate-in fade-in slide-in-from-bottom-2">
             <Card v-for="(group, gIdx) in formData.os_groups" :key="gIdx" class="border-l-4 border-l-orange-400 shadow-sm overflow-hidden">
                <div class="bg-orange-50 p-3 flex items-center gap-2 border-b border-orange-100">
                   <div class="font-mono font-bold text-orange-800 text-sm w-10 text-right">{{ gIdx + 1 }}.00</div>
                   <Input v-model="group.title" placeholder="TÍTULO DEL GRUPO (Ej: MEJORAMIENTO DE SALA...)" class="font-bold border-transparent hover:border-orange-200 focus:border-orange-400 uppercase h-8" />
                   <div class="ml-auto text-xs font-bold text-orange-800 bg-orange-100 px-2 py-1 rounded">
                      Total Grupo: {{ formData.currency }} {{ getGroupTotal(group).toFixed(2) }}
                   </div>
                   <Button variant="ghost" size="icon" class="h-8 w-8 text-red-400 hover:text-red-600 hover:bg-red-50" @click="removeOSGroup(gIdx)">
                      <Trash2 class="w-4 h-4"/>
                   </Button>
                </div>

                <div class="p-0">
                   <Table>
                     <TableHeader>
                        <TableRow class="hover:bg-transparent">
                           <TableHead class="w-[10%] text-center text-xs">Item</TableHead>
                           <TableHead class="w-[40%] text-xs">Descripción</TableHead>
                           <TableHead class="w-[10%] text-xs">Und</TableHead>
                           <TableHead class="w-[10%] text-right text-xs">Cant</TableHead>
                           <TableHead class="w-[15%] text-right text-xs">P. Unit</TableHead>
                           <TableHead class="w-[15%] text-right text-xs">Subtotal</TableHead>
                           <TableHead class="w-[5%]"></TableHead>
                        </TableRow>
                     </TableHeader>
                     <TableBody>
                        <TableRow v-for="(item, iIdx) in group.items" :key="iIdx" class="hover:bg-gray-50 border-b-0">
                           <TableHead class="text-center font-mono text-xs text-gray-500">
                              {{ gIdx + 1 }}.{{ String(iIdx + 1).padStart(2, '0') }}
                           </TableHead>
                           <TableCell class="p-1">
                             <textarea
                                 v-model="item.invoice_detail_text"
                                 class="flex w-full min-h-[2.5rem] rounded-md border border-gray-200 bg-white px-2 py-1 text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 resize-y"
                                 rows="2"
                                 placeholder="Descripción detallada..." >
                             </textarea>
                           </TableCell>
                           <TableCell class="p-1">
                              <Select v-model="item.um">
                                <SelectTrigger class="h-7 text-xs border-gray-200"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="UND">und</SelectItem><SelectItem value="m2">m2</SelectItem>
                                  <SelectItem value="ml">ml</SelectItem><SelectItem value="glb">glb</SelectItem>
                                  <SelectItem value="pza">pza</SelectItem>
                                </SelectContent>
                              </Select>
                           </TableCell>
                           <TableCell class="p-1"><Input type="number" v-model="item.quantity" class="h-7 text-right text-xs border-gray-200" min="1" /></TableCell>
                           <TableCell class="p-1"><Input type="number" v-model="item.unit_price" class="h-7 text-right text-xs border-gray-200" min="0" step="0.01" /></TableCell>
                           <TableCell class="p-1 text-right text-xs font-mono text-gray-700 pt-2">
                              {{ (item.quantity * item.unit_price).toFixed(2) }}
                           </TableCell>
                           <TableCell class="p-1 text-center">
                              <Button variant="ghost" size="icon" class="h-6 w-6 text-gray-300 hover:text-red-500" @click="removeOSItem(gIdx, iIdx)">
                                 <Trash2 class="w-3 h-3" />
                              </Button>
                           </TableCell>
                        </TableRow>
                        <TableRow>
                           <TableCell colspan="7" class="text-center p-2 bg-gray-50/30">
                              <Button variant="ghost" size="xs" class="text-blue-600 hover:bg-blue-50 h-6 text-xs" @click="addOSItem(gIdx)">
                                 <Plus class="w-3 h-3 mr-1"/> Agregar ítem al grupo
                              </Button>
                           </TableCell>
                        </TableRow>
                     </TableBody>
                   </Table>
                </div>
             </Card>

             <Button variant="outline" class="w-full border-dashed border-orange-300 text-orange-600 hover:bg-orange-50" @click="addOSGroup">
                <Layers class="w-4 h-4 mr-2"/> Agregar Nuevo Grupo de Trabajo
             </Button>



          </div>
             <Card class="border-t-4 border-t-gray-400 mt-6 shadow-sm">
                <CardHeader class="pb-2 pt-3 px-4 bg-gray-100 flex flex-row justify-between items-center">
                   <CardTitle class="text-xs font-bold uppercase text-gray-700 flex items-center gap-2">
                      <ListTree class="w-3 h-3"/> INCLUYE
                   </CardTitle>
                   <Button size="xs" variant="ghost" class="h-6 text-gray-500 hover:text-gray-900" @click="addIncludeLine">
                      <Plus class="w-3 h-3"/>
                   </Button>
                </CardHeader>
                <CardContent class="p-2 space-y-1 bg-gray-50">
                   <div v-for="(inc, idx) in formData.service_includes" :key="idx" class="flex items-center gap-2">
                      <div class="w-1.5 h-1.5 rounded-full bg-gray-400 shrink-0"></div>
                      <Input v-model="inc.text" placeholder="Ej: Recojo y devolución de llaves..." class="h-7 text-xs bg-white border-gray-200" />
                      <Button variant="ghost" size="icon" class="h-6 w-6 text-gray-300 hover:text-red-400" @click="removeIncludeLine(idx)">
                         <Trash2 class="w-3 h-3"/>
                      </Button>
                   </div>
                   <div v-if="formData.service_includes.length === 0" class="text-center text-xs text-gray-400 italic py-2">
                      Sin inclusiones adicionales.
                   </div>
                </CardContent>
             </Card>
        </div>

        <div class="space-y-6">
          <Card>
            <CardHeader class="pb-3 border-b bg-gray-50/50 py-3">
               <CardTitle class="text-sm font-bold uppercase text-gray-600">Condiciones</CardTitle>
            </CardHeader>
            <CardContent class="pt-4 space-y-4">

               <div class="bg-gray-50 p-4 rounded border flex flex-col space-y-2 mb-4">
                  <div class="flex justify-between text-sm"><span class="text-gray-600">Subtotal:</span><span class="font-medium">{{ formData.currency }} {{ subtotal.toFixed(2) }}</span></div>
                  <div class="flex justify-between text-sm"><span class="text-gray-600">IGV (18%):</span><span class="font-medium">{{ formData.currency }} {{ igv.toFixed(2) }}</span></div>
                  <div class="flex justify-between text-lg font-bold text-gray-900 pt-2 border-t border-gray-200"><span>Total:</span><span>{{ formData.currency }} {{ total.toFixed(2) }}</span></div>
               </div>

               <div>
                  <Label>Centro de Costo</Label>
                  <Select v-model="formData.cost_center_id">
                    <SelectTrigger><SelectValue placeholder="Seleccione..." /></SelectTrigger>
                    <SelectContent>
                      <SelectItem v-for="cc in catalogs.cost_centers" :key="cc.id" :value="cc.id">{{ cc.code }} - {{ cc.name }}</SelectItem>
                    </SelectContent>
                  </Select>
               </div>

               <div>
                  <Label>Moneda</Label>
                  <Select v-model="formData.currency">
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="PEN">Soles (S/.)</SelectItem><SelectItem value="USD">Dólares ($)</SelectItem>
                    </SelectContent>
                  </Select>
               </div>

               <div>
                   <Label>Forma de Pago</Label>
                   <textarea
                       v-model="formData.payment_condition"
                       rows="2"
                       class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                       placeholder="Ej: 40% Adelanto..."
                   ></textarea>
               </div>

               <div v-if="selectedType === 'OC'">
                   <Label>Fecha Entrega</Label>
                   <Input type="date" v-model="formData.transfer_date" />
               </div>
               <div v-if="selectedType === 'OS'" class="grid grid-cols-2 gap-2">
                   <div>
                       <Label>Fecha Inicio</Label>
                       <Input type="date" v-model="formData.start_date" />
                   </div>
                   <div>
                       <Label>Fecha Fin</Label>
                       <Input type="date" v-model="formData.end_date" />
                   </div>
               </div>

               <div>
                  <Label class="flex items-center gap-1"><MapPin class="w-3 h-3 text-gray-500"/> Site / Lugar de Entrega</Label>
                  <Input v-model="formData.site" placeholder="Ej: ALMACÉN SURCO" class="mt-1" />
               </div>

               <div class="border-t pt-4 mt-2">
                   <Label class="text-xs font-bold uppercase text-gray-500 mb-2 block">Condiciones Comerciales</Label>

                   <div class="mb-3">
                       <Label class="text-xs text-gray-400">Penalidad</Label>
                       <textarea
                           v-model="formData.penalty"
                           rows="3"
                           class="flex w-full rounded-md border border-input bg-gray-50 px-3 py-2 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                       ></textarea>
                   </div>

                   <div class="space-y-2">
                       <div v-for="(cond, idx) in formData.commercial_conditions" :key="idx" class="flex items-start gap-2">
                           <span class="text-xs font-bold text-gray-400 mt-2">{{ idx + 5 }}.</span>
                           <textarea
                               v-model="formData.commercial_conditions[idx]"
                               rows="2"
                               class="flex-1 rounded-md border border-input px-3 py-2 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                           ></textarea>
                           <Button variant="ghost" size="icon" class="h-8 w-8 text-red-400 hover:text-red-600 mt-1" @click="removeConditionLine(idx)">
                               <XCircle class="w-4 h-4"/>
                           </Button>
                       </div>
                       <Button variant="outline" size="sm" class="w-full text-xs" @click="addConditionLine">
                           <Plus class="w-3 h-3 mr-1"/> Agregar Condición
                       </Button>
                   </div>
               </div>

               <div class="border-t pt-4 mt-2">
                   <Label class="text-xs font-bold uppercase text-gray-500 mb-2 block">Notas al Pie (Legal)</Label>
                   <textarea
                       v-model="formData.footer_note"
                       rows="5"
                       class="flex w-full rounded-md border border-input bg-yellow-50/50 px-3 py-2 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                   ></textarea>
               </div>

               <Button class="w-full mt-4 bg-gray-900 hover:bg-black" :disabled="isSubmitting" @click="handleSubmit">
                  <Loader2 v-if="isSubmitting" class="w-4 h-4 mr-2 animate-spin" />
                  Guardar Orden
               </Button>
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  </div>
</template>