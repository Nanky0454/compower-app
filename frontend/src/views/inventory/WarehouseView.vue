<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button/index.js'
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Label } from '@/components/ui/label/index.js'
import { Loader2, Pencil, Trash2 } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()
const warehouses = ref([])
const isLoading = ref(true)
const error = ref(null)

// --- CAMBIO: Añadir address y ubigeo al formData inicial ---
const isDialogOpen = ref(false)
const modalMode = ref('create') // 'create' o 'edit'
const formData = ref({ id: null, name: '', location: '', address: '', ubigeo: '' })

// --- Cargar Datos ---
async function fetchWarehouses() {
  isLoading.value = true
  error.value = null
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/warehouses`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('No se pudieron cargar los almacenes.')
    warehouses.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}
onMounted(fetchWarehouses)

// --- Abrir Modales ---
function openCreateModal() {
  modalMode.value = 'create'
  // --- CAMBIO: Resetear el formulario con los nuevos campos ---
  formData.value = { id: null, name: '', location: '', address: '', ubigeo: '' }
  isDialogOpen.value = true
}

function openEditModal(warehouse) {
  modalMode.value = 'edit'
  formData.value = { ...warehouse } // Copia todos los datos, incluyendo los nuevos
  isDialogOpen.value = true
}

// --- Guardar Cambios (Crear o Editar) ---
async function handleFormSubmit() {
  let url = `${import.meta.env.VITE_API_URL}/api/warehouses`
  let method = 'POST'

  if (modalMode.value === 'edit') {
    url = `${import.meta.env.VITE_API_URL}/api/warehouses/${formData.value.id}`
    method = 'PUT'
  }

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(url, {
      method: method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(formData.value)
    })
    if (!response.ok) throw new Error('Error al guardar.')

    isDialogOpen.value = false
    await fetchWarehouses() // Recargar la tabla
  } catch (e) {
    alert(e.message)
  }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">Gestión de Almacenes</h1>
      <Button @click="openCreateModal">Crear Almacén</Button>
    </div>

    <div v-if="isLoading">Cargando...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nombre</TableHead>
            <TableHead>Ubicación (Distrito)</TableHead>
            <!-- CAMBIO: Nuevas columnas -->
            <TableHead>Dirección</TableHead>
            <TableHead>Ubigeo</TableHead>
            <TableHead>Acciones</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="wh in warehouses" :key="wh.id">
            <TableCell class="font-medium">{{ wh.name }}</TableCell>
            <TableCell>{{ wh.location }}</TableCell>
            <!-- CAMBIO: Nuevas celdas -->
            <TableCell>{{ wh.address }}</TableCell>
            <TableCell>{{ wh.ubigeo }}</TableCell>
            <TableCell>
              <Button variant="outline" size="icon" @click="openEditModal(wh)">
                <Pencil class="h-4 w-4" />
              </Button>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>

    <Dialog :open="isDialogOpen" @update:open="isDialogOpen = $event">
      <DialogContent class="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{{ modalMode === 'create' ? 'Crear' : 'Editar' }} Almacén</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="name" class="text-right">Nombre</Label>
            <Input id="name" v-model="formData.name" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="location" class="text-right">Ubicación (Distrito)</Label>
            <Input id="location" v-model="formData.location" class="col-span-3" />
          </div>
          <!-- CAMBIO: Nuevos campos en el formulario -->
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="address" class="text-right">Dirección</Label>
            <Input id="address" v-model="formData.address" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="ubigeo" class="text-right">Ubigeo</Label>
            <Input id="ubigeo" v-model="formData.ubigeo" class="col-span-3" />
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
