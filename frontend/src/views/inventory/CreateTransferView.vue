<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
// Componentes UI
import { Button } from '@/components/ui/button/index.js'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Label } from '@/components/ui/label/index.js'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Loader2, Search, Plus, Trash2, Truck, MapPin, FileText, Package } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()
const FLASK_API_URL = `${import.meta.env.VITE_API_URL}/api`

// --- CATÁLOGO 20 SUNAT (MOTIVOS) ---
const transferReasons = [
  { code: '01', label: 'Venta' },
  { code: '02', label: 'Compra' },
  { code: '04', label: 'Traslado entre establecimientos' },
  { code: '08', label: 'Importación' },
  { code: '09', label: 'Exportación' },
  { code: '13', label: 'Otros' },
  { code: '14', label: 'Venta sujeta a confirmación' },
  { code: '18', label: 'Traslado emisor itinerante' },
]

const getToday = () => {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const isLoading = ref(true)
const isSubmitting = ref(false)
const isFetchingCorrelative = ref(false)
const error = ref(null)
const successMessage = ref(null)

// --- DATOS MAESTROS ---
const warehouses = ref([])
const ubiDeptos = ref([])
const ubiProvs = ref([])
const ubiDists = ref([])
const cost_centers = ref([])

const warehouseProducts = ref([])

const mode = ref('internal')

const formData = reactive({
  cost_center_id: null,
  origin_warehouse_id: null,
  destination_warehouse_id: null,
  gre_type: 'remitente',
  serie: 'T001',
  numero: 1,
  fecha_de_emision: getToday(),
  fecha_de_inicio_de_traslado: getToday(),
  motivo_traslado_codigo: '13',
  motivo_manual: 'Otros',
  observaciones: '',
  client_search: '',
  client_id: null,
  client_ruc: '',
  client_name: '',
  client_address: 'Sin dirección',
  location_id: null,
  location_name: '',
  punto_llegada_ubigeo: '',
  punto_llegada_direccion: '',
  transport_type: 'private',
  driver_id: null,
  driver_doc_type: '1',
  driver_doc_number: '',
  driver_name: '',
  driver_lastname: '',
  driver_license: '',
  vehicle_plate: 'BHP781',
  vehicle_brand: 'TOYOTA',
  transport_provider_id: null,
  transport_ruc: '',
  transport_name: '',
  remitente_original_ruc: '',
  remitente_original_rs: ''
})

const showNewLocationForm = ref(false)
const newLoc = reactive({ name: '', dept_code: '', prov_code: '', dist_code: '' })

// --- BÚSQUEDAS ---
const showClientResults = ref(false)
const clientResults = ref([])
const isSearchingClient = ref(false)
let searchTimeout = null

const driverSearch = ref('')
const showDriverResults = ref(false)
const driverResults = ref([])
const isSearchingDriver = ref(false)

const transportSearch = ref('')
const showTransportResults = ref(false)
const transportResults = ref([])
const isSearchingTransport = ref(false)

const lineItems = ref([])
const productSearch = ref('')
const clientLocations = ref([])

// =======================================================================
// CARGA INICIAL
// =======================================================================
onMounted(async () => {
  try {
    const token = await getAccessTokenSilently()
    const headers = { 'Authorization': `Bearer ${token}` }
    const [whRes, deptRes, ccRes] = await Promise.all([
      fetch(`${FLASK_API_URL}/warehouses`, { headers }),
      fetch(`${FLASK_API_URL}/ubigeos/departamentos`, { headers }),
      fetch(`${FLASK_API_URL}/cost-centers`, { headers })
    ])
    if (whRes.ok) warehouses.value = await whRes.json()
    if (deptRes.ok) ubiDeptos.value = await deptRes.json()
    if (ccRes.ok) cost_centers.value = await ccRes.json()
  } catch (e) { error.value = e.message }
  finally { isLoading.value = false }
})

// =======================================================================
// LOGICA DE STOCK POR ALMACÉN
// =======================================================================
watch(() => formData.origin_warehouse_id, async (newId) => {
  lineItems.value = []
  warehouseProducts.value = []
  productSearch.value = ''

  if (mode.value === 'internal' && newId) {
    const other = warehouses.value.find(w => w.id !== newId)
    if (other) formData.destination_warehouse_id = other.id
  }

  if (!newId) return

  isLoading.value = true
  try {
    const token = await getAccessTokenSilently()
    // OJO: Si esta ruta del backend solo devuelve stock > 0,
    // necesitamos modificar el backend también.
    const res = await fetch(`${FLASK_API_URL}/inventory/warehouse/${newId}/products`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      warehouseProducts.value = await res.json()
    }
  } catch (e) {
    console.error("Error cargando stock del almacén:", e)
  } finally {
    isLoading.value = false
  }
})

// --- COMPUTED PARA FILTRAR ---
const filteredProducts = computed(() => {
  if (!formData.origin_warehouse_id) return []
  if (!productSearch.value) return []

  const q = productSearch.value.toLowerCase()
  return warehouseProducts.value.filter(p =>
    p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q)
  ).slice(0, 10)
})

// --- ¡FUNCIÓN MODIFICADA! Ya no bloquea si excedes el stock ---
function validateStock(item) {
  // Solo aseguramos que no sea negativo
  if (item.quantity < 0) {
    item.quantity = 1
  }
  // ELIMINADO: La lógica que forzaba item.quantity = item.max_stock
}

function addItem(p) {
  const exists = lineItems.value.find(i => i.id === p.id)
  if (exists) {
    alert("El producto ya está en la lista")
    return
  }

  lineItems.value.push({
    ...p,
    quantity: 1,
    unit_sunat: p.sunat_code,
    max_stock: p.stock // Se mantiene solo como referencia visual
  })
  productSearch.value = ''
}

// =======================================================================
// CORRELATIVO
// =======================================================================
async function fetchNextCorrelative() {
  if (!formData.serie || formData.serie.length < 4) return
  isFetchingCorrelative.value = true
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/gre/next-correlative?serie=${formData.serie}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      const data = await res.json()
      formData.numero = data.next_number
    }
  } catch (e) { console.error("Error obteniendo correlativo:", e) }
  finally { isFetchingCorrelative.value = false }
}

watch(() => formData.gre_type, (newType) => {
  formData.serie = 'T002'
})

watch(() => formData.serie, async (newSerie) => {
  if (newSerie && newSerie.length >= 4) {
    await fetchNextCorrelative()
  }
}, { immediate: true })

// =======================================================================
// LOGICA CLIENTE Y UBICACIONES
// =======================================================================
async function handleClientSearch(isFocus = false) {
  const query = formData.client_search.trim()
  if ((isFocus && query === '') || (query === '' && !isFocus)) {
    await searchLocalProviders(query, 'client')
    return
  }
  isSearchingClient.value = true
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(async () => {
    try {
      const token = await getAccessTokenSilently()
      if (/^\d{11}$/.test(query)) {
        const localRes = await fetch(`${FLASK_API_URL}/purchases/providers?q=${query}`, { headers: { 'Authorization': `Bearer ${token}` } })
        const localData = await localRes.json()
        if (localData.length > 0) {
          clientResults.value = localData
          showClientResults.value = true
        } else {
          const res = await fetch(`${FLASK_API_URL}/purchases/lookup-provider/${query}`, { headers: { 'Authorization': `Bearer ${token}` } })
          if (res.ok) {
            clientResults.value = [await res.json()]
            showClientResults.value = true
          } else clientResults.value = []
        }
      } else {
        await searchLocalProviders(query, 'client')
      }
    } catch (e) { console.error(e) }
    finally { isSearchingClient.value = false }
  }, 300)
}

function closeClientResults() { setTimeout(() => showClientResults.value = false, 200) }

async function selectClient(client) {
  const ruc = client.ruc || client.document_number || ''
  const name = client.name || client.razon_social || ''
  const address = client.address || client.direccion || 'Sin dirección'

  formData.client_id = client.id || null
  formData.client_ruc = ruc
  formData.client_name = name
  formData.client_address = address
  formData.client_search = `${ruc} - ${name}`
  formData.punto_llegada_direccion = address
  formData.punto_llegada_ubigeo = client.ubigeo_code || client.ubigeo || '150101'
  formData.location_name = 'DIRECCIÓN FISCAL'
  showClientResults.value = false
  clientResults.value = []
  if (client.id) await loadClientLocations(client.id)
  else clientLocations.value = []
  if (!client.id && address !== 'Sin dirección') {
    showNewLocationForm.value = true
    newLoc.name = "OFICINA PRINCIPAL"
  }
}

async function loadClientLocations(providerId) {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/locations/?provider_id=${providerId}`, { headers: { 'Authorization': `Bearer ${token}` } })
    if (res.ok) clientLocations.value = await res.json()
  } catch (e) { console.error(e) }
}

watch(() => formData.location_id, (newId) => {
  const loc = clientLocations.value.find(l => l.id === newId)
  if (loc) {
    formData.punto_llegada_ubigeo = loc.ubigeo_code || loc.ubigeo || '150101'
    const direccionBD = loc.address || ''
    const esGenerica = direccionBD === 'Sin dirección' || direccionBD.trim() === ''
    formData.punto_llegada_direccion = esGenerica ? loc.name : `${loc.name} - ${direccionBD}`
    formData.location_name = loc.name
  }
})

// =======================================================================
// NUEVA SEDE
// =======================================================================
async function handleDeptChange(code) {
  newLoc.dept_code = code; newLoc.prov_code = ''; newLoc.dist_code = ''
  const token = await getAccessTokenSilently()
  const res = await fetch(`${FLASK_API_URL}/ubigeos/children/${code}`, { headers: { 'Authorization': `Bearer ${token}` } })
  ubiProvs.value = await res.json()
}
async function handleProvChange(code) {
  newLoc.prov_code = code; newLoc.dist_code = ''
  const token = await getAccessTokenSilently()
  const res = await fetch(`${FLASK_API_URL}/ubigeos/children/${code}`, { headers: { 'Authorization': `Bearer ${token}` } })
  ubiDists.value = await res.json()
}
async function saveNewLocation() {
  if (!newLoc.name || !newLoc.dist_code) { alert("Nombre y Distrito obligatorios"); return }
  try {
    const token = await getAccessTokenSilently()
    const payload = {
      name: newLoc.name.toUpperCase(),
      address: formData.client_address,
      ruc: formData.client_ruc,
      ubigeo_code: newLoc.dist_code,
      provider_id: formData.client_id
    }
    const res = await fetch(`${FLASK_API_URL}/locations/`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (res.ok) {
      const saved = await res.json()
      clientLocations.value.push(saved)
      formData.location_id = saved.id
      showNewLocationForm.value = false
      newLoc.name = ''; newLoc.dept_code = ''; newLoc.prov_code = ''; newLoc.dist_code = ''
    } else {
      const err = await res.json()
      alert("Error: " + (err.error || "No se pudo guardar"))
    }
  } catch (e) { console.error(e); alert("Error de conexión") }
}

// =======================================================================
// CHOFERES Y TRANSPORTE
// =======================================================================
async function handleDriverSearch(isFocus = false) {
  // --- CORRECCIÓN: Si el usuario escribe, limpiamos la selección previa ---
  if (!isFocus) {
    // 1. Borramos el ID para que el sistema sepa que ya no es el de la base de datos
    formData.driver_id = null;

    // 2. Limpiamos datos vinculados para no mezclar (ej: licencia del anterior con nombre nuevo)
    formData.driver_doc_number = '';
    formData.driver_license = '';
    formData.driver_lastname = '';

    // 3. Asignamos lo que escribes en el input al campo de nombre del formulario
    // Así, si es un chofer manual, se guardará lo que estás escribiendo.
    formData.driver_name = driverSearch.value;
  }
  // -----------------------------------------------------------------------

  const query = driverSearch.value.trim()
  if (isFocus && query === '') { await fetchDrivers(''); return }
  if (query === '' && !isFocus) return
  isSearchingDriver.value = true
  setTimeout(async () => { await fetchDrivers(query); isSearchingDriver.value = false }, 300)
}
async function fetchDrivers(query) {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/hr/drivers?q=${query}`, { headers: { 'Authorization': `Bearer ${token}` } })
    if (res.ok) { driverResults.value = await res.json(); showDriverResults.value = true }
  } catch (e) { console.error(e) }
}
function selectDriver(driver) {
  // 1. Guardamos el ID
  formData.driver_id = driver.id

  // 2. Llenamos los campos separados (Esto hará que aparezcan en tus nuevos inputs)
  formData.driver_name = driver.first_name
  formData.driver_lastname = driver.last_name
  formData.driver_doc_number = driver.document_number

  // 3. Licencia (si existe)
  formData.driver_license = (driver.licenses && driver.licenses.length > 0)
    ? driver.licenses[0].license_number
    : ''

  // 4. Opcional: Ponemos el nombre completo en el buscador para referencia visual
  driverSearch.value = `${driver.first_name} ${driver.last_name}`

  // 5. Cerramos la lista
  showDriverResults.value = false
}
function closeDriverResults() { setTimeout(() => showDriverResults.value = false, 200) }
async function handleTransportSearch(isFocus = false) {
  const query = transportSearch.value.trim()
  if ((isFocus && query === '') || (query === '' && !isFocus)) { await searchLocalProviders(query, 'transport'); return }
  isSearchingTransport.value = true
  setTimeout(async () => { await searchLocalProviders(query, 'transport'); isSearchingTransport.value = false }, 300)
}
function selectTransport(provider) {
  formData.transport_provider_id = provider.id
  formData.transport_ruc = provider.ruc || provider.document_number
  formData.transport_name = provider.name || provider.razon_social
  transportSearch.value = `${formData.transport_ruc} - ${formData.transport_name}`
  showTransportResults.value = false
}
function closeTransportResults() { setTimeout(() => showTransportResults.value = false, 200) }
async function searchLocalProviders(query, type) {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/purchases/providers?q=${query}`, { headers: { 'Authorization': `Bearer ${token}` } })
    if (res.ok) {
      const data = await res.json()
      if (type === 'client') { clientResults.value = data; showClientResults.value = true }
      else { transportResults.value = data; showTransportResults.value = true }
    }
  } catch (e) { console.error(e) }
}

// =======================================================================
// ENVÍO Y DESCARGA
// =======================================================================
async function downloadGeneratedPDF(transferId, docName) {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${FLASK_API_URL}/gre/download-pdf/${transferId}`, {
      method: 'GET',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!res.ok) throw new Error("Error al descargar el PDF generado.")
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `GRE-${docName}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (e) { console.error("Error en descarga automática:", e) }
}

async function handleSubmit() {
  isSubmitting.value = true
  error.value = null
  successMessage.value = null

  try {
    const token = await getAccessTokenSilently()

    if (!formData.origin_warehouse_id) throw new Error("Seleccione un almacén de origen")

    if (mode.value === 'external') {
        if (!formData.client_id && !formData.client_name) throw new Error("Debe seleccionar un Cliente destinatario.")
        if (!formData.location_id && !showNewLocationForm.value) throw new Error("Debe seleccionar una Sede (Punto de Llegada).")
        if (formData.transport_type === 'private') {
            if (!formData.driver_doc_number || !formData.driver_name) throw new Error("Datos del Chofer obligatorios.")
            if (!formData.vehicle_plate) throw new Error("La Placa del vehículo es obligatoria.")
        } else {
            if (!formData.transport_ruc || !formData.transport_name) throw new Error("Datos de la Empresa de Transporte obligatorios.")
        }
    }

    const originWarehouse = warehouses.value.find(w => w.id === formData.origin_warehouse_id)
    const ubigeoPartida = originWarehouse.ubigeo || originWarehouse.ubigeo_code || '150101'

    if (mode.value === 'external' && !originWarehouse.address) {
      throw new Error(`El almacén "${originWarehouse.name}" no tiene dirección configurada.`)
    }

    let finalBody = {}
    let endpoint = ''

    if (mode.value === 'internal') {
      endpoint = '/transfers'
      finalBody = {
        transfer_data: {
          cost_center_id: formData.cost_center_id,
          origin_warehouse_id: formData.origin_warehouse_id,
          destination_warehouse_id: formData.destination_warehouse_id,
          fecha_de_emision: formData.fecha_de_emision,
          items: lineItems.value.map(i => ({ product_id: i.id, quantity: i.quantity }))
        }
      }
    } else {
      endpoint = '/gre/enviar'
      const itemsFormatted = lineItems.value.map(i => ({
        codigo: i.sku,
        descripcion: i.name,
        cantidad: parseFloat(i.quantity),
        unidad_de_medida: i.unit_sunat || 'NIU'
      }))

      const motivoObj = transferReasons.find(r => r.code === formData.motivo_traslado_codigo)
      const motivoTexto = motivoObj ? motivoObj.label : 'VENTA'

      finalBody = {
        cost_center_id: formData.cost_center_id,
        serie: formData.serie,
        numero: parseInt(formData.numero),
        fecha_de_emision: formData.fecha_de_emision,
        fecha_de_inicio_de_traslado: formData.fecha_de_inicio_de_traslado,
        observaciones: formData.observaciones,
        cliente_tipo_de_documento: "6",
        cliente_numero_de_documento: formData.client_ruc,
        cliente_denominacion: formData.client_name,
        motivo_de_traslado: formData.motivo_traslado_codigo,
        motivo: motivoTexto,
        peso_bruto_total: 1.0,
        punto_de_partida_ubigeo: ubigeoPartida,
        punto_de_partida_direccion: originWarehouse.address,
        punto_de_llegada_ubigeo: formData.punto_llegada_ubigeo || '150101',
        punto_de_llegada_direccion: formData.punto_llegada_direccion || formData.client_address,
        items: itemsFormatted,
        gre_type: formData.gre_type
      }

      if (formData.transport_type === 'private') {
        finalBody.tipo_de_transporte = "02"
        finalBody.transportista_placa_numero = formData.vehicle_plate
        finalBody.marca = formData.vehicle_brand || ''
        finalBody.conductor_documento_tipo = formData.driver_doc_type
        finalBody.conductor_documento_numero = formData.driver_doc_number
        finalBody.conductor_nombre = formData.driver_name
        finalBody.conductor_apellidos = formData.driver_lastname
        finalBody.licencia = formData.driver_license
      } else {
        finalBody.tipo_de_transporte = "01"
        finalBody.transportista_documento_numero = formData.transport_ruc
        finalBody.transportista_denominacion = formData.transport_name
      }
    }

    const res = await fetch(`${FLASK_API_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(finalBody)
    })

    const data = await res.json()
    if (!res.ok) throw new Error(data.error || "Error en el servidor")

    successMessage.value = mode.value === 'internal'
      ? "Transferencia interna realizada correctamente."
      : `Guía enviada a SUNAT con éxito. Ticket: ${data.numTicket || 'OK'}`

    if (mode.value === 'external' && data.transfer_id) {
        await downloadGeneratedPDF(data.transfer_id, `${formData.serie}-${formData.numero}`)
    }

    lineItems.value = []
    if (mode.value === 'external') {
      await fetchNextCorrelative()
    }

  } catch (e) {
    console.error(e)
    error.value = e.message
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="max-w-7xl mx-auto p-4 space-y-5 bg-gray-50/50 min-h-screen">

    <div class="flex flex-col md:flex-row justify-between items-center gap-4 bg-white p-4 rounded-lg shadow-sm border border-gray-100">
      <div class="flex items-center gap-4">
        <div class="bg-gray-900 text-white p-2 rounded-lg">
          <Truck v-if="mode === 'external'" class="w-6 h-6" />
          <Package v-else class="w-6 h-6" />
        </div>
        <div>
          <h1 class="text-xl font-bold text-gray-800 tracking-tight">Gestión de Traslados</h1>
          <p class="text-xs text-gray-500">Administra movimientos internos y guías de remisión</p>
        </div>
      </div>

      <div class="flex flex-col sm:flex-row gap-3 items-center">
        <div class="bg-gray-100 p-1 rounded-lg flex text-xs font-medium">
          <label class="cursor-pointer px-4 py-1.5 rounded-md transition-all flex items-center gap-2"
            :class="mode === 'internal' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'">
            <input type="radio" value="internal" v-model="mode" class="hidden">
            <span>Interno</span>
          </label>
          <label class="cursor-pointer px-4 py-1.5 rounded-md transition-all flex items-center gap-2"
            :class="mode === 'external' ? 'bg-white shadow-sm text-blue-700' : 'text-gray-500 hover:text-gray-700'">
            <input type="radio" value="external" v-model="mode" class="hidden">
            <span>Guía Remisión</span>
          </label>
        </div>

        <div class="flex gap-2">
          <div class="flex flex-col bg-white border px-3 py-1 rounded-md shadow-sm">
            <span class="text-[9px] font-bold text-gray-400 uppercase tracking-wider">Emisión</span>
            <input type="date" v-model="formData.fecha_de_emision" class="text-xs border-none p-0 h-4 focus:ring-0 font-medium text-gray-700">
          </div>
          <div class="flex flex-col bg-white border px-3 py-1 rounded-md shadow-sm">
            <span class="text-[9px] font-bold text-gray-400 uppercase tracking-wider">Traslado</span>
            <input type="date" v-model="formData.fecha_de_inicio_de_traslado" class="text-xs border-none p-0 h-4 focus:ring-0 font-medium text-gray-700">
          </div>
        </div>
      </div>
    </div>

    <div v-if="error" class="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm border border-red-100 flex items-center gap-2 shadow-sm animate-in fade-in slide-in-from-top-2">
      <span class="font-bold">Error:</span> {{ error }}
    </div>
    <div v-if="successMessage" class="bg-green-50 text-green-700 px-4 py-3 rounded-lg text-sm border border-green-100 flex items-center gap-2 shadow-sm animate-in fade-in slide-in-from-top-2">
      <span class="font-bold">Éxito:</span> {{ successMessage }}
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">

      <div class="lg:col-span-4 space-y-4">

        <Card class="shadow-sm border-gray-200">
          <CardHeader class="py-2 px-4">
            <CardTitle class="text-xs font-bold text-gray-500 uppercase tracking-wide flex items-center gap-2">
              <MapPin class="w-3.5 h-3.5" /> Punto de Partida
            </CardTitle>
          </CardHeader>
          <CardContent class="px-4 pb-4 space-y-2">

            <Select v-model="formData.origin_warehouse_id">
              <SelectTrigger class="h-10 text-sm bg-white border-gray-300 shadow-sm"><SelectValue placeholder="Seleccione Almacén Origen..." /></SelectTrigger>
              <SelectContent><SelectItem v-for="w in warehouses" :key="w.id" :value="w.id" class="text-sm">{{ w.name }}</SelectItem></SelectContent>
            </Select>
            <div v-if="mode === 'external' && formData.origin_warehouse_id" class="mt-2 text-xs text-gray-500 bg-gray-50 p-2 rounded border border-gray-100">
              <span class="font-semibold text-gray-700">Dirección:</span><br>
              {{ warehouses.find(w => w.id === formData.origin_warehouse_id)?.address || 'Sin dirección' }}
            </div>
          </CardContent>
        </Card>

        <Card v-if="mode === 'external'" class="shadow-sm border-blue-100 bg-white">
  <CardHeader class="!py-1.5 px-4 border-b border-gray-50 bg-blue-50/30">
    <CardTitle class="text-xs font-bold text-blue-700 uppercase tracking-wide flex items-center gap-2">
      <FileText class="w-3.5 h-3.5" /> Datos Guía Remisión
    </CardTitle>
  </CardHeader>

  <CardContent class="px-4 pb-4 !pt-2 space-y-3">

    <Select v-model="formData.cost_center_id">
      <SelectTrigger class="h-9 text-xs bg-white border-gray-300 shadow-sm"><SelectValue placeholder="Centro de Costo..." /></SelectTrigger>
      <SelectContent>
        <SelectItem v-for="cc in cost_centers" :key="cc.id" :value="cc.id" class="text-xs">
          {{ cc.code }}
        </SelectItem>
      </SelectContent>
    </Select>

    <div class="grid grid-cols-2 gap-2 bg-gray-100 p-1 rounded-md">
      <label class="cursor-pointer text-center py-1 rounded text-[10px] font-bold uppercase transition-colors"
        :class="formData.gre_type === 'remitente' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'">
        <input type="radio" v-model="formData.gre_type" value="remitente" class="hidden">
        Remitente (09)
      </label>
      <label class="cursor-pointer text-center py-1 rounded text-[10px] font-bold uppercase transition-colors"
        :class="formData.gre_type === 'transportista' ? 'bg-white text-purple-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'">
        <input type="radio" v-model="formData.gre_type" value="transportista" class="hidden">
        Transportista (31)
      </label>
    </div>

    <div class="text-[10px] text-center p-1 rounded border leading-tight"
         :class="formData.gre_type === 'remitente' ? 'bg-blue-50 text-blue-600 border-blue-100' : 'bg-purple-50 text-purple-600 border-purple-100'">
      <span v-if="formData.gre_type === 'remitente'">📉 Descuenta stock inventario</span>
      <span v-else>🚚 Solo traslado (No mueve stock)</span>
    </div>

    <div class="flex gap-2">
      <div class="w-1/3">
        <Label class="text-[9px] text-gray-400 font-bold mb-0.5 block uppercase">Serie</Label>
        <Input v-model="formData.serie" @change="fetchNextCorrelative" class="h-8 text-xs font-mono uppercase text-center font-bold border-gray-300 shadow-sm" maxlength="4"/>
      </div>
      <div class="flex-1 relative">
        <Label class="text-[9px] text-gray-400 font-bold mb-0.5 block uppercase">Correlativo</Label>
        <Input type="number" v-model="formData.numero" class="h-8 text-xs font-mono text-center font-bold text-blue-700 border-gray-300 shadow-sm"/>
        <Loader2 v-if="isFetchingCorrelative" class="w-3 h-3 absolute right-2 top-6 animate-spin text-gray-400" />
      </div>
    </div>

    <div>
      <Label class="text-[9px] text-gray-400 font-bold mb-0.5 block uppercase">Motivo Traslado</Label>
      <Select v-model="formData.motivo_traslado_codigo">
        <SelectTrigger class="h-8 text-xs bg-white border-gray-300 shadow-sm"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem v-for="m in transferReasons" :key="m.code" :value="m.code" class="text-xs">{{ m.label }}</SelectItem>
        </SelectContent>
      </Select>
    </div>

    <div v-if="formData.motivo_traslado_codigo === '13'" class="animate-in fade-in slide-in-from-top-1">
      <Input v-model="formData.motivo_manual" placeholder="Especifique el motivo..." class="h-8 text-xs border-orange-200 bg-orange-50 placeholder:text-orange-300 focus:border-orange-400"/>
    </div>
  </CardContent>
</Card>

        <Card v-if="mode === 'internal'" class="shadow-sm border-gray-200">
          <CardHeader class="py-2 px-4">
            <CardTitle class="text-xs font-bold text-gray-500 uppercase tracking-wide">Almacén Destino</CardTitle>
          </CardHeader>
          <CardContent class="px-4 pb-4">
            <Select v-model="formData.destination_warehouse_id">
              <SelectTrigger class="h-10 text-sm bg-white border-gray-300 shadow-sm"><SelectValue placeholder="Seleccione..." /></SelectTrigger>
              <SelectContent><SelectItem v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.name }}</SelectItem></SelectContent>
            </Select>
          </CardContent>
        </Card>
      </div>

      <div class="lg:col-span-8 space-y-4">

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">

          <Card v-if="mode === 'external'" class="shadow-sm border-gray-200">
            <CardHeader class="pb-2 pt-4 px-4 border-b border-gray-50">
              <CardTitle class="text-xs font-bold text-gray-500 uppercase tracking-wide">Datos del Destinatario</CardTitle>
            </CardHeader>
            <CardContent class="p-3 space-y-3">
              <div class="relative">
                <Input v-model="formData.client_search" @input="handleClientSearch(false)" @focus="handleClientSearch(true)" @blur="closeClientResults" placeholder="🔍 Buscar Cliente por RUC o Nombre..." class="h-9 text-sm border-gray-300 w-full shadow-sm"/>
                <div v-if="showClientResults" class="absolute z-50 w-full bg-white border shadow-lg mt-1 rounded-md max-h-48 overflow-y-auto">
                  <div v-for="c in clientResults" :key="c.ruc || c.id" @click="selectClient(c)" class="p-2.5 hover:bg-blue-50 cursor-pointer text-xs border-b last:border-0">
                    <span class="font-bold block text-gray-800">{{ c.name || c.razon_social }}</span>
                    <span class="text-gray-500 font-mono">{{ c.ruc || c.document_number }}</span>
                  </div>
                </div>
              </div>

              <div v-if="formData.client_name" class="bg-gray-50 p-2.5 rounded-lg border border-gray-100 space-y-2">
                <div class="flex items-start gap-2">
                  <div class="bg-blue-100 p-1 rounded text-blue-600 font-bold text-[10px]">CLIENTE</div>
                  <div>
                    <div class="text-xs font-bold text-gray-800 leading-tight">{{ formData.client_name }}</div>
                    <div class="text-[10px] text-gray-500 font-mono">{{ formData.client_ruc }}</div>
                  </div>
                </div>

                <div class="space-y-1">
                  <Label class="text-[9px] text-gray-400 font-bold uppercase">
                    Punto de Llegada <span class="text-red-500">*</span>
                  </Label>
                  <div class="flex gap-2">
                    <Select v-if="!showNewLocationForm" v-model="formData.location_id">
                      <SelectTrigger class="h-8 text-xs flex-1 bg-white border-gray-200"><SelectValue placeholder="Seleccione Sede..." /></SelectTrigger>
                      <SelectContent><SelectItem v-for="l in clientLocations" :key="l.id" :value="l.id" class="text-xs">{{ l.name }}</SelectItem></SelectContent>
                    </Select>
                    <Button size="icon" variant="outline" class="h-8 w-8 shrink-0 border-gray-200 hover:bg-white" @click="showNewLocationForm = !showNewLocationForm">
                      <Plus class="h-3.5 w-3.5 text-blue-600" :class="{'rotate-45': showNewLocationForm}"/>
                    </Button>
                  </div>

                  <div v-if="formData.location_name && !showNewLocationForm" class="text-[10px] text-gray-500 bg-white p-1.5 border rounded leading-tight">
                    {{ formData.punto_llegada_direccion }}
                  </div>
                </div>

                <div v-if="showNewLocationForm" class="bg-white p-2 rounded border border-blue-200 shadow-sm space-y-2 animate-in fade-in zoom-in-95">
                  <span class="text-[10px] font-bold text-blue-700 uppercase block">Nueva Sede</span>
                  <Input v-model="newLoc.name" placeholder="Nombre (Ej: ALMACEN LIMA)" class="h-7 text-xs" />
                  <div class="grid grid-cols-3 gap-1">
                    <Select @update:model-value="handleDeptChange"><SelectTrigger class="h-7 text-[10px]"><SelectValue placeholder="Dpto" /></SelectTrigger><SelectContent><SelectItem v-for="d in ubiDeptos" :key="d.code" :value="d.code" class="text-xs">{{ d.name }}</SelectItem></SelectContent></Select>
                    <Select @update:model-value="handleProvChange" :disabled="!newLoc.dept_code"><SelectTrigger class="h-7 text-[10px]"><SelectValue placeholder="Prov" /></SelectTrigger><SelectContent><SelectItem v-for="p in ubiProvs" :key="p.code" :value="p.code" class="text-xs">{{ p.name }}</SelectItem></SelectContent></Select>
                    <Select v-model="newLoc.dist_code" :disabled="!newLoc.prov_code"><SelectTrigger class="h-7 text-[10px]"><SelectValue placeholder="Dist" /></SelectTrigger><SelectContent><SelectItem v-for="d in ubiDists" :key="d.code" :value="d.code" class="text-xs">{{ d.name }}</SelectItem></SelectContent></Select>
                  </div>
                  <div class="flex justify-end gap-2">
                    <Button size="xs" variant="ghost" class="h-6 text-[10px]" @click="showNewLocationForm = false">Cancelar</Button>
                    <Button size="xs" class="h-6 text-[10px] bg-blue-600 text-white" @click="saveNewLocation">Guardar</Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card v-if="mode === 'external'" class="shadow-sm border-gray-200">
            <CardHeader class="pb-2 pt-4 px-4 border-b border-gray-50">
              <CardTitle class="text-xs font-bold text-gray-500 uppercase tracking-wide">Datos del Transporte</CardTitle>
            </CardHeader>
            <CardContent class="p-3 space-y-3">
              <div class="flex bg-gray-100 p-1 rounded-md">
                <label class="flex-1 text-center cursor-pointer py-1 text-[10px] font-bold uppercase rounded transition-colors"
                  :class="formData.transport_type === 'private' ? 'bg-white shadow-sm text-gray-800' : 'text-gray-500 hover:text-gray-700'">
                  <input type="radio" value="private" v-model="formData.transport_type" class="hidden"> Privado
                </label>
                <label class="flex-1 text-center cursor-pointer py-1 text-[10px] font-bold uppercase rounded transition-colors"
                  :class="formData.transport_type === 'public' ? 'bg-white shadow-sm text-gray-800' : 'text-gray-500 hover:text-gray-700'">
                  <input type="radio" value="public" v-model="formData.transport_type" class="hidden"> Público
                </label>
              </div>

              <div class="relative">
                <Input v-if="formData.transport_type === 'private'"  @input="handleDriverSearch(false)" @focus="handleDriverSearch(true)" @blur="closeDriverResults" placeholder="🔍 Buscar Chofer..." class="h-9 text-sm border-gray-300 shadow-sm"/>
                <Input v-else v-model="transportSearch" @input="handleTransportSearch(false)" @focus="handleTransportSearch(true)" @blur="closeTransportResults" placeholder="🔍 Buscar Empresa Transp..." class="h-9 text-sm border-gray-300 shadow-sm"/>

                <div v-if="showDriverResults" class="absolute z-50 w-full bg-white border shadow-lg mt-1 rounded-md max-h-40 overflow-y-auto">
                  <div v-for="d in driverResults" :key="d.id" @click="selectDriver(d)" class="p-2 hover:bg-gray-50 cursor-pointer text-xs border-b">
                    <span class="font-bold">{{ d.first_name }} {{ d.last_name }}</span> <span class="text-gray-400">({{ d.document_number }})</span>
                  </div>
                </div>
                <div v-if="showTransportResults" class="absolute z-50 w-full bg-white border shadow-lg mt-1 rounded-md max-h-40 overflow-y-auto">
                  <div v-for="t in transportResults" :key="t.id" @click="selectTransport(t)" class="p-2 hover:bg-gray-50 cursor-pointer text-xs border-b">
                     <span class="font-bold">{{ t.name }}</span> <span class="text-gray-400">({{ t.ruc || t.document_number }})</span>
                  </div>
                </div>
              </div>

              <div v-if="formData.transport_type === 'private'" class="grid grid-cols-2 gap-2 animate-in fade-in">
                <div>
                   <Label class="text-[9px] text-gray-400 font-bold mb-0.5 block uppercase">Nombres</Label>
                   <Input v-model="formData.driver_name" class="h-8 text-xs font-mono uppercase border-gray-300"/>
                </div>

                <div>
                   <Label class="text-[9px] text-gray-400 font-bold mb-0.5 block uppercase">Apellidos</Label>
                   <Input v-model="formData.driver_lastname" class="h-8 text-xs font-mono uppercase border-gray-300"/>
                </div>

                <div>
                   <Label class="text-[9px] text-gray-400 font-bold mb-0.5 block uppercase">Placa</Label>
                   <Input v-model="formData.vehicle_plate" class="h-8 text-xs font-mono uppercase border-gray-300"/>
                </div>

                <div>
                   <Label class="text-[9px] text-gray-400 font-bold mb-0.5 block uppercase">Marca</Label>
                   <Input v-model="formData.vehicle_brand" class="h-8 text-xs font-mono uppercase border-gray-300"/>
                </div>

                <div class="col-span-2">
                   <Label class="text-[9px] text-gray-400 font-bold mb-0.5 block uppercase">Licencia</Label>
                   <Input v-model="formData.driver_license" class="h-8 text-xs font-mono uppercase border-gray-300 bg-gray-50"/>
                </div>
            </div>
            </CardContent>
          </Card>
        </div>

        <Card class="shadow-sm border-gray-200">
          <CardContent class="p-0">
            <div class="p-3 border-b bg-gray-50/50 flex justify-between items-center">
              <h3 class="text-xs font-bold text-gray-600 uppercase tracking-wide">Detalle de Productos</h3>

              <div class="relative w-64">
                <Search class="absolute left-2.5 top-2 h-3.5 w-3.5 text-gray-400" />
                <Input
                  v-model="productSearch"
                  :disabled="!formData.origin_warehouse_id"
                  :placeholder="!formData.origin_warehouse_id ? 'Seleccione almacén origen' : 'Escriba para buscar...'"
                  class="h-8 pl-8 text-xs w-full border-gray-200 focus:border-blue-300 focus:ring-1 focus:ring-blue-100 disabled:bg-gray-100"
                />

                <div v-if="filteredProducts.length > 0" class="absolute z-30 left-0 right-0 top-9 bg-white border shadow-lg rounded-md max-h-56 overflow-y-auto">
                  <div v-for="p in filteredProducts" :key="p.id" @click="addItem(p)" class="p-2.5 hover:bg-blue-50 cursor-pointer text-xs border-b flex justify-between items-center">
                    <div class="flex-1 mr-2 min-w-0">
                      <div class="font-medium text-gray-800 whitespace-normal break-words leading-tight">
                        {{ p.name }}
                      </div>
                      <div class="text-[10px] font-bold mt-0.5" :class="p.stock > 0 ? 'text-blue-600' : 'text-red-500'">
                          Stock Disp: {{ p.stock }}
                      </div>
                    </div>
                    <span class="font-mono text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded shrink-0">
                      {{ p.sku }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <Table>
              <TableHeader>
                <TableRow class="bg-gray-50 hover:bg-gray-50 border-b border-gray-100">
                  <TableHead class="h-8 text-[10px] font-bold uppercase w-24 pl-4 text-gray-500">SKU</TableHead>
                  <TableHead class="h-8 text-[10px] font-bold uppercase text-gray-500">Descripción</TableHead>
                  <TableHead class="h-8 text-[10px] font-bold uppercase w-20 text-gray-500">Unidad</TableHead>
                  <TableHead class="h-8 text-[10px] font-bold uppercase w-24 text-center text-gray-500">Cantidad</TableHead>
                  <TableHead class="h-8 w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="(item, idx) in lineItems" :key="idx" class="border-b last:border-0 hover:bg-gray-50/50 transition-colors">
                  <TableCell class="py-2 text-xs font-mono pl-4 text-gray-600">{{ item.sku }}</TableCell>
                  <TableCell class="py-2 text-xs font-medium text-gray-800 whitespace-normal">{{ item.name }}</TableCell>
                  <TableCell class="py-2 text-[10px] text-gray-500 uppercase">{{ item.unit_sunat || 'NIU' }}</TableCell>
                  <TableCell class="py-1">
                    <div class="flex flex-col items-center">
                        <Input
                            type="number"
                            v-model="item.quantity"
                            class="h-7 text-xs w-full text-center border-gray-200 focus:border-blue-300 font-bold"
                            min="0.1"
                            @input="validateStock(item)"
                        />
                        <span class="text-[9px]" :class="item.quantity > item.max_stock ? 'text-red-500 font-bold' : 'text-gray-400'">
                            Max: {{ item.max_stock }}
                        </span>
                    </div>
                  </TableCell>
                  <TableCell class="py-1 text-center">
                    <Button variant="ghost" size="icon" class="h-6 w-6 text-gray-400 hover:text-red-500 hover:bg-red-50" @click="lineItems.splice(idx,1)">
                      <Trash2 class="w-3.5 h-3.5"/>
                    </Button>
                  </TableCell>
                </TableRow>
                <TableRow v-if="lineItems.length === 0">
                  <TableCell colspan="5" class="h-24 text-center text-xs text-gray-400 italic">
                    <span v-if="!formData.origin_warehouse_id">Seleccione un almacén de origen para cargar productos.</span>
                    <span v-else>No hay productos agregados. Utilice el buscador superior.</span>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <div class="flex justify-end pt-2 pb-8">
          <Button size="default" @click="handleSubmit" :disabled="isSubmitting || lineItems.length === 0"
            class="h-10 text-sm px-8 shadow-md transition-all"
            :class="mode === 'internal' ? 'bg-gray-900 hover:bg-black text-white' : 'bg-blue-700 hover:bg-blue-800 text-white'">
            <Loader2 v-if="isSubmitting" class="mr-2 h-4 w-4 animate-spin"/>
            {{ mode === 'internal' ? 'Procesar Transferencia' : 'Emitir Guía de Remisión' }}
          </Button>
        </div>

      </div>
    </div>
  </div>
</template>