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
// AGREGADO: Importamos 'Download' para el ícono de descarga
import { Loader2, Plus, Trash2, Search, FileText, Wrench, ArrowLeft, Printer, Eye, Contact, Pencil, Download } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()
const router = useRouter()
const FLASK_API_URL = `${import.meta.env.VITE_API_URL}/api`

// --- ESTADOS DE LA VISTA ---
const viewMode = ref('list') // 'list' | 'create'
const isLoadingList = ref(true)
const purchaseOrders = ref([])

// Estado para saber qué orden se está descargando actualmente (para mostrar el spinner correcto)
const downloadingOrderId = ref(null)

// =============================================================================
//  LÓGICA DE LISTADO (MODO LISTA)
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

// NUEVA FUNCIÓN: Descargar PDF desde la lista
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

// =============================================================================
//  LÓGICA DE CREACIÓN
// =============================================================================

const isSubmitting = ref(false)
const catalogs = ref({ document_types: [], statuses: [], cost_centers: [] })

// Configuración del Correlativo (Editables)
const correlativeSeries = ref('026')
const correlativeNumber = ref(1)
const isFetchingCorrelative = ref(false)

const selectedType = ref('OC') // 'OC' o 'OS'

const formData = reactive({
  provider_id: null,
  provider_search: '',
  provider_data: null,
  cost_center_id: null,
  reference: '',

  // --- CAMPOS DE CONTACTO ---
  attention: '',       // Nombre de la persona
  provider_contact: '', // Campo unificado (Teléfono o Email)

  payment_condition: '',
  currency: 'PEN',
  transfer_date: '',
  scope: '', // Alcance (Solo para OS)
  items: []
})

const providerResults = ref([])
const showProviderResults = ref(false)
const isSearchingProvider = ref(false)
let searchTimeout = null

// --- COMPUTED ---
const formattedCorrelative = computed(() => {
  const num = String(correlativeNumber.value).padStart(3, '0')
  return `${correlativeSeries.value}-${num}`
})

const subtotal = computed(() => {
  return formData.items.reduce((acc, item) => acc + (parseFloat(item.quantity || 0) * parseFloat(item.unit_price || 0)), 0)
})

const igv = computed(() => subtotal.value * 0.18)
const total = computed(() => subtotal.value + igv.value)

// --- CICLO DE VIDA ---
onMounted(async () => {
  await fetchOrders()
  loadCatalogs()
})

// --- MÉTODOS DE CAMBIO DE VISTA ---
function switchToCreate() {
  viewMode.value = 'create'
  formData.items = []
  addItem() // Agregar un item vacío por defecto
  fetchNextCorrelative() // Cargar el siguiente número disponible
}

function switchToList() {
  viewMode.value = 'list'
  fetchOrders() // Recargar la lista para ver los nuevos cambios
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
      // Si falla, no rompemos nada, el usuario puede editar manualmente
      console.warn("No se pudo obtener correlativo automático.")
  } finally {
      isFetchingCorrelative.value = false
  }
}

// Vigilar cambios en la serie para actualizar el número automáticamente
watch(correlativeSeries, (newVal) => {
    if(newVal.length === 3) fetchNextCorrelative()
})


// --- BUSCADOR PROVEEDOR INTELIGENTE ---
async function handleProviderSearch() {
  const q = formData.provider_search.trim()
  if (!q) return

  isSearchingProvider.value = true
  clearTimeout(searchTimeout)

  searchTimeout = setTimeout(async () => {
    try {
      const token = await getAccessTokenSilently()

      if (/^\d{11}$/.test(q)) {
         // CASO A: Es un RUC (11 dígitos)
         // 1. Buscar en BD Local
         const localRes = await fetch(`${FLASK_API_URL}/purchases/providers?q=${q}`, {
            headers: { 'Authorization': `Bearer ${token}` }
         })
         const localData = await localRes.json()

         if (localData.length > 0) {
            providerResults.value = localData
            showProviderResults.value = true
         } else {
            // 2. Si no está en local, buscar en API SUNAT
            const sunatRes = await fetch(`${FLASK_API_URL}/purchases/lookup-provider/${q}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })

            if (sunatRes.ok) {
                const sunatData = await sunatRes.json()
                providerResults.value = [sunatData]
                showProviderResults.value = true
            } else {
                providerResults.value = []
            }
         }
      } else {
         // CASO B: Es un Nombre (Buscar solo en local)
         const res = await fetch(`${FLASK_API_URL}/purchases/providers?q=${q}`, {
            headers: { 'Authorization': `Bearer ${token}` }
         })
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

  // Llenar contacto automáticamente si existe teléfono o email en el proveedor
  formData.provider_contact = p.phone || p.email || ''

  showProviderResults.value = false
}

// --- GESTIÓN DE ITEMS ---
function addItem() {
  formData.items.push({
    invoice_detail_text: '',
    um: 'UND',
    quantity: 1,
    unit_price: 0
  })
}

function removeItem(index) {
  formData.items.splice(index, 1)
}

// --- GUARDAR (SUBMIT) ---
async function handleSubmit() {
  if (!formData.provider_search || formData.items.length === 0) {
    alert("Seleccione un proveedor y agregue al menos un item.")
    return
  }

  isSubmitting.value = true
  try {
    const token = await getAccessTokenSilently()

    // Lógica para determinar el Tipo de Documento ID
    const docTypeName = selectedType.value === 'OC' ? 'Orden de Compra' : 'Orden de Servicio'
    const docType = catalogs.value.document_types.find(d => d.name.includes(docTypeName) || d.name === selectedType.value)
    const docTypeId = docType ? docType.id : 1

    const status = catalogs.value.statuses.find(s => s.name === 'Emitida') || catalogs.value.statuses[0]

    const payload = {
      document_number: formattedCorrelative.value,
      order_type: selectedType.value, // Envía 'OC' o 'OS'
      provider_id: formData.provider_id,
      document_type_id: docTypeId,
      status_id: status.id,
      cost_center_id: formData.cost_center_id,

      reference: formData.reference,
      attention: formData.attention,
      provider_contact: formData.provider_contact, // Campo unificado

      // Alcance solo si es OS
      scope: selectedType.value === 'OS' ? formData.scope : '',

      payment_condition: formData.payment_condition,
      currency: formData.currency,
      transfer_date: formData.transfer_date,

      items: formData.items.map(i => ({
        invoice_detail_text: i.invoice_detail_text,
        um: i.um,
        quantity: i.quantity,
        unit_price: i.unit_price
      }))
    }

    // Si el proveedor vino de SUNAT y aún no tiene ID en el frontend (caso raro), usamos el del objeto data
    if(!payload.provider_id && formData.provider_data?.id) {
        payload.provider_id = formData.provider_data.id
    }

    const res = await fetch(`${FLASK_API_URL}/purchases/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
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
</script>

<template>
  <div class="max-w-6xl mx-auto p-6 space-y-6">

    <div v-if="viewMode === 'list'" class="space-y-6 animate-in fade-in">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-gray-900">Ordenes de Compra/Servicio</h1>
          <p class="text-sm text-gray-500">Historial de adquisiciones y servicios.</p>
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

                   <Button variant="ghost" size="icon" class="h-8 w-8 text-gray-400" @click="goToDetail(order.id)">
                     <Eye class="w-4 h-4" />
                   </Button>

                   <Button
                     v-if="order.status === 'Pendiente' || order.status === 'Borrador' || order.status === 'Emitida'"
                     variant="ghost"
                     size="icon"
                     class="h-8 w-8 text-blue-600 hover:text-blue-800 hover:bg-blue-50"
                     @click="$router.push(`/purchases/${order.id}/edit`)"
                   >
                     <Pencil class="w-4 h-4" />
                   </Button>

                   <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 text-gray-600 hover:text-gray-900"
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

                <div class="flex items-center gap-1">
                    <div class="relative">
                        <Input v-model="correlativeSeries" class="h-8 w-16 text-center font-mono font-bold bg-blue-50 text-blue-700 border-blue-200" maxlength="3" />
                        <span class="absolute -bottom-4 left-0 w-full text-center text-[9px] text-gray-400">SERIE</span>
                    </div>
                    <span class="text-blue-300 font-bold">-</span>
                    <div class="relative">
                        <Input v-model="correlativeNumber" type="number" class="h-8 w-20 text-center font-mono font-bold bg-blue-50 text-blue-700 border-blue-200" min="1" />
                        <span class="absolute -bottom-4 left-0 w-full text-center text-[9px] text-gray-400">CORRELATIVO</span>
                    </div>
                    <Loader2 v-if="isFetchingCorrelative" class="w-4 h-4 animate-spin text-blue-400 ml-2" />
                </div>
              </div>
            </CardHeader>
            <CardContent class="pt-6 grid gap-4">

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

              <div v-if="formData.provider_data" class="bg-blue-50/50 p-3 rounded text-sm space-y-1 border border-blue-100 text-blue-900">
                  <div class="font-bold">{{ formData.provider_data.name || formData.provider_data.razon_social }}</div>
                  <div class="text-xs opacity-75">RUC: {{ formData.provider_data.ruc }}</div>
                  <div class="text-xs opacity-75">{{ formData.provider_data.address || formData.provider_data.direccion || 'Sin dirección registrada' }}</div>
              </div>

              <div class="bg-gray-50 p-3 rounded-lg border border-gray-100 space-y-3">
                 <Label class="text-xs font-bold text-gray-500 uppercase">Datos de Contacto (Atención)</Label>

                 <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div class="md:col-span-2">
                        <Input v-model="formData.attention" placeholder="Nombre de la persona de contacto..." class="bg-white" />
                    </div>

                    <div class="md:col-span-2 relative">
                        <Contact class="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
                        <Input
                            v-model="formData.provider_contact"
                            placeholder="Teléfono / Celular o Correo Electrónico"
                            class="pl-9 bg-white"
                        />
                    </div>
                 </div>
              </div>

              <div>
                  <Label>Referencia (Cotización / Proyecto)</Label>
                  <Input v-model="formData.reference" class="mt-1" />
              </div>

            </CardContent>
          </Card>

          <Card>
             <CardHeader class="pb-3 border-b bg-gray-50/50 py-2 flex flex-row justify-between items-center">
               <CardTitle class="text-sm font-bold uppercase text-gray-600">2. Detalle de Items</CardTitle>
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
                            <SelectItem value="UND">UND</SelectItem><SelectItem value="SERV">SERV</SelectItem>
                            <SelectItem value="GLB">GLB</SelectItem><SelectItem value="KG">KG</SelectItem>
                            <SelectItem value="MTS">MTS</SelectItem>
                          </SelectContent>
                        </Select>
                     </TableCell>
                     <TableCell class="p-2"><Input type="number" v-model="item.quantity" class="h-8 text-right" min="1" /></TableCell>
                     <TableCell class="p-2"><Input type="number" v-model="item.unit_price" class="h-8 text-right" min="0" step="0.01" /></TableCell>
                     <TableCell class="p-2 text-center"><Button variant="ghost" size="icon" class="h-8 w-8 text-red-400 hover:text-red-600" @click="removeItem(idx)"><Trash2 class="w-4 h-4" /></Button></TableCell>
                   </TableRow>
                 </TableBody>
               </Table>

               <div class="p-4 bg-gray-50 border-t flex flex-col items-end space-y-1">
                  <div class="flex justify-between w-48 text-sm"><span class="text-gray-600">Subtotal:</span><span class="font-medium">{{ formData.currency }} {{ subtotal.toFixed(2) }}</span></div>
                  <div class="flex justify-between w-48 text-sm"><span class="text-gray-600">IGV (18%):</span><span class="font-medium">{{ formData.currency }} {{ igv.toFixed(2) }}</span></div>
                  <div class="flex justify-between w-48 text-lg font-bold text-gray-900 pt-2 border-t border-gray-200"><span>Total:</span><span>{{ formData.currency }} {{ total.toFixed(2) }}</span></div>
               </div>
             </CardContent>
          </Card>

        </div>

        <div class="space-y-6">
          <Card>
            <CardHeader class="pb-3 border-b bg-gray-50/50 py-3">
               <CardTitle class="text-sm font-bold uppercase text-gray-600">3. Condiciones</CardTitle>
            </CardHeader>
            <CardContent class="pt-4 space-y-4">
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

               <div><Label>Forma de Pago</Label><Input v-model="formData.payment_condition" /></div>
               <div><Label>Fecha Traslado / Entrega</Label><Input type="date" v-model="formData.transfer_date" /></div>

               <div class="pt-2 animate-in fade-in slide-in-from-top-2" v-if="selectedType === 'OS'">
                  <Label class="text-orange-600">Alcance (Detalle Técnico - OS)</Label>
                  <textarea
                      v-model="formData.scope"
                      rows="6"
                      placeholder="Ingrese detalles técnicos, alcance del servicio..."
                      class="flex w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none"
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