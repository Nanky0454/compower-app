<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { useRouter } from 'vue-router'

// --- UI Components ---
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Loader2, Plus, Trash2, Search, FileText, Wrench } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()
const router = useRouter()
const FLASK_API_URL = `${import.meta.env.VITE_API_URL}/api`

// --- ESTADO DEL FORMULARIO ---
const isLoading = ref(true)
const isSubmitting = ref(false)
const catalogs = ref({ document_types: [], statuses: [], cost_centers: [] })

// Configuración del Correlativo
const correlativeSeries = ref('026')
const correlativeNumber = ref(1) // Empieza en 1 -> 001

// Selector de Tipo (Visual)
const selectedType = ref('OC') // 'OC' (Compra) o 'OS' (Servicio)

const formData = reactive({
  provider_id: null,
  provider_search: '',
  provider_data: null, // Para mostrar dirección/ruc
  cost_center_id: null,

  // Campos del Formato Excel
  reference: '',
  attention: '',
  payment_condition: '',
  currency: 'PEN',
  transfer_date: '',
  scope: '', // Alcance

  items: []
})

// --- Búsqueda de Proveedor ---
const providerResults = ref([])
const showProviderResults = ref(false)
const isSearchingProvider = ref(false)
let searchTimeout = null

// --- CÁLCULOS ---
const formattedCorrelative = computed(() => {
  const num = String(correlativeNumber.value).padStart(3, '0')
  return `${correlativeSeries.value}-${num}`
})

const subtotal = computed(() => {
  return formData.items.reduce((acc, item) => acc + (parseFloat(item.quantity || 0) * parseFloat(item.unit_price || 0)), 0)
})

const igv = computed(() => subtotal.value * 0.18)
const total = computed(() => subtotal.value + igv.value)

// --- MÉTODOS ---

onMounted(async () => {
  await loadCatalogs()
  await fetchLastCorrelative()
  // Agregar una línea vacía al inicio
  addItem()
})

async function loadCatalogs() {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/purchases/catalogs`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) catalogs.value = await res.json()
  } catch (e) { console.error(e) }
  finally { isLoading.value = false }
}

async function fetchLastCorrelative() {
  // Aquí podrías consultar al backend cuál es el último número.
  // Por ahora, lo dejamos en 026-001 como pediste, o incrementamos si ya existen.
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/purchases/`, {
       headers: { 'Authorization': `Bearer ${token}` }
    })
    if(res.ok) {
        const orders = await res.json()
        if(orders.length > 0) {
            // Lógica simple: Buscar el último del mismo tipo y sumar 1
            // Si quieres forzar 026-001, puedes borrar esto.
            const lastOrder = orders[0] // Asumiendo que viene ordenado desc
            if(lastOrder.codigo && lastOrder.codigo.startsWith('026-')) {
                const parts = lastOrder.codigo.split('-')
                const lastNum = parseInt(parts[1])
                correlativeNumber.value = lastNum + 1
            }
        }
    }
  } catch(e) { console.error("Error obteniendo correlativo", e)}
}

// --- LÓGICA DE PROVEEDOR ---
function handleProviderSearch() {
  const q = formData.provider_search.trim()
  if (!q) return
  isSearchingProvider.value = true
  clearTimeout(searchTimeout)

  searchTimeout = setTimeout(async () => {
    try {
      const token = await getAccessTokenSilently()
      // Usamos el endpoint de búsqueda local primero
      const res = await fetch(`${FLASK_API_URL}/purchases/providers?q=${q}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        providerResults.value = await res.json()
        showProviderResults.value = true
      }

      // Si es RUC y no hay locales, buscar en SUNAT (Tu API lookup)
      if (providerResults.value.length === 0 && /^\d{11}$/.test(q)) {
         const sunatRes = await fetch(`${FLASK_API_URL}/purchases/lookup-provider/${q}`, {
            headers: { 'Authorization': `Bearer ${token}` }
         })
         if(sunatRes.ok) {
            const sunatData = await sunatRes.json()
            providerResults.value = [sunatData]
            showProviderResults.value = true
         }
      }
    } catch (e) { console.error(e) }
    finally { isSearchingProvider.value = false }
  }, 400)
}

function selectProvider(p) {
  formData.provider_id = p.id // Puede ser null si es nuevo de SUNAT (se creará en backend)
  formData.provider_data = p
  formData.provider_search = p.name || p.razon_social

  // Si viene de SUNAT, llenamos dirección automáticamente
  if(p.address || p.direccion) {
      // Podríamos ponerlo en 'Atención' o dejarlo visual
  }
  showProviderResults.value = false
}

// --- LÓGICA DE ITEMS ---
function addItem() {
  formData.items.push({
    invoice_detail_text: '', // Descripción manual
    um: 'UND',
    quantity: 1,
    unit_price: 0
  })
}

function removeItem(index) {
  formData.items.splice(index, 1)
}

// --- GUARDAR ---
async function handleSubmit() {
  if (!formData.provider_search || formData.items.length === 0) {
    alert("Seleccione un proveedor y agregue al menos un item.")
    return
  }

  isSubmitting.value = true
  try {
    const token = await getAccessTokenSilently()

    // Buscar el ID del tipo de documento según selección (OC o OS)
    // Asumimos que en BD tienes "Orden de Compra" y "Orden de Servicio"
    const docTypeName = selectedType.value === 'OC' ? 'Orden de Compra' : 'Orden de Servicio'
    const docType = catalogs.value.document_types.find(d => d.name.includes(docTypeName) || d.name === selectedType.value)
    const docTypeId = docType ? docType.id : 1 // Fallback

    // Buscar estado "Pendiente" o "Emitida"
    const status = catalogs.value.statuses.find(s => s.name === 'Emitida') || catalogs.value.statuses[0]

    const payload = {
      document_number: formattedCorrelative.value,
      provider_id: formData.provider_id, // Si es null, el backend debe manejar creación si mandas todos los datos (requiere ajuste en backend si no guardaste antes)
      // *Truco*: Si el proveedor vino de SUNAT y no tiene ID, el backend lookup lo devolvió.
      // Asegúrate de que tu backend 'create_purchase' acepte crear proveedor al vuelo o
      // asegurate de haber guardado el proveedor al seleccionarlo.

      // NOTA: Para simplificar, asumo que el proveedor YA EXISTE o el backend lo maneja.
      // Si seleccionaste de la lista 'lookup', ese endpoint YA lo guardó en BD local, así que p.id existe.

      document_type_id: docTypeId,
      status_id: status.id,
      cost_center_id: formData.cost_center_id,

      // Campos nuevos
      reference: formData.reference,
      attention: formData.attention,
      scope: formData.scope,
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

    // Validación extra por si provider_id es null (caso borde)
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
    router.push('/purchases') // Volver a la lista

  } catch (e) {
    alert(e.message)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="max-w-5xl mx-auto p-6 space-y-6">

    <div class="flex flex-col md:flex-row justify-between items-center gap-4">
      <div>
        <h1 class="text-3xl font-bold tracking-tight text-gray-900">Nueva Orden</h1>
        <p class="text-sm text-gray-500">Generación de OC/OS y control de servicios.</p>
      </div>

      <div class="bg-gray-100 p-1 rounded-lg flex items-center shadow-inner">
        <button
          @click="selectedType = 'OC'"
          class="flex items-center gap-2 px-6 py-2 rounded-md text-sm font-bold transition-all"
          :class="selectedType === 'OC' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
        >
          <FileText class="w-4 h-4" /> Orden de Compra
        </button>
        <button
          @click="selectedType = 'OS'"
          class="flex items-center gap-2 px-6 py-2 rounded-md text-sm font-bold transition-all"
          :class="selectedType === 'OS' ? 'bg-white text-orange-600 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
        >
          <Wrench class="w-4 h-4" /> Orden de Servicio
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <div class="lg:col-span-2 space-y-6">

        <Card>
          <CardHeader class="pb-3 border-b">
            <div class="flex justify-between items-center">
              <CardTitle class="text-base font-bold uppercase text-gray-700">1. Datos Generales</CardTitle>
              <div class="bg-blue-50 text-blue-700 px-3 py-1 rounded font-mono font-bold text-lg border border-blue-200">
                {{ formattedCorrelative }}
              </div>
            </div>
          </CardHeader>
          <CardContent class="pt-4 grid gap-4">

            <div class="relative">
              <Label>Proveedor (Buscar por RUC o Nombre)</Label>
              <div class="relative">
                <Search class="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
                <Input
                  v-model="formData.provider_search"
                  @input="handleProviderSearch"
                  placeholder="Ej: 20123456789 o Compower..."
                  class="pl-9"
                />
                <Loader2 v-if="isSearchingProvider" class="absolute right-3 top-2.5 h-4 w-4 animate-spin text-gray-400" />
              </div>

              <div v-if="showProviderResults" class="absolute z-10 w-full bg-white border rounded-md shadow-lg mt-1 max-h-60 overflow-y-auto">
                 <div
                    v-for="p in providerResults"
                    :key="p.ruc"
                    @click="selectProvider(p)"
                    class="p-3 hover:bg-gray-50 cursor-pointer border-b last:border-0"
                 >
                    <div class="font-bold text-sm">{{ p.name || p.razon_social }}</div>
                    <div class="text-xs text-gray-500">RUC: {{ p.ruc || p.numero_documento }}</div>
                 </div>
              </div>
            </div>

            <div v-if="formData.provider_data" class="bg-gray-50 p-3 rounded text-sm space-y-1 border">
                <div class="font-bold text-gray-800">{{ formData.provider_data.name || formData.provider_data.razon_social }}</div>
                <div class="text-gray-500">RUC: {{ formData.provider_data.ruc }}</div>
                <div class="text-gray-500">{{ formData.provider_data.address || formData.provider_data.direccion || 'Sin dirección registrada' }}</div>
            </div>

            <div class="grid grid-cols-2 gap-4">
               <div>
                  <Label>Atención (Contacto)</Label>
                  <Input v-model="formData.attention" placeholder="Sr. Juan Pérez" />
               </div>
               <div>
                  <Label>Referencia</Label>
                  <Input v-model="formData.reference" placeholder="Cotización #123" />
               </div>
            </div>

          </CardContent>
        </Card>

        <Card>
           <CardHeader class="pb-3 border-b bg-gray-50 flex flex-row justify-between items-center">
             <CardTitle class="text-base font-bold uppercase text-gray-700">2. Detalle de Items</CardTitle>
             <Button size="sm" variant="outline" @click="addItem">
               <Plus class="w-4 h-4 mr-2"/> Agregar Item
             </Button>
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
                   <TableCell class="p-2">
                     <Input v-model="item.invoice_detail_text" class="h-8" placeholder="Descripción del producto/servicio..." />
                   </TableCell>
                   <TableCell class="p-2">
                      <Select v-model="item.um">
                        <SelectTrigger class="h-8"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="UND">UND</SelectItem>
                          <SelectItem value="SERV">SERV</SelectItem>
                          <SelectItem value="GLB">GLB</SelectItem>
                          <SelectItem value="MTS">MTS</SelectItem>
                          <SelectItem value="KG">KG</SelectItem>
                        </SelectContent>
                      </Select>
                   </TableCell>
                   <TableCell class="p-2">
                     <Input type="number" v-model="item.quantity" class="h-8 text-right" min="1" step="0.01" />
                   </TableCell>
                   <TableCell class="p-2">
                     <Input type="number" v-model="item.unit_price" class="h-8 text-right" min="0" step="0.01" />
                   </TableCell>
                   <TableCell class="p-2 text-center">
                     <Button variant="ghost" size="icon" class="h-8 w-8 text-red-500" @click="removeItem(idx)">
                       <Trash2 class="w-4 h-4" />
                     </Button>
                   </TableCell>
                 </TableRow>
               </TableBody>
             </Table>

             <div class="p-4 bg-gray-50 border-t flex flex-col items-end space-y-1">
                <div class="flex justify-between w-48 text-sm">
                   <span class="text-gray-600">Subtotal:</span>
                   <span class="font-medium">{{ formData.currency }} {{ subtotal.toFixed(2) }}</span>
                </div>
                <div class="flex justify-between w-48 text-sm">
                   <span class="text-gray-600">IGV (18%):</span>
                   <span class="font-medium">{{ formData.currency }} {{ igv.toFixed(2) }}</span>
                </div>
                <div class="flex justify-between w-48 text-lg font-bold text-gray-900 pt-2 border-t border-gray-200">
                   <span>Total:</span>
                   <span>{{ formData.currency }} {{ total.toFixed(2) }}</span>
                </div>
             </div>

           </CardContent>
        </Card>

      </div>

      <div class="space-y-6">

        <Card>
          <CardHeader class="pb-3 border-b">
             <CardTitle class="text-base font-bold uppercase text-gray-700">3. Condiciones</CardTitle>
          </CardHeader>
          <CardContent class="pt-4 space-y-4">

             <div>
                <Label>Centro de Costo</Label>
                <Select v-model="formData.cost_center_id">
                  <SelectTrigger><SelectValue placeholder="Seleccione..." /></SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="cc in catalogs.cost_centers" :key="cc.id" :value="cc.id">
                      {{ cc.code }} - {{ cc.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
             </div>

             <div>
                <Label>Moneda</Label>
                <Select v-model="formData.currency">
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PEN">Soles (S/.)</SelectItem>
                    <SelectItem value="USD">Dólares ($)</SelectItem>
                  </SelectContent>
                </Select>
             </div>

             <div>
                <Label>Forma de Pago</Label>
                <Input v-model="formData.payment_condition" placeholder="Ej: Crédito 30 días" />
             </div>

             <div>
                <Label>Fecha Traslado / Ejecución</Label>
                <Input type="date" v-model="formData.transfer_date" />
             </div>

             <div class="pt-2">
                <Label>Alcance (Detalle Técnico)</Label>
                <Textarea
                   v-model="formData.scope"
                   rows="6"
                   placeholder="Ingrese detalles técnicos, alcance del servicio o notas adicionales..."
                   class="resize-none text-xs"
                />
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
</template>