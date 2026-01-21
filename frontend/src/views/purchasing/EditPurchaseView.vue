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
import { Loader2, Plus, Trash2, Search, Save, ArrowLeft, Contact, FileText, Wrench } from 'lucide-vue-next'

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

// Formulario
const formData = reactive({
  document_number: '',
  order_type: 'OC',
  status_id: null,

  provider_id: null,
  provider_search: '',

  cost_center_id: null,
  reference: '',
  attention: '',
  provider_contact: '',

  payment_condition: '',
  currency: 'PEN',
  transfer_date: '',
  scope: '',
  items: []
})

// Búsqueda Proveedor
const providerResults = ref([])
const showProviderResults = ref(false)
const isSearchingProvider = ref(false)
let searchTimeout = null

// Cálculos
const subtotal = computed(() => {
  return formData.items.reduce((acc, item) => acc + (parseFloat(item.quantity || 0) * parseFloat(item.unit_price || 0)), 0)
})
const igv = computed(() => subtotal.value * 0.18)
const total = computed(() => subtotal.value + igv.value)

// --- CICLO DE VIDA ---
onMounted(async () => {
  await loadCatalogs()
  await loadOrderData()
})

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

async function loadOrderData() {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/purchases/${orderId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!res.ok) throw new Error("No se pudo cargar la orden")

    const data = await res.json()

    // Rellenar formulario con datos existentes
    formData.document_number = data.codigo
    formData.order_type = data.order_type || 'OC'

    // Buscar el ID del estado basado en el nombre (data.status viene como texto 'Emitida')
    const statusObj = catalogs.value.statuses.find(s => s.name === data.status)
    formData.status_id = statusObj ? statusObj.id : null

    // Proveedor
    formData.provider_search = data.provider_name
    // NOTA: El backend 'to_dict' actual no devuelve provider_id explícito,
    // pero al editar normalmente no cambiamos el proveedor.
    // Si necesitas cambiarlo, asegúrate que to_dict devuelva 'provider_id'.
    // Aquí asumimos que el usuario buscará de nuevo si quiere cambiarlo.
    // OJO: Necesitas que tu backend devuelva 'provider_id' en to_dict para que esto sea perfecto.
    // Por ahora, asumimos que provider_search visualmente es suficiente si no se toca.
    // Si el usuario toca el buscador, se reseteará el ID.

    // **TRUCO**: Como tu backend actual devuelve 'ruc', podemos buscarlo en local si provider_id falta.
    if(data.ruc) {
        // Podríamos hacer un fetch silencioso para obtener el ID real si es crítico
    }

    formData.cost_center_id = data.id_cc
    formData.reference = data.referencia
    formData.attention = data.atencion
    formData.provider_contact = data.contacto === 'N/A' ? '' : data.contacto
    formData.payment_condition = data.forma_pago
    formData.currency = data.moneda
    formData.transfer_date = data.fecha_traslado || ''
    formData.scope = data.alcance

    // Mapear Items del backend a la estructura del frontend
    formData.items = data.items.map(i => ({
        invoice_detail_text: i.invoice_detail_text,
        um: i.unit_of_measure,
        quantity: i.quantity,
        unit_price: i.unit_price
    }))

  } catch (e) {
    alert(e.message)
    router.push('/purchases')
  } finally {
    isLoading.value = false
  }
}

// --- PROVEEDOR (Igual que en crear) ---
async function handleProviderSearch() {
  const q = formData.provider_search.trim()
  if (!q) return
  isSearchingProvider.value = true
  clearTimeout(searchTimeout)

  searchTimeout = setTimeout(async () => {
    try {
      const token = await getAccessTokenSilently()
      const res = await fetch(`${FLASK_API_URL}/purchases/providers?q=${q}`, {
         headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
         providerResults.value = await res.json()
         showProviderResults.value = true
      }
    } catch (e) { console.error(e) }
    finally { isSearchingProvider.value = false }
  }, 400)
}

function selectProvider(p) {
  formData.provider_id = p.id
  formData.provider_search = p.name
  // Si cambia proveedor, actualizamos contacto sugerido
  if(!formData.provider_contact) formData.provider_contact = p.phone || p.email || ''
  showProviderResults.value = false
}

// --- ITEMS ---
function addItem() {
  formData.items.push({ invoice_detail_text: '', um: 'UND', quantity: 1, unit_price: 0 })
}
function removeItem(index) {
  formData.items.splice(index, 1)
}

// --- ACTUALIZAR (PUT) ---
async function handleUpdate() {
  if (formData.items.length === 0) return alert("Agregue items.")

  isSubmitting.value = true
  try {
    const token = await getAccessTokenSilently()

    // Buscamos el tipo de doc ID (aunque al editar raramente cambia)
    const docTypeName = formData.order_type === 'OC' ? 'Orden de Compra' : 'Orden de Servicio'
    const docType = catalogs.value.document_types.find(d => d.name.includes(docTypeName))

    const payload = {
      document_number: formData.document_number,
      order_type: formData.order_type,
      status_id: formData.status_id, // <--- AQUÍ SE ENVÍA EL NUEVO STATUS
      cost_center_id: formData.cost_center_id,
      document_type_id: docType ? docType.id : 1,

      // Si el usuario no tocó el buscador, provider_id podría ser null.
      // En ese caso, NO lo enviamos para que el backend mantenga el anterior.
      ...(formData.provider_id && { provider_id: formData.provider_id }),

      reference: formData.reference,
      attention: formData.attention,
      provider_contact: formData.provider_contact,
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

    const res = await fetch(`${FLASK_API_URL}/purchases/${orderId}`, {
      method: 'PUT', // <--- IMPORTANTE: PUT
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })

    if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Error al actualizar')
    }

    alert("Orden actualizada correctamente.")
    router.push('/purchases')

  } catch (e) {
    alert(e.message)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="max-w-6xl mx-auto p-6 space-y-6">

    <div v-if="isLoading" class="flex justify-center py-10">
        <Loader2 class="w-8 h-8 animate-spin text-gray-400" />
    </div>

    <div v-else class="animate-in fade-in">
        <div class="flex items-center justify-between mb-6">
            <div class="flex items-center gap-4">
                <Button variant="outline" size="icon" @click="$router.push('/purchases')">
                    <ArrowLeft class="w-4 h-4" />
                </Button>
                <div>
                    <h1 class="text-2xl font-bold text-gray-900">Editar Orden: {{ formData.document_number }}</h1>
                    <p class="text-sm text-gray-500">Modificar detalles o cambiar estado.</p>
                </div>
            </div>

            <Button class="bg-blue-600 hover:bg-blue-700" :disabled="isSubmitting" @click="handleUpdate">
                <Save class="w-4 h-4 mr-2" />
                <Loader2 v-if="isSubmitting" class="w-4 h-4 mr-2 animate-spin" />
                Guardar Cambios
            </Button>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

            <div class="lg:col-span-2 space-y-6">
                <Card>
                    <CardHeader class="pb-3 border-b bg-gray-50/50 py-3">
                        <CardTitle class="text-sm font-bold uppercase text-gray-600">Datos Principales</CardTitle>
                    </CardHeader>
                    <CardContent class="pt-6 grid gap-4">

                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <Label>Número Documento</Label>
                                <Input v-model="formData.document_number" class="font-mono font-bold text-blue-700 bg-blue-50" />
                            </div>
                            <div>
                                <Label>Estado</Label>
                                <Select v-model="formData.status_id">
                                    <SelectTrigger>
                                        <SelectValue placeholder="Seleccione estado" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem v-for="s in catalogs.statuses" :key="s.id" :value="s.id">
                                            {{ s.name }}
                                        </SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        <div class="relative">
                            <Label>Proveedor</Label>
                            <div class="relative mt-1">
                                <Search class="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
                                <Input
                                    v-model="formData.provider_search"
                                    @input="handleProviderSearch"
                                    placeholder="Buscar para cambiar..."
                                    class="pl-9"
                                />
                            </div>
                            <div v-if="showProviderResults" class="absolute z-10 w-full bg-white border rounded-md shadow-lg mt-1 max-h-40 overflow-y-auto">
                                <div v-for="p in providerResults" :key="p.id" @click="selectProvider(p)" class="p-2 hover:bg-gray-50 cursor-pointer text-sm border-b">
                                    {{ p.name }}
                                </div>
                            </div>
                        </div>

                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <Label>Atención (Nombre)</Label>
                                <Input v-model="formData.attention" />
                            </div>
                            <div class="relative">
                                <Label>Contacto (Tel/Email)</Label>
                                <div class="relative">
                                    <Contact class="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
                                    <Input v-model="formData.provider_contact" class="pl-9" />
                                </div>
                            </div>
                        </div>

                    </CardContent>
                </Card>

                <Card>
                    <CardHeader class="pb-3 border-b bg-gray-50/50 py-2 flex flex-row justify-between items-center">
                        <CardTitle class="text-sm font-bold uppercase text-gray-600">Items</CardTitle>
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
                                    <TableCell class="p-2"><Input type="number" v-model="item.quantity" class="h-8 text-right" /></TableCell>
                                    <TableCell class="p-2"><Input type="number" v-model="item.unit_price" class="h-8 text-right" /></TableCell>
                                    <TableCell class="p-2 text-center">
                                        <Button variant="ghost" size="icon" class="h-8 w-8 text-red-500" @click="removeItem(idx)">
                                            <Trash2 class="w-4 h-4" />
                                        </Button>
                                    </TableCell>
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
                        <CardTitle class="text-sm font-bold uppercase text-gray-600">Configuración</CardTitle>
                    </CardHeader>
                    <CardContent class="pt-4 space-y-4">

                        <div class="bg-gray-100 p-1 rounded-lg flex items-center shadow-inner">
                            <button @click="formData.order_type = 'OC'" class="flex-1 py-1.5 rounded text-xs font-bold transition-all" :class="formData.order_type === 'OC' ? 'bg-white text-blue-700 shadow' : 'text-gray-500'">OC</button>
                            <button @click="formData.order_type = 'OS'" class="flex-1 py-1.5 rounded text-xs font-bold transition-all" :class="formData.order_type === 'OS' ? 'bg-white text-orange-600 shadow' : 'text-gray-500'">OS</button>
                        </div>

                        <div>
                            <Label>Centro de Costo</Label>
                            <Select v-model="formData.cost_center_id">
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem v-for="cc in catalogs.cost_centers" :key="cc.id" :value="cc.id">{{ cc.code }}</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div><Label>Moneda</Label>
                            <Select v-model="formData.currency">
                                <SelectTrigger><SelectValue /></SelectTrigger>
                                <SelectContent><SelectItem value="PEN">Soles</SelectItem><SelectItem value="USD">Dólares</SelectItem></SelectContent>
                            </Select>
                        </div>

                        <div><Label>Forma Pago</Label><Input v-model="formData.payment_condition" /></div>
                        <div><Label>Fecha Entrega</Label><Input type="date" v-model="formData.transfer_date" /></div>

                        <div v-if="formData.order_type === 'OS'">
                            <Label>Alcance</Label>
                            <textarea v-model="formData.scope" rows="5" class="w-full text-sm border p-2 rounded"></textarea>
                        </div>

                    </CardContent>
                </Card>
            </div>

        </div>
    </div>
  </div>
</template>