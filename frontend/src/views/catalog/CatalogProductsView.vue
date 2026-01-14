<script setup>
import { ref, onMounted, computed } from 'vue' // <-- AÑADE computed
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button/index.js'
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Label } from '@/components/ui/label/index.js'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Loader2, Pencil, Upload, Trash2, Download } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()
const products = ref([])
const searchQuery = ref('')

const filteredProducts = computed(() => {
  if (!searchQuery.value) {
    return products.value
  }
  const lowerCaseQuery = searchQuery.value.toLowerCase()
  return products.value.filter(product => {
    return (
      product.name.toLowerCase().includes(lowerCaseQuery) ||
      product.sku.toLowerCase().includes(lowerCaseQuery)
    )
  })
})

const categories = ref([])
const isLoading = ref(true)
const error = ref(null)

const isDialogOpen = ref(false)
const modalMode = ref('create')
const isSubmitting = ref(false)
// MODIFICADO: Añade 'location' al formulario
const formData = ref({ id: null, sku: '', name: '', description: '', unit_measure_id: null, standard_price: 0.00, category_id: null, location: [] })
const fileInput = ref(null)
const isImporting = ref(false)
const isDownloading = ref(false)
// -------------------------------------------------------------------
const units = ref([])

const fetchUnits = async () => {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch('/api/units/', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      // 2. Asegúrate de llenar la variable correcta
      units.value = await res.json()
    }
  } catch (error) {
    console.error("Error cargando unidades:", error)
  }
}

// --------------------------------------------------------------------


// --- NUEVO: Computed property para el input de ubicaciones ---
// Esto permite un enlace de doble vía entre el array de formData y el string del input
const locationInput = computed({
  get: () => formData.value.location.join(', '),
  set: (val) => {
    formData.value.location = val.split(',').map(s => s.trim())
  }
})


// --- Cargar AMBOS, productos y categorías ---
async function fetchData() {
  isLoading.value = true
  error.value = null
  try {
    const token = await getAccessTokenSilently()
    const prodRes = await fetch(`${import.meta.env.VITE_API_URL}/api/products`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!prodRes.ok) throw new Error('No se pudieron cargar los productos.')
    products.value = await prodRes.json()

    const catRes = await fetch(`${import.meta.env.VITE_API_URL}/api/categories`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!catRes.ok) throw new Error('No se pudieron cargar las categorías.')
    categories.value = await catRes.json()

  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}
onMounted(() => {
  fetchData()   // Tu función original
  fetchUnits()  // La nueva función de unidades
})

// --- Lógica de Modales ---
function openCreateModal() {
  modalMode.value = 'create'
  // MODIFICADO: Resetea el formulario incluyendo 'location'
  formData.value = { id: null, sku: '', name: '', description: '', unit_measure_id: null, category_id: null, location: [] }
  isDialogOpen.value = true
}

function openEditModal(product) {
  modalMode.value = 'edit'
  const productData = products.value.find(p => p.id === product.id)
  // El backend ahora devuelve 'location' como un array, así que la copia directa funciona
  formData.value = { ...productData }
  isDialogOpen.value = true
}

async function handleFormSubmit() {
  isSubmitting.value = true
  let url = `${import.meta.env.VITE_API_URL}/api/products`
  let method = 'POST'

  if (modalMode.value === 'edit') {
    url = `${import.meta.env.VITE_API_URL}/api/products/${formData.value.id}`
    method = 'PUT'
  }

  // MODIFICADO: Añade 'location' al payload
  const payload = {
    sku: formData.value.sku,
    name: formData.value.name,
    description: formData.value.description,
    unit_measure_id: formData.value.unit_measure_id,
    standard_price: formData.value.standard_price,
    category_id: formData.value.category_id,
    // El backend espera una lista de strings
    location: formData.value.location.filter(loc => loc) // Filtra strings vacíos
  }

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(url, {
      method: method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })
    if (!response.ok) throw new Error('Error al guardar.')

    isDialogOpen.value = false
    await fetchData()
  } catch (e) {
    alert(e.message)
  } finally {
    isSubmitting.value = false
  }
}

// --- Lógica de Eliminación ---
async function confirmDeleteProduct(productId) {
  if (window.confirm('¿Estás seguro de que quieres eliminar este producto? Esta acción no se puede deshacer.')) {
    await deleteProduct(productId)
  }
}

async function deleteProduct(productId) {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/products/${productId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('Error al eliminar el producto.')

    alert('Producto eliminado correctamente.')
    await fetchData()
  } catch (e) {
    alert(e.message)
  }
}

// --- Lógica de Importación/Exportación ---
function triggerImport() {
  fileInput.value.click()
}

async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return
  isImporting.value = true
  const importFormData = new FormData()
  importFormData.append('file', file)
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/products/import`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: importFormData
    })
    const result = await response.json()
    if (!response.ok) throw new Error(result.error || 'Error en la importación')
    alert(`Importación Exitosa:\nCreados: ${result.created}\nActualizados: ${result.updated}`)
    await fetchData()
  } catch (e) {
    alert(e.message)
  } finally {
    isImporting.value = false
    event.target.value = ''
  }
}

async function downloadExcel() {
  isDownloading.value = true
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/products/export`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('Error al generar el archivo.')
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'productos.xlsx'
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    alert(e.message)
  } finally {
    isDownloading.value = false
  }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">Gestión de Productos</h1>
        <div class="flex items-center gap-2">
        <Input
            class="w-[400px]"
            placeholder="Buscar por SKU o nombre..."
            :model-value="searchQuery"
            @update:model-value="searchQuery = $event"
        />
      </div>
      <div class="flex gap-2">
        <input type="file" ref="fileInput" class="hidden" accept=".xlsx, .xls" @change="handleFileUpload" />
        <Button variant="outline" @click="triggerImport" :disabled="isImporting">
          <Loader2 v-if="isImporting" class="h-4 w-4 animate-spin mr-2" />
          <Upload v-else class="h-4 w-4 mr-2" />
          Importar Excel
        </Button>
        <Button variant="outline" @click="downloadExcel" :disabled="isDownloading">
          <Loader2 v-if="isDownloading" class="h-4 w-4 animate-spin mr-2" />
          <Download v-else class="h-4 w-4 mr-2" />
          Descargar Excel
        </Button>
        <Button @click="openCreateModal">Crear Producto</Button>
      </div>
    </div>

    <div class="bg-blue-50 p-3 rounded-md text-sm text-blue-800 mb-4">
      <strong>Para importar productos:</strong> El archivo Excel debe tener las columnas obligatorias: "SKU", "Nombre", "Categoria". Las columnas "Descripcion", "UM" y "Precio" son opcionales.
    </div>

    <div v-if="isLoading">Cargando...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>SKU</TableHead>
            <TableHead>Nombre</TableHead>
            <TableHead>Categoría</TableHead>
            <TableHead>Ubicaciones</TableHead> <!-- NUEVA COLUMNA -->
            <TableHead>UM</TableHead>
            <TableHead class="text-right">Precio Ref.</TableHead>
            <TableHead>Acciones</TableHead>
          </TableRow>
        </TableHeader>
       <TableBody>
          <TableRow v-for="prod in filteredProducts" :key="prod.id">
            <TableCell class="font-medium">{{ prod.sku }}</TableCell>

            <TableCell class="whitespace-normal min-w-[250px] max-w-[400px]">
              {{ prod.name }}
            </TableCell>
            <TableCell>{{ prod.category_name }}</TableCell>
            <TableCell>{{ prod.location.join(', ') }}</TableCell>
            <TableCell>{{ prod.unit_of_measure }}</TableCell>
            <TableCell class="text-right">S/ {{ parseFloat(prod.standard_price).toFixed(2) }}</TableCell>
            <TableCell>
              <div class="flex gap-2">
                <Button variant="outline" size="icon" @click="openEditModal(prod)">
                  <Pencil class="h-4 w-4" />
                </Button>
                <Button variant="destructive" size="icon" @click="confirmDeleteProduct(prod.id)">
                  <Trash2 class="h-4 w-4" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>

    <Dialog :open="isDialogOpen" @update:open="isDialogOpen = $event">
      <DialogContent class="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{{ modalMode === 'create' ? 'Crear' : 'Editar' }} Producto</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="sku" class="text-right">SKU</Label>
            <Input id="sku" v-model="formData.sku" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="name" class="text-right">Nombre</Label>
            <Input id="name" v-model="formData.name" class="col-span-3" />
          </div>
          <!-- NUEVO CAMPO DE UBICACIONES -->
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="location" class="text-right">Ubicaciones</Label>
            <Input id="location" v-model="locationInput" class="col-span-3" placeholder="Ej: Estante A, Pasillo 2" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="um" class="text-right">Unidad Medida</Label>

            <select
              id="um"
              v-model="formData.unit_measure_id"
              class="col-span-3 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option :value="null">Seleccione...</option>

              <option v-for="unit in units" :key="unit.id" :value="unit.id">
                {{ unit.sunat_code }} - {{ unit.description }}
              </option>
            </select>
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="category" class="text-right">Categoría</Label>
            <Select v-model="formData.category_id">
              <SelectTrigger class="col-span-3">
                <SelectValue placeholder="Selecciona una categoría..." />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.name }}</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="price" class="text-right">Precio Ref. (S/)</Label>
            <Input id="price" type="number" step="0.01" v-model="formData.standard_price" class="col-span-3" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="secondary" @click="isDialogOpen = false">Cancelar</Button>
          <Button @click="handleFormSubmit">Guardar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
