<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button/index.js'
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Label } from '@/components/ui/label/index.js'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Pencil, Upload, Loader2, Trash2 } from 'lucide-vue-next' // <-- AÑADE Upload, Loader2

const { getAccessTokenSilently } = useAuth0()
const categories = ref([])
const isLoading = ref(true)
const error = ref(null)

const isDialogOpen = ref(false)
const modalMode = ref('create')
const formData = ref({ id: null, name: '', description: '', parent_id: null })

// --- Estado para el diálogo de eliminación ---
const isDeleteDialogOpen = ref(false)
const categoryToDelete = ref(null)

// --- Lógica de Importación ---
const fileInput = ref(null)
const isImporting = ref(false)

async function fetchCategories() {
  isLoading.value = true
  error.value = null
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/categories`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('No se pudieron cargar las categorías.')
    categories.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}
onMounted(fetchCategories)

function openCreateModal() {
  modalMode.value = 'create'
  formData.value = { id: null, name: '', description: '', parent_id: null }
  isDialogOpen.value = true
}

function openEditModal(category) {
  modalMode.value = 'edit'
  formData.value = { ...category }
  isDialogOpen.value = true
}

// --- Funciones para Eliminar ---
function openDeleteDialog(category) {
  categoryToDelete.value = category
  isDeleteDialogOpen.value = true
}

async function handleDeleteConfirm() {
  if (!categoryToDelete.value) return

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/categories/${categoryToDelete.value.id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Error al eliminar la categoría.')
    }

    isDeleteDialogOpen.value = false
    categoryToDelete.value = null
    await fetchCategories() // Recargar la lista
  } catch (e) {
    alert(e.message)
  }
}


async function handleFormSubmit() {
  let url = `${import.meta.env.VITE_API_URL}/api/categories`
  let method = 'POST'

  if (modalMode.value === 'edit') {
    url = `${import.meta.env.VITE_API_URL}/api/categories/${formData.value.id}`
    method = 'PUT'
  }

  // Asegurarse de que parent_id sea null si está vacío, no 0 o ""
  const payload = { ...formData.value }
  if (!payload.parent_id) {
    payload.parent_id = null
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
    await fetchCategories()
  } catch (e) {
    alert(e.message)
  }
}

// --- Funciones de Importación ---
function triggerImport() {
  fileInput.value.click()
}

async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return

  isImporting.value = true

  const formData = new FormData()
  formData.append('file', file)

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/categories/import`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
        // NOTA: No pongas 'Content-Type': 'application/json' aquí.
        // El navegador lo pondrá automáticamente como 'multipart/form-data'
      },
      body: formData
    })

    const result = await response.json()

    if (!response.ok) throw new Error(result.error || 'Error en la importación')

    alert(`Importación Exitosa:\nCreadas: ${result.created}\nActualizadas: ${result.updated}\nErrores: ${result.errors.length}`)
    await fetchCategories() // Recargar la tabla

  } catch (e) {
    alert(e.message)
  } finally {
    isImporting.value = false
    event.target.value = '' // Limpiar el input para poder subir el mismo archivo de nuevo si se quiere
  }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">Gestión de Categorías</h1>

      <div class="flex gap-2">
        <!-- Input de archivo oculto -->
        <input
          type="file"
          ref="fileInput"
          class="hidden"
          accept=".xlsx, .xls"
          @change="handleFileUpload"
        />
        <!-- Botón para disparar la importación -->
        <Button variant="outline" @click="triggerImport" :disabled="isImporting">
          <Loader2 v-if="isImporting" class="h-4 w-4 animate-spin mr-2" />
          <Upload v-else class="h-4 w-4 mr-2" />
          Importar Excel
        </Button>
        <Button @click="openCreateModal">Crear Categoría</Button>
      </div>
    </div>

    <!-- Mensaje de Instrucciones -->
    <div class="bg-blue-50 p-3 rounded-md text-sm text-blue-800 mb-4">
      <strong>Para importar categorías:</strong> El archivo Excel debe tener al menos la columna "Nombre". La columna "Padre" es opcional y se usa para subcategorías.
    </div>

    <div v-if="isLoading">Cargando...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nombre</TableHead>
            <TableHead>Categoría Padre (Subcategoría de)</TableHead>
            <TableHead>Acciones</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="cat in categories" :key="cat.id">
            <TableCell class="font-medium">{{ cat.name }}</TableCell>
            <TableCell>{{ cat.parent_name || '---' }}</TableCell>
            <TableCell class="flex gap-2">
              <Button variant="outline" size="icon" @click="openEditModal(cat)">
                <Pencil class="h-4 w-4" />
              </Button>
              <Button variant="destructive" size="icon" @click="openDeleteDialog(cat)">
                <Trash2 class="h-4 w-4" />
              </Button>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>

    <!-- Modal de Crear/Editar -->
    <Dialog :open="isDialogOpen" @update:open="isDialogOpen = $event">
      <DialogContent class="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{{ modalMode === 'create' ? 'Crear' : 'Editar' }} Categoría</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="name" class="text-right">Nombre</Label>
            <Input id="name" v-model="formData.name" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="description" class="text-right">Descripción</Label>
            <Input id="description" v-model="formData.description" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="parent" class="text-right">Categoría Padre</Label>
            <Select v-model="formData.parent_id">
              <SelectTrigger class="col-span-3">
                <SelectValue placeholder="Selecciona (si es subcategoría)..." />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem :value="null">Ninguna (Categoría Principal)</SelectItem>
                  <SelectItem v-for="cat in categories" :key="cat.id" :value="cat.id">
                    {{ cat.name }}
                  </SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="secondary" @click="isDialogOpen = false">Cancelar</Button>
          <Button @click="handleFormSubmit">Guardar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Modal de Confirmación de Eliminación -->
    <Dialog :open="isDeleteDialogOpen" @update:open="isDeleteDialogOpen = $event">
      <DialogContent class="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Confirmar Eliminación</DialogTitle>
        </DialogHeader>
        <div class="py-4">
          <p>¿Estás seguro de que quieres eliminar la categoría <strong>"{{ categoryToDelete?.name }}"</strong>?</p>
          <p class="text-sm text-red-600 mt-2">
            Esta acción no se puede deshacer. Si esta categoría tiene subcategorías, podrían quedar huérfanas o ser eliminadas dependiendo de la configuración del sistema.
          </p>
        </div>
        <DialogFooter>
          <Button variant="secondary" @click="isDeleteDialogOpen = false">Cancelar</Button>
          <Button variant="destructive" @click="handleDeleteConfirm">Eliminar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
