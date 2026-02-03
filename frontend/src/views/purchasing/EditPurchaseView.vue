<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth0 } from '@auth0/auth0-vue'

// UI Components
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  Loader2, Plus, Trash2, Search, Save, ArrowLeft, Contact,
  MapPin, ListTree, Layers, XCircle
} from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()
const route = useRoute()
const router = useRouter()
const FLASK_API_URL = `${import.meta.env.VITE_API_URL}/api`

// --- ESTADO ---
const isLoading = ref(true)
const isSubmitting = ref(false)
const orderId = route.params.id

// Catálogos
const catalogs = ref({ document_types: [], statuses: [], cost_centers: [] })

// Datos Simulados
const coordinators = ref([
  { id: '1', name: 'FABRIZIO ALARCON' },
  { id: '2', name: 'GERSON CALLAÑAUPA' },
  { id: '3', name: 'MARIA AYALA' },
  { id: '4', name: 'BRAULIO CASTILLO' },
  { id: '5', name: 'ROSARIO CUEVAS' },
  { id: '6', name: 'GIANCARLO ZEGARRA' },
  { id: '7', name: 'PIERO NANQUEN' }
])

// --- VALORES POR DEFECTO ---
const DEFAULT_FOOTER_NOTE = `Nota: La orden de compra es nula sin todas las firmas necesaria.
Toda factura deberá incluir el número de orden de compra y centro de costo correspondiente.
Solo se recibirán documentos de pago (facturas) los días miércoles de 9:00 a 16:00. De enviar el documento fuera de día indicado será programado para la semana siguiente.`

const DEFAULT_PENALTY = "Penalidad: 5% por día de atraso, hasta un total de 15%, después del cual la OC será automáticamente anulada y liquidada."

const DEFAULT_CONDITIONS = [
    "El contratista será responsable de proveer los implementos de seguridad, SCTR para su ingreso y documentos de SST para su respectivo llenado a su personal.",
    "Ambas partes acuerdan que toda información y documentación será considerada confidencial, no será divulgada a terceros sin consentimiento, no utilizarla para fines distintos a los establecidos en esta orden de compra.",
    "El contratista se compromete a cumplir con todas la leyes, regulaciones y normas de medio ambiente según apliquen en esta orden de compra.",
    "El número de esta orden de compra deberá estar claramente indicado en las facturas correspondientes al servicio ejecutado. Asimismo el contratista deberá comunicar recibo de esta orden de compra inmediatamente después de su recepción en los correos a mayala@compower.pe, jbarbachan@compower.pe. Cada factura deberá adjuntar su OC y el % de la misma, más el acumulado."
]

// Formulario
const formData = reactive({
  document_number: '',
  order_type: 'OC',
  status_id: null,

  provider_id: null,
  provider_search: '',
  provider_data: null,

  cost_center_id: null,
  reference: '',
  attention: '',
  provider_contact: '',

  coordinator: '',
  site: '',

  payment_condition: '',
  currency: 'PEN',

  // Fechas
  issue_date: '',
  transfer_date: '',
  start_date: '',
  end_date: '',

  scope: '',

  // Listas
  items: [],
  os_groups: [],
  service_includes: [],

  // Condiciones y Notas
  penalty: '',
  commercial_conditions: [],
  footer_note: ''
})

const providerResults = ref([])
const showProviderResults = ref(false)
const isSearchingProvider = ref(false)
let searchTimeout = null

// Fecha Actual (Helper)
const getToday = () => {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// Cálculos (Idénticos a PurchaseView)
const subtotal = computed(() => {
  if (formData.order_type === 'OS') {
     let totalOS = 0
     formData.os_groups.forEach(group => {
       group.items.forEach(item => {
         totalOS += (parseFloat(item.quantity || 0) * parseFloat(item.unit_price || 0))
       })
     })
     return totalOS
  } else {
     return formData.items.reduce((acc, item) => acc + (parseFloat(item.quantity || 0) * parseFloat(item.unit_price || 0)), 0)
  }
})

const igv = computed(() => subtotal.value * 0.18)
const total = computed(() => subtotal.value + igv.value)

// --- CICLO DE VIDA ---
onMounted(async () => {
  await loadCatalogs()
  await loadOrderData()
})

async function loadCatalogs() {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/purchases/catalogs`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) catalogs.value = await res.json()
  } catch (e) { console.error(e) }
}

async function loadOrderData() {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/purchases/${orderId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!res.ok) throw new Error("No se pudo cargar la orden")

    const data = await res.json()

    // Datos Básicos
    formData.document_number = data.codigo
    formData.order_type = data.order_type || 'OC'

    // Mantenemos el ID del estado actual para enviarlo al guardar, pero no lo mostramos en UI
    const statusObj = catalogs.value.statuses.find(s => s.name === data.status)
    formData.status_id = statusObj ? statusObj.id : null

    formData.provider_id = data.provider_id // Asumiendo que el back devuelve esto, si no, se busca al guardar
    formData.provider_search = data.provider_name
    formData.cost_center_id = data.id_cc
    formData.reference = data.referencia
    formData.attention = data.atencion
    formData.provider_contact = data.contacto === 'N/A' ? '' : data.contacto
    formData.coordinator = data.coordinador
    formData.site = data.site
    formData.payment_condition = data.forma_pago
    formData.currency = data.moneda

    // Fechas
    formData.issue_date = getToday()
    formData.transfer_date = data.fecha_traslado || ''
    formData.start_date = data.fecha_inicio || ''
    formData.end_date = data.fecha_fin || ''

    // Nota al pie
    formData.footer_note = data.notas_pie || DEFAULT_FOOTER_NOTE

    // Condiciones Comerciales
    if (data.condiciones_comerciales && data.condiciones_comerciales.length > 0) {
        formData.penalty = data.condiciones_comerciales[0]
        formData.commercial_conditions = data.condiciones_comerciales.slice(1)
    } else {
        formData.penalty = DEFAULT_PENALTY
        formData.commercial_conditions = [...DEFAULT_CONDITIONS]
    }

    // Lógica Scope / Items
    let parsedScope = null
    if (data.alcance && data.alcance.trim().startsWith('{')) {
        try { parsedScope = JSON.parse(data.alcance) } catch(e) {}
    }

    if (formData.order_type === 'OS' && parsedScope && parsedScope.groups) {
        formData.os_groups = parsedScope.groups
        formData.service_includes = parsedScope.includes || []
        formData.scope = ''
    } else {
        formData.scope = data.alcance
        formData.items = data.items.map(i => ({
            invoice_detail_text: i.invoice_detail_text,
            um: i.unit_of_measure,
            quantity: i.quantity,
            unit_price: i.unit_price
        }))

        // Migración visual para OS antiguas
        if (formData.order_type === 'OS' && formData.os_groups.length === 0) {
            if (formData.items.length > 0) {
                 formData.os_groups.push({
                     title: 'ITEMS ORIGINALES',
                     items: JSON.parse(JSON.stringify(formData.items))
                 })
                 formData.items = []
            } else {
                 addOSGroup()
            }
        }
    }

  } catch (e) {
    alert(e.message)
    router.push('/purchases')
  } finally {
    isLoading.value = false
  }
}

// --- PROVEEDOR ---
async function handleProviderSearch() {
  const q = formData.provider_search.trim()
  if (!q) return
  isSearchingProvider.value = true

  if (searchTimeout) clearTimeout(searchTimeout)

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
  formData.provider_search = p.name
  if(!formData.provider_contact) formData.provider_contact = p.phone || p.email || ''
  showProviderResults.value = false
}

// --- GESTIÓN DE ITEMS ---
function addItem() { formData.items.push({ invoice_detail_text: '', um: 'UND', quantity: 1, unit_price: 0 }) }
function removeItem(index) { formData.items.splice(index, 1) }

function addOSGroup() { formData.os_groups.push({ title: '', items: [ { invoice_detail_text: '', um: 'GLB', quantity: 1, unit_price: 0 } ] }) }
function removeOSGroup(index) { formData.os_groups.splice(index, 1) }
function addOSItem(groupIndex) { formData.os_groups[groupIndex].items.push({ invoice_detail_text: '', um: 'UND', quantity: 1, unit_price: 0 }) }
function removeOSItem(groupIndex, itemIndex) { formData.os_groups[groupIndex].items.splice(itemIndex, 1) }
function getGroupTotal(group) { return group.items.reduce((acc, item) => acc + (parseFloat(item.quantity || 0) * parseFloat(item.unit_price || 0)), 0) }

function addIncludeLine() { formData.service_includes.push({ text: '' }) }
function removeIncludeLine(index) { formData.service_includes.splice(index, 1) }

// --- GESTIÓN DE CONDICIONES ---
function addConditionLine() { formData.commercial_conditions.push('') }
function removeConditionLine(index) { formData.commercial_conditions.splice(index, 1) }

// --- ACTUALIZAR ---
async function handleUpdate() {
  isSubmitting.value = true
  try {
    const token = await getAccessTokenSilently()
    const docType = catalogs.value.document_types.find(d => d.name.includes(formData.order_type === 'OC' ? 'Orden de Compra' : 'Orden de Servicio'))

    let itemsPayload = []
    let scopePayload = formData.scope

    if (formData.order_type === 'OC') {
        itemsPayload = formData.items.map(i => ({ invoice_detail_text: i.invoice_detail_text, um: i.um, quantity: i.quantity, unit_price: i.unit_price }))
    } else {
        formData.os_groups.forEach(group => {
            group.items.forEach(item => {
                itemsPayload.push({ group_name: group.title, invoice_detail_text: item.invoice_detail_text, um: item.um, quantity: item.quantity, unit_price: item.unit_price })
            })
        })
        scopePayload = JSON.stringify({ groups: formData.os_groups, includes: formData.service_includes })
    }

    const finalConditions = [formData.penalty, ...formData.commercial_conditions].filter(c => c && c.trim() !== '')

    const payload = {
      document_number: formData.document_number,
      order_type: formData.order_type,
      status_id: formData.status_id, // Enviamos el mismo estado que tenía
      cost_center_id: formData.cost_center_id,
      document_type_id: docType ? docType.id : 1,
      ...(formData.provider_id && { provider_id: formData.provider_id }),

      reference: formData.reference,
      attention: formData.attention,
      provider_contact: formData.provider_contact,
      coordinator: formData.coordinator,
      site: formData.site,
      scope: scopePayload,
      payment_condition: formData.payment_condition,
      currency: formData.currency,

      issue_date: formData.issue_date,
      transfer_date: formData.order_type === 'OC' ? formData.transfer_date : null,
      start_date: formData.order_type === 'OS' ? formData.start_date : null,
      end_date: formData.order_type === 'OS' ? formData.end_date : null,

      commercial_conditions: JSON.stringify(finalConditions),
      footer_note: formData.footer_note,

      items: itemsPayload
    }

    const res = await fetch(`${FLASK_API_URL}/purchases/${orderId}`, {
      method: 'PUT',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (!res.ok) throw new Error((await res.json()).error || 'Error al actualizar')

    alert("Orden actualizada correctamente.")
    router.push('/purchases')

  } catch (e) { alert(e.message) }
  finally { isSubmitting.value = false }
}
</script>

<template>
  <div class="max-w-7xl mx-auto p-6 space-y-6">
    <div v-if="isLoading" class="flex justify-center py-10"><Loader2 class="w-8 h-8 animate-spin text-gray-400" /></div>

    <div v-else class="animate-in fade-in">
        <div class="flex items-center justify-between mb-6">
            <div class="flex items-center gap-4">
                <Button variant="outline" size="icon" @click="$router.push('/purchases')"><ArrowLeft class="w-4 h-4" /></Button>
                <div>
                    <h1 class="text-2xl font-bold text-gray-900">Editar {{ formData.order_type === 'OC' ? 'Orden de Compra' : 'Orden de Servicio' }}</h1>
                    <p class="text-sm text-gray-500">Documento: {{ formData.document_number }}</p>
                </div>
            </div>

            <div class="flex items-center gap-2">
                 <span class="px-3 py-1 bg-gray-100 rounded-full text-xs font-bold text-gray-600 border">
                    {{ formData.order_type }}
                </span>
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
                                    <Input type="date" v-model="formData.issue_date" class="h-8 w-32 text-xs" disabled />
                                    <span class="absolute -bottom-4 left-0 w-full text-center text-[9px] text-gray-400">EMISIÓN</span>
                                </div>
                                <div class="h-6 w-px bg-gray-300 mx-1"></div>
                                <div class="relative">
                                    <Input v-model="formData.document_number" class="h-8 w-32 text-center font-mono font-bold bg-blue-50 text-blue-700 border-blue-200" disabled/>
                                    <span class="absolute -bottom-4 left-0 w-full text-center text-[9px] text-gray-400">CÓDIGO</span>
                                </div>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent class="pt-6 grid gap-4">
                        <div class="grid grid-cols-2 gap-4">
                            <div class="relative">
                                <Label class="text-xs font-bold text-gray-500 uppercase">Proveedor</Label>
                                <div class="relative mt-1">
                                    <Search class="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
                                    <Input v-model="formData.provider_search" @input="handleProviderSearch" placeholder="Buscar..." class="pl-9"/>
                                    <Loader2 v-if="isSearchingProvider" class="absolute right-3 top-2.5 h-4 w-4 animate-spin text-gray-400" />
                                </div>
                                <div v-if="showProviderResults" class="absolute z-10 w-full bg-white border rounded-md shadow-lg mt-1 max-h-60 overflow-y-auto">
                                    <div v-for="p in providerResults" :key="p.id" @click="selectProvider(p)" class="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-0">
                                        <div class="font-bold text-sm">{{ p.name }}</div>
                                        <div class="text-xs text-gray-500">RUC: {{ p.ruc }}</div>
                                    </div>
                                </div>
                            </div>
                            <div>
                                <Label class="text-xs font-bold text-gray-500 uppercase">Solicitante</Label>
                                <Select v-model="formData.coordinator">
                                    <SelectTrigger class="mt-1"><SelectValue/></SelectTrigger>
                                    <SelectContent><SelectItem v-for="c in coordinators" :key="c.id" :value="c.name">{{ c.name }}</SelectItem></SelectContent>
                                </Select>
                            </div>
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

                <Card v-if="formData.order_type === 'OC'">
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
                                        <SelectItem value="UND">UND</SelectItem>
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

                <div v-if="formData.order_type === 'OS'" class="space-y-4">
                    <Card v-for="(group, gIdx) in formData.os_groups" :key="gIdx" class="border-l-4 border-l-orange-400 shadow-sm overflow-hidden">
                        <div class="bg-orange-50 p-3 flex items-center gap-2 border-b border-orange-100">
                           <div class="font-mono font-bold text-orange-800 text-sm w-10 text-right">{{ gIdx + 1 }}.00</div>
                           <Input v-model="group.title" class="font-bold border-transparent hover:border-orange-200 focus:border-orange-400 uppercase h-8" placeholder="TÍTULO GRUPO"/>
                           <div class="ml-auto text-xs font-bold text-orange-800 bg-orange-100 px-2 py-1 rounded">
                               Total: {{ formData.currency }} {{ getGroupTotal(group).toFixed(2) }}
                           </div>
                           <Button variant="ghost" size="icon" class="h-8 w-8 text-red-400 hover:text-red-600 hover:bg-red-50" @click="removeOSGroup(gIdx)"><Trash2 class="w-4 h-4"/></Button>
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
                                     <textarea v-model="item.invoice_detail_text" class="flex w-full min-h-[2.5rem] rounded-md border border-gray-200 bg-white px-2 py-1 text-xs shadow-sm resize-y" rows="2"></textarea>
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
                                   <TableCell class="p-1"><Input type="number" v-model="item.quantity" class="h-7 text-right text-xs border-gray-200" /></TableCell>
                                   <TableCell class="p-1"><Input type="number" v-model="item.unit_price" class="h-7 text-right text-xs border-gray-200" /></TableCell>
                                   <TableCell class="p-1 text-right text-xs font-mono text-gray-700 pt-2">{{ (item.quantity * item.unit_price).toFixed(2) }}</TableCell>
                                   <TableCell class="p-1 text-center"><Button variant="ghost" size="icon" class="h-6 w-6 text-gray-300 hover:text-red-500" @click="removeOSItem(gIdx, iIdx)"><Trash2 class="w-3 h-3" /></Button></TableCell>
                                </TableRow>
                                <TableRow>
                                   <TableCell colspan="7" class="text-center p-2 bg-gray-50/30">
                                      <Button variant="ghost" size="xs" class="text-blue-600 hover:bg-blue-50 h-6 text-xs" @click="addOSItem(gIdx)"><Plus class="w-3 h-3 mr-1"/> Agregar ítem al grupo</Button>
                                   </TableCell>
                                </TableRow>
                             </TableBody>
                           </Table>
                        </div>
                    </Card>
                    <Button variant="outline" class="w-full border-dashed border-orange-300 text-orange-600 hover:bg-orange-50" @click="addOSGroup"><Layers class="w-4 h-4 mr-2"/> Agregar Nuevo Grupo de Trabajo</Button>

                    <Card class="border-t-4 border-t-gray-400 mt-6 shadow-sm">
                        <CardHeader class="pb-2 pt-3 px-4 bg-gray-100 flex flex-row justify-between items-center">
                           <CardTitle class="text-xs font-bold uppercase text-gray-700 flex items-center gap-2"><ListTree class="w-3 h-3"/> INCLUYE</CardTitle>
                           <Button size="xs" variant="ghost" class="h-6 text-gray-500 hover:text-gray-900" @click="addIncludeLine"><Plus class="w-3 h-3"/></Button>
                        </CardHeader>
                        <CardContent class="p-2 space-y-1 bg-gray-50">
                           <div v-for="(inc, idx) in formData.service_includes" :key="idx" class="flex items-center gap-2">
                              <div class="w-1.5 h-1.5 rounded-full bg-gray-400 shrink-0"></div>
                              <Input v-model="inc.text" class="h-7 text-xs bg-white border-gray-200" />
                              <Button variant="ghost" size="icon" class="h-6 w-6 text-gray-300 hover:text-red-400" @click="removeIncludeLine(idx)"><Trash2 class="w-3 h-3"/></Button>
                           </div>
                        </CardContent>
                    </Card>
                </div>
            </div>

            <div class="space-y-6">
                <Card>
                    <CardHeader class="pb-3 border-b bg-gray-50/50 py-3"><CardTitle class="text-sm font-bold uppercase text-gray-600">Condiciones</CardTitle></CardHeader>
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
                             <SelectContent><SelectItem v-for="cc in catalogs.cost_centers" :key="cc.id" :value="cc.id">{{ cc.code }}</SelectItem></SelectContent>
                           </Select>
                        </div>

                        <div>
                           <Label>Moneda</Label>
                           <Select v-model="formData.currency">
                             <SelectTrigger><SelectValue /></SelectTrigger>
                             <SelectContent><SelectItem value="PEN">Soles (S/.)</SelectItem><SelectItem value="USD">Dólares ($)</SelectItem></SelectContent>
                           </Select>
                        </div>

                        <div>
                            <Label>Forma de Pago</Label>
                            <textarea v-model="formData.payment_condition" rows="2" class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm" placeholder="Ej: 40% Adelanto..."></textarea>
                        </div>

                        <div v-if="formData.order_type === 'OC'"><Label>Fecha Entrega</Label><Input type="date" v-model="formData.transfer_date" /></div>
                        <div v-else class="grid grid-cols-2 gap-2">
                            <div><Label>Inicio</Label><Input type="date" v-model="formData.start_date" /></div>
                            <div><Label>Fin</Label><Input type="date" v-model="formData.end_date" /></div>
                        </div>

                        <div>
                           <Label class="flex items-center gap-1"><MapPin class="w-3 h-3 text-gray-500"/> Site / Lugar de Entrega</Label>
                           <Input v-model="formData.site" class="mt-1" />
                        </div>

                        <div class="border-t pt-4 mt-2">
                           <Label class="text-xs font-bold uppercase text-gray-500 mb-2 block">Condiciones Comerciales</Label>
                           <div class="mb-3">
                               <Label class="text-xs text-gray-400">Penalidad</Label>
                               <textarea v-model="formData.penalty" rows="3" class="flex w-full rounded-md border border-input bg-gray-50 px-3 py-2 text-xs shadow-sm"></textarea>
                           </div>
                           <div class="space-y-2">
                               <div v-for="(cond, idx) in formData.commercial_conditions" :key="idx" class="flex items-start gap-2">
                                   <span class="text-xs font-bold text-gray-400 mt-2">{{ idx + 5 }}.</span>
                                   <textarea v-model="formData.commercial_conditions[idx]" rows="2" class="flex-1 rounded-md border border-input px-3 py-2 text-xs shadow-sm"></textarea>
                                   <Button variant="ghost" size="icon" class="h-8 w-8 text-red-400 hover:text-red-600 mt-1" @click="removeConditionLine(idx)"><XCircle class="w-4 h-4"/></Button>
                               </div>
                               <Button variant="outline" size="sm" class="w-full text-xs" @click="addConditionLine"><Plus class="w-3 h-3 mr-1"/> Agregar Condición</Button>
                           </div>
                        </div>

                        <div class="border-t pt-4 mt-2">
                           <Label class="text-xs font-bold uppercase text-gray-500 mb-2 block">Notas al Pie (Legal)</Label>
                           <textarea v-model="formData.footer_note" rows="5" class="flex w-full rounded-md border border-input bg-yellow-50/50 px-3 py-2 text-xs shadow-sm"></textarea>
                        </div>

                        <Button class="w-full mt-4 bg-blue-600 hover:bg-blue-700" :disabled="isSubmitting" @click="handleUpdate">
                             <Save class="w-4 h-4 mr-2" /> Guardar Cambios
                        </Button>

                    </CardContent>
                </Card>
            </div>
        </div>
    </div>
  </div>
</template>