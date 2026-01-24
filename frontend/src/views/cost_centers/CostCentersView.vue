<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button/index.js'
import { Card } from '@/components/ui/card/index.js'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table/index.js'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger, DialogClose,
} from '@/components/ui/dialog/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Label } from '@/components/ui/label/index.js'
import { Badge } from '@/components/ui/badge/index.js'
import { Pencil } from 'lucide-vue-next' // <-- Icono para editar
import {
  Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select/index.js' // <-- Nuevo componente

// Hooks
const { getAccessTokenSilently } = useAuth0()

// Refs
const costCenters = ref([])
const isLoading = ref(true)
const error = ref(null)

// --- Refs para el formulario (modal) ---
const isDialogOpen = ref(false)
const modalMode = ref('create') // <-- 'create' o 'edit'

// Usamos un 'ref' para el formulario
// Lo reseteamos a un estado vacío para la creación
const formData = ref({
  id: null,
  code: '',
  name: '',
  description: '',
  status: 'Activo',
  budget: 0.00
})

// Helper para formatear a moneda (ej. S/ 1,200.00)
const currencyFormatter = new Intl.NumberFormat('es-PE', {
  style: 'currency',
  currency: 'PEN',
})

// --- 1. Cargar la tabla ---
async function fetchCostCenters() {
  isLoading.value = true
  error.value = null
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/cost-centers/with-budget-consumption`, { // <-- API actualizada
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) {
      throw new Error('No se pudieron cargar los centros de costos.')
    }
    costCenters.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchCostCenters)

// --- 2. Funciones del Modal ---
function openCreateModal() {
  modalMode.value = 'create'
  // Resetea el formulario
  formData.value = {
    id: null, code: '', name: '', description: '', status: 'Activo', budget: 0.00
  }
  isDialogOpen.value = true
}

function openEditModal(cc) {
  modalMode.value = 'edit'
  // Carga el formulario con los datos del centro de costos
  formData.value = { ...cc }
  isDialogOpen.value = true
}

// --- 3. Manejar el envío del formulario (Crear o Editar) ---
async function handleFormSubmit() {
  let url = `${import.meta.env.VITE_API_URL}/api/cost-centers`
  let method = 'POST'

  // Si estamos en modo edición, cambiamos la URL y el método
  if (modalMode.value === 'edit') {
    url = `${import.meta.env.VITE_API_URL}/api/cost-centers/${formData.value.id}`
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
      body: JSON.stringify(formData.value) // Enviamos todos los datos
    })

    if (!response.ok) {
      if (response.status === 403) {
        alert(`¡Error! No tienes permiso para ${modalMode.value === 'create' ? 'crear' : 'editar'}.`)
        return
      }
      throw new Error(`Error al ${modalMode.value === 'create' ? 'crear' : 'editar'}.`)
    }

    // ¡Éxito!
    isDialogOpen.value = false // Cierra el modal
    await fetchCostCenters() // Recarga la tabla

  } catch (e) {
    alert(e.message)
  }
}
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">
        Centros de Costos
      </h1>

      <Button @click="openCreateModal">Crear Centro de Costo</Button>
    </div>

    <div v-if="isLoading">Cargando...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Código</TableHead>
            <TableHead>Nombre</TableHead>
            <TableHead>Presupuesto</TableHead>
            <TableHead>Consumido</TableHead>
            <TableHead>Disponible</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead>Acciones</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="cc in costCenters" :key="cc.id">
            <TableCell class="font-medium">{{ cc.code }}</TableCell>
            <TableCell>{{ cc.name }}</TableCell>
            <TableCell>{{ currencyFormatter.format(cc.budget) }}</TableCell>
            <TableCell>{{ currencyFormatter.format(cc.consumed_budget) }}</TableCell>
            <TableCell>{{ currencyFormatter.format(cc.remaining_budget) }}</TableCell>
            <TableCell>
              <Badge :variant="cc.status === 'Activo' ? 'default' : 'secondary'">
                {{ cc.status }}
              </Badge>
            </TableCell>
            <TableCell>
              <Button variant="outline" size="icon" @click="openEditModal(cc)">
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
          <DialogTitle>{{ modalMode === 'create' ? 'Crear' : 'Editar' }} Centro de Costo</DialogTitle>
        </DialogHeader>

        <div class="grid gap-4 py-4">
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="code" class="text-right">Código</Label>
            <Input id="code" v-model="formData.code" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="name" class="text-right">Nombre</Label>
            <Input id="name" v-model="formData.name" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="description" class="text-right">Descripción</Label>
            <Input id="description" v-model="formData.description" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="budget" class="text-right">Presupuesto (S/)</Label>
            <Input id="budget" type="number" v-model="formData.budget" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="status" class="text-right">Estado</Label>
            <Select v-model="formData.status">
              <SelectTrigger class="col-span-3">
                <SelectValue placeholder="Selecciona un estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="Activo">Activo</SelectItem>
                  <SelectItem value="Inactivo">Inactivo</SelectItem>
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

  </div>
</template>
