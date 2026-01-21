<script setup>
import { ref, onMounted, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth0 } from '@auth0/auth0-vue'

// UI Components
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Loader2, Plus, Trash2, Check, ChevronsUpDown, Save, ArrowLeft, Search } from 'lucide-vue-next'

const router = useRouter()
const { getAccessTokenSilently } = useAuth0()
const API_URL = import.meta.env.VITE_API_URL

// --- Estado ---
const isLoading = ref(false)
const isSubmitting = ref(false)
const warehouses = ref([])
const productCatalog = ref([])
const openProductSearch = ref(false)

// --- Formulario Principal ---
const formData = reactive({
  warehouse_id: null,
  invoice_number: '',
  items: [],
  provider_id: null,
  provider_search: '',
})

// --- Estado del Buscador de Proveedores ---
const isSearchingProvider = ref(false)
const providerResults = ref([])
const showProviderResults = ref(false)
let searchTimeout = null

// --- Estado del Item en Edición ---
const tempItem = reactive({
  product_id: null,
  product_data: null,
  quantity: 1,
  unit_price: 0,
  location: ''
})

// --- Carga Inicial ---
onMounted(async () => {
  isLoading.value = true
  try {
    const token = await getAccessTokenSilently()
    const [whRes, prodRes] = await Promise.all([
      fetch(`${API_URL}/api/inventory/warehouses`, { headers: { Authorization: `Bearer ${token}` } }),
      fetch(`${API_URL}/api/products`, { headers: { Authorization: `Bearer ${token}` } })
    ])

    if (whRes.ok) warehouses.value = await whRes.json()
    if (prodRes.ok) productCatalog.value = await prodRes.json()

  } catch (e) {
    console.error("Error cargando datos:", e)
  } finally {
    isLoading.value = false
  }
})

// --- LÓGICA DE BUSCADOR DE PROVEEDOR ---
async function handleProviderSearch() {
  const q = formData.provider_search.trim()
  if (!q) return

  isSearchingProvider.value = true
  clearTimeout(searchTimeout)

  searchTimeout = setTimeout(async () => {
    try {
      const token = await getAccessTokenSilently()

      if (/^\d{11}$/.test(q)) {
         const localRes = await fetch(`${API_URL}/api/purchases/providers?q=${q}`, {
            headers: { 'Authorization': `Bearer ${token}` }
         })
         const localData = await localRes.json()

         if (localData.length > 0) {
            providerResults.value = localData
            showProviderResults.value = true
         } else {
            const sunatRes = await fetch(`${API_URL}/api/purchases/lookup-provider/${q}`, {
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
         const res = await fetch(`${API_URL}/api/purchases/providers?q=${q}`, {
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
  formData.provider_search = p.name || p.razon_social
  showProviderResults.value = false
}

// --- Métodos de Gestión de Items ---
function selectProduct(product) {
  tempItem.product_id = product.id
  tempItem.product_data = product
  tempItem.unit_price = product.standard_price || 0
  tempItem.location = product.location || ''
  openProductSearch.value = false
}

function addItem() {
  if (!tempItem.product_id) return alert("Selecciona un producto")
  if (tempItem.quantity <= 0) return alert("La cantidad debe ser mayor a 0")

  const existing = formData.items.find(i => i.product_id === tempItem.product_id)

  if (existing) {
    existing.quantity += parseFloat(tempItem.quantity)
    existing.unit_price = parseFloat(tempItem.unit_price)
  } else {
    formData.items.push({
      product_id: tempItem.product_id,
      product_name: tempItem.product_data.name,
      product_sku: tempItem.product_data.sku,
      quantity: parseFloat(tempItem.quantity),
      unit_price: parseFloat(tempItem.unit_price),
      location: tempItem.location,
    })
  }

  tempItem.product_id = null
  tempItem.product_data = null
  tempItem.quantity = 1
  tempItem.unit_price = 0
  tempItem.location = ''
}

function removeItem(index) {
  formData.items.splice(index, 1)
}

// --- Totales ---
const totalGeneral = computed(() => {
  return formData.items.reduce((acc, item) => acc + (item.quantity * item.unit_price), 0)
})

// --- Enviar al Backend ---
async function handleSubmit() {
  if (!formData.warehouse_id) return alert("Selecciona un almacén")
  if (!formData.invoice_number) return alert("Ingresa el número de factura o guía")
  if (formData.items.length === 0) return alert("Agrega al menos un producto")

  isSubmitting.value = true
  try {
    const token = await getAccessTokenSilently()

    const payload = {
      warehouse_id: formData.warehouse_id,
      invoice_number: formData.invoice_number,
      provider_id: formData.provider_id,
      items: formData.items.map(i => ({
        product_id: i.product_id,
        quantity: i.quantity,
        unit_price: i.unit_price,
        location: i.location
      }))
    }

    const res = await fetch(`${API_URL}/api/inventory/direct-receive`, {
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

    alert("Ingreso registrado correctamente")
    router.push('/inventory')

  } catch (e) {
    alert(e.message)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-[96%] mx-auto p-4 space-y-6">

    <div class="flex items-center justify-between border-b pb-4">
      <div class="flex items-center gap-4">
        <Button variant="outline" size="icon" @click="router.back()">
           <ArrowLeft class="w-4 h-4" />
        </Button>
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-gray-900">Registrar Ingreso</h1>
          <p class="text-sm text-gray-500">Ingreso directo de mercadería a inventario (con Factura/Guía).</p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-8">

      <div class="lg:col-span-1 space-y-6">
        <Card class="border-blue-100 shadow-sm">
          <CardHeader class="bg-blue-50/50 pb-3">
            <CardTitle class="text-sm font-bold uppercase text-blue-700">1. Datos del Documento</CardTitle>
          </CardHeader>
          <CardContent class="space-y-5 pt-5">

            <div class="space-y-2 relative">
              <Label class="font-semibold text-gray-700">Proveedor</Label>
              <div class="relative">
                <Search class="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
                <Input
                  v-model="formData.provider_search"
                  @input="handleProviderSearch"
                  placeholder="RUC o Nombre..."
                  class="pl-9 bg-white"
                />
                <Loader2 v-if="isSearchingProvider" class="absolute right-3 top-2.5 h-4 w-4 animate-spin text-gray-400" />
              </div>

              <div v-if="showProviderResults" class="absolute z-10 w-full bg-white border rounded-md shadow-xl mt-1 max-h-60 overflow-y-auto">
                 <div v-for="p in providerResults" :key="p.ruc" @click="selectProvider(p)" class="p-3 hover:bg-blue-50 cursor-pointer border-b last:border-0">
                    <div class="font-bold text-sm text-gray-800">{{ p.name || p.razon_social }}</div>
                    <div class="text-xs text-gray-500">RUC: {{ p.ruc || p.numero_documento }}</div>
                 </div>
              </div>
            </div>

            <div class="space-y-2">
              <Label class="font-semibold text-gray-700">Almacén de Destino</Label>
              <Select v-model="formData.warehouse_id">
                <SelectTrigger class="bg-white">
                  <SelectValue placeholder="Seleccionar..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem v-for="wh in warehouses" :key="wh.id" :value="wh.id">
                    {{ wh.name }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div class="space-y-2">
              <Label class="font-semibold text-gray-700">Nro. Factura / Guía</Label>
              <Input v-model="formData.invoice_number" placeholder="Ej: F001-00004520" class="bg-white font-mono" />
            </div>

            <div class="pt-4 border-t mt-4 bg-gray-50 -mx-6 px-6 pb-2">
              <div class="flex justify-between items-center text-sm text-gray-500 mb-1">Total Estimado</div>
              <div class="text-2xl font-bold text-gray-900">S/. {{ totalGeneral.toFixed(2) }}</div>
            </div>

            <Button class="w-full bg-gray-900 hover:bg-black text-white" :disabled="isSubmitting" @click="handleSubmit">
              <Loader2 v-if="isSubmitting" class="w-4 h-4 mr-2 animate-spin" />
              <Save class="w-4 h-4 mr-2" />
              Procesar Ingreso
            </Button>

          </CardContent>
        </Card>
      </div>

      <div class="lg:col-span-3 space-y-6">
        <Card class="shadow-sm border-gray-200">
          <CardHeader class="flex flex-row justify-between items-center py-4 border-b bg-gray-50/30">
            <CardTitle class="text-sm font-bold uppercase text-gray-600">2. Productos a Ingresar</CardTitle>
          </CardHeader>

          <CardContent class="p-0">

            <div class="p-4 grid grid-cols-1 md:grid-cols-12 gap-4 items-end bg-white border-b">

              <div class="md:col-span-5 space-y-2">
                <Label class="text-xs font-bold text-gray-500 uppercase">Buscar Producto</Label>
                <Popover v-model:open="openProductSearch">
                  <PopoverTrigger as-child>
                    <Button
                      variant="outline"
                      role="combobox"
                      :aria-expanded="openProductSearch"
                      class="w-full justify-between h-auto min-h-[40px] whitespace-normal text-left py-2 items-start"
                    >
                      <span class="line-clamp-2">
                        {{ tempItem.product_data ? `${tempItem.product_data.sku} - ${tempItem.product_data.name}` : "Buscar por nombre o SKU..." }}
                      </span>
                      <ChevronsUpDown class="ml-2 h-4 w-4 shrink-0 opacity-50 mt-1" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent class="p-0 w-[450px]" align="start">
                    <Command>
                      <CommandInput placeholder="Escribe para buscar..." />
                      <CommandEmpty>No encontrado.</CommandEmpty>
                      <CommandList>
                          <CommandGroup>
                          <CommandItem
                              v-for="product in productCatalog"
                              :key="product.id"
                              :value="`${product.name} ${product.sku}`"
                              @select="() => selectProduct(product)"
                              class="cursor-pointer py-2"
                          >
                              <Check :class="['mr-2 h-4 w-4 mt-1', tempItem.product_id === product.id ? 'opacity-100' : 'opacity-0']" />
                              <div class="flex flex-col">
                                  <span class="font-medium">{{ product.name }}</span>
                                  <span class="text-xs text-gray-500 font-mono">SKU: {{ product.sku }}</span>
                              </div>
                          </CommandItem>
                          </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>

              <div class="md:col-span-2 space-y-2">
                <Label class="text-xs font-bold text-gray-500 uppercase">Ubicación</Label>
                <Input v-model="tempItem.location" placeholder="Ej: A1" />
              </div>

              <div class="md:col-span-2 space-y-2">
                <Label class="text-xs font-bold text-gray-500 uppercase">Cantidad</Label>
                <Input type="number" v-model="tempItem.quantity" min="1" class="text-right" />
              </div>

              <div class="md:col-span-2 space-y-2">
                <Label class="text-xs font-bold text-gray-500 uppercase">Costo Unit.</Label>
                <Input type="number" v-model="tempItem.unit_price" min="0" step="0.01" class="text-right" />
              </div>

              <div class="md:col-span-1">
                <Button @click="addItem" :disabled="!tempItem.product_id" class="w-full bg-blue-600 hover:bg-blue-700 text-white">
                  <Plus class="w-5 h-5" />
                </Button>
              </div>
            </div>

            <Table>
              <TableHeader>
                <TableRow class="bg-gray-50 hover:bg-gray-50">
                  <TableHead class="w-[40%]">Producto</TableHead>
                  <TableHead class="text-center w-[15%]">Ubicación</TableHead>
                  <TableHead class="text-right w-[10%]">Cant.</TableHead>
                  <TableHead class="text-right w-[15%]">Costo</TableHead>
                  <TableHead class="text-right w-[15%]">Total</TableHead>
                  <TableHead class="w-[5%]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="(item, idx) in formData.items" :key="idx" class="group">

                  <TableCell class="py-2 align-top">
                    <div class="font-bold text-gray-800 whitespace-normal break-words leading-tight min-w-[200px]">
                      {{ item.product_name }}
                    </div>
                    <div class="text-xs text-gray-500 font-mono mt-1">
                      {{ item.product_sku }}
                    </div>
                  </TableCell>

                  <TableCell class="text-center p-2 align-top">
                      <Input v-model="item.location" class="h-8 w-24 mx-auto text-center border-transparent group-hover:border-gray-300 focus:border-blue-500 bg-transparent group-hover:bg-white transition-all" />
                  </TableCell>
                  <TableCell class="text-right p-2 align-top">
                      <Input type="number" v-model="item.quantity" class="h-8 w-20 ml-auto text-right border-transparent group-hover:border-gray-300 focus:border-blue-500 bg-transparent group-hover:bg-white transition-all" />
                  </TableCell>
                  <TableCell class="text-right p-2 align-top">
                      <Input type="number" v-model="item.unit_price" class="h-8 w-24 ml-auto text-right border-transparent group-hover:border-gray-300 focus:border-blue-500 bg-transparent group-hover:bg-white transition-all" step="0.01"/>
                  </TableCell>
                  <TableCell class="text-right font-medium text-gray-900 p-2 align-top pt-3">
                    S/. {{ (item.quantity * item.unit_price).toFixed(2) }}
                  </TableCell>
                  <TableCell class="p-2 align-top text-center pt-2">
                    <Button variant="ghost" size="icon" class="text-gray-400 hover:text-red-600 hover:bg-red-50" @click="removeItem(idx)">
                      <Trash2 class="w-4 h-4" />
                    </Button>
                  </TableCell>
                </TableRow>

                </TableBody>
            </Table>

          </CardContent>
        </Card>
      </div>

    </div>
  </div>
</template>