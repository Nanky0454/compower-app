<script setup>
import { ref, onMounted, computed, reactive } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Pencil, Trash2, Plus, Search, Upload, Loader2, FileSpreadsheet } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()

// --- ESTADOS ---
const units = ref([])
const searchQuery = ref('')
const isLoading = ref(false)
const isModalOpen = ref(false)
const isEditing = ref(false)
const fileInput = ref(null)

const form = reactive({
  id: null,
  sunat_code: '',
  description: '',
  symbol: ''
})

// --- COMPUTED ---
// Filtramos localmente porque la lista de unidades no suele ser muy grande (50-100 registros)
const filteredUnits = computed(() => {
  if (!searchQuery.value) return units.value
  const q = searchQuery.value.toLowerCase()
  return units.value.filter(u =>
    u.sunat_code.toLowerCase().includes(q) ||
    u.description.toLowerCase().includes(q) ||
    u.symbol.toLowerCase().includes(q)
  )
})

// --- API Calls ---

const fetchUnits = async () => {
  isLoading.value = true
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch('/api/units/', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      units.value = await res.json()
    }
  } catch (error) {
    console.error("Error cargando unidades:", error)
  } finally {
    isLoading.value = false
  }
}

const saveUnit = async () => {
  // Validación básica
  if (!form.sunat_code || !form.description) {
    alert("El Código SUNAT y la Descripción son obligatorios")
    return
  }

  try {
    const token = await getAccessTokenSilently()
    const method = isEditing.value ? 'PUT' : 'POST'
    const url = isEditing.value ? `/api/units/${form.id}` : '/api/units/'

    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(form)
    })

    const data = await res.json()

    if (!res.ok) {
      throw new Error(data.error || 'Error al guardar la unidad')
    }

    await fetchUnits()
    closeModal()
  } catch (error) {
    alert(error.message)
  }
}

const deleteUnit = async (id) => {
  if (!confirm('¿Estás seguro de eliminar esta unidad de medida? Esto podría fallar si hay productos usándola.')) return

  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`/api/units/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.error || 'Error al eliminar')
    }

    await fetchUnits()
  } catch (error) {
    alert(error.message)
  }
}

// --- IMPORTACIÓN MASIVA ---

const triggerFileUpload = () => {
  fileInput.value.click()
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  try {
    isLoading.value = true
    const token = await getAccessTokenSilently()
    const res = await fetch('/api/units/import', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData
    })

    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error en la importación')

    alert(`Importación completada.\nCreados: ${data.created}\nActualizados: ${data.updated}\nErrores: ${data.errors.length}`)
    await fetchUnits()
  } catch (error) {
    alert(error.message)
  } finally {
    isLoading.value = false
    event.target.value = '' // Reset input
  }
}

// --- UI Helpers ---

const openCreateModal = () => {
  isEditing.value = false
  form.id = null
  form.sunat_code = ''
  form.description = ''
  form.symbol = ''
  isModalOpen.value = true
}

const openEditModal = (item) => {
  isEditing.value = true
  form.id = item.id
  form.sunat_code = item.sunat_code
  form.description = item.description
  form.symbol = item.symbol
  isModalOpen.value = true
}

const closeModal = () => {
  isModalOpen.value = false
}

// Helper para convertir a mayúsculas mientras escribe
const handleCodeInput = (e) => {
  form.sunat_code = e.target.value.toUpperCase()
}

onMounted(() => {
  fetchUnits()
})
</script>

<template>
  <div class="space-y-6 p-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <h2 class="text-3xl font-bold tracking-tight text-gray-900">Unidades de Medida</h2>
        <p class="text-muted-foreground text-sm mt-1">
          Catálogo estandarizado SUNAT (NIU, KGM, etc.) para productos y servicios.
        </p>
      </div>
      <div class="flex space-x-2">
        <input type="file" ref="fileInput" class="hidden" accept=".xlsx, .xls, .csv" @change="handleFileUpload" />
        <Button variant="outline" @click="triggerFileUpload" :disabled="isLoading">
          <FileSpreadsheet class="mr-2 h-4 w-4 text-green-600" />
          {{ isLoading ? 'Procesando...' : 'Importar Excel' }}
        </Button>
        <Button @click="openCreateModal">
          <Plus class="mr-2 h-4 w-4" /> Nueva Unidad
        </Button>
      </div>
    </div>

    <!-- Buscador -->
    <div class="flex items-center space-x-2 bg-white p-1 rounded-md border w-full md:w-1/3">
      <Search class="h-4 w-4 text-gray-400 ml-2" />
      <Input
        v-model="searchQuery"
        placeholder="Buscar por código, nombre o símbolo..."
        class="border-0 focus-visible:ring-0"
      />
    </div>

    <!-- Tabla -->
    <div class="border rounded-md bg-white shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[120px]">Código SUNAT</TableHead>
            <TableHead>Descripción</TableHead>
            <TableHead class="w-[120px]">Símbolo</TableHead>
            <TableHead class="text-right">Acciones</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="isLoading && units.length === 0">
            <TableCell colspan="4" class="h-24 text-center">
              <Loader2 class="h-6 w-6 animate-spin mx-auto text-blue-600"/>
            </TableCell>
          </TableRow>

          <TableRow v-else v-for="item in filteredUnits" :key="item.id">
            <TableCell class="font-bold font-mono text-blue-700 bg-blue-50/50">
              {{ item.sunat_code }}
            </TableCell>
            <TableCell>{{ item.description }}</TableCell>
            <TableCell>
                <span class="px-2 py-1 rounded bg-gray-100 text-xs font-semibold text-gray-700">
                    {{ item.symbol }}
                </span>
            </TableCell>
            <TableCell class="text-right">
              <div class="flex justify-end gap-2">
                <Button variant="ghost" size="icon" @click="openEditModal(item)">
                  <Pencil class="h-4 w-4 text-gray-500 hover:text-blue-600" />
                </Button>
                <Button variant="ghost" size="icon" @click="deleteUnit(item.id)">
                  <Trash2 class="h-4 w-4 text-gray-500 hover:text-red-600" />
                </Button>
              </div>
            </TableCell>
          </TableRow>

          <TableRow v-if="filteredUnits.length === 0 && !isLoading">
            <TableCell colspan="4" class="text-center h-24 text-muted-foreground">
              No se encontraron resultados.
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <!-- Modal (Dialog) -->
    <Dialog :open="isModalOpen" @update:open="isModalOpen = $event">
      <DialogContent class="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{{ isEditing ? 'Editar Unidad' : 'Crear Unidad' }}</DialogTitle>
          <DialogDescription>
            Asegúrate de usar el código oficial de SUNAT para evitar problemas en facturación.
          </DialogDescription>
        </DialogHeader>

        <div class="grid gap-4 py-4">
          <!-- Código SUNAT -->
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="code" class="text-right font-semibold">Cód. SUNAT</Label>
            <div class="col-span-3">
              <Input
                id="code"
                v-model="form.sunat_code"
                @input="handleCodeInput"
                placeholder="Ej: NIU, KGM, ZZ"
                maxlength="5"
                class="font-mono uppercase"
                :disabled="isEditing"
              />
              <p v-if="isEditing" class="text-[10px] text-gray-500 mt-1">El código SUNAT no debería cambiar.</p>
            </div>
          </div>

          <!-- Descripción -->
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="desc" class="text-right font-semibold">Descripción</Label>
            <Input
              id="desc"
              v-model="form.description"
              class="col-span-3"
              placeholder="Ej: Unidad, Kilogramos"
            />
          </div>

          <!-- Símbolo -->
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="sym" class="text-right font-semibold">Símbolo</Label>
            <Input
              id="sym"
              v-model="form.symbol"
              class="col-span-3"
              placeholder="Ej: UND, KG"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" @click="closeModal">Cancelar</Button>
          <Button type="submit" @click="saveUnit">
            {{ isEditing ? 'Actualizar' : 'Guardar' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
