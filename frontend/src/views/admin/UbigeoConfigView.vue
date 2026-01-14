<script setup>
import { ref, onMounted, watch } from 'vue'
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
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Pencil, Trash2, Plus, Search, Upload } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()

const ubigeos = ref([])
const searchQuery = ref('')
const isLoading = ref(false)
const isModalOpen = ref(false)
const isEditing = ref(false)
const fileInput = ref(null)

const form = ref({
  id: null,
  ubigeo_inei: '',
  departamento: '',
  provincia: '',
  distrito: ''
})

// --- API Calls ---

const fetchUbigeos = async () => {
  isLoading.value = true
  try {
    const token = await getAccessTokenSilently()
    const url = searchQuery.value.length >= 3 
        ? `/api/ubigeo/search?q=${searchQuery.value}` 
        : '/api/ubigeo/'
    
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) ubigeos.value = await res.json()
  } catch (error) {
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

const saveUbigeo = async () => {
  try {
    const token = await getAccessTokenSilently()
    const method = isEditing.value ? 'PUT' : 'POST'
    const url = isEditing.value ? `/api/ubigeo/${form.value.id}` : '/api/ubigeo/'
    
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(form.value)
    })

    if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Error saving ubigeo')
    }

    await fetchUbigeos()
    closeModal()
  } catch (error) {
    alert(error.message)
  }
}

const deleteUbigeo = async (id) => {
  if (!confirm('¿Estás seguro de eliminar este Ubigeo?')) return
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`/api/ubigeo/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Error deleting ubigeo')
    }
    await fetchUbigeos()
  } catch (error) {
    alert(error.message)
  }
}

const triggerFileUpload = () => {
  fileInput.value.click()
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  try {
    const token = await getAccessTokenSilently()
    const res = await fetch('/api/ubigeo/import', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData
    })
    
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || 'Error uploading file')

    alert(`Importación completada.\nCreados: ${data.created}\nActualizados: ${data.updated}\nErrores: ${data.errors_count}`)
    await fetchUbigeos()
  } catch (error) {
    alert(error.message)
  } finally {
    event.target.value = '' // Reset input
  }
}

// --- UI Helpers ---

const openCreateModal = () => {
  isEditing.value = false
  form.value = { id: null, ubigeo_inei: '', departamento: '', provincia: '', distrito: '' }
  isModalOpen.value = true
}

const openEditModal = (item) => {
  isEditing.value = true
  form.value = { ...item }
  isModalOpen.value = true
}

const closeModal = () => {
  isModalOpen.value = false
}

// Debounce search
let timeout
watch(searchQuery, (newVal) => {
    clearTimeout(timeout)
    if (newVal.length >= 3 || newVal.length === 0) {
        timeout = setTimeout(() => fetchUbigeos(), 500)
    }
})

onMounted(() => {
  fetchUbigeos()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-3xl font-bold tracking-tight">Configuración de Ubigeos</h2>
        <p class="text-muted-foreground">Gestiona el catálogo de ubicaciones geográficas.</p>
      </div>
      <div class="flex space-x-2">
        <input type="file" ref="fileInput" class="hidden" accept=".xlsx, .xls, .csv" @change="handleFileUpload" />
        <Button variant="outline" @click="triggerFileUpload">
          <Upload class="mr-2 h-4 w-4" /> Cargar Excel/CSV
        </Button>
        <Button @click="openCreateModal">
          <Plus class="mr-2 h-4 w-4" /> Nuevo Ubigeo
        </Button>
      </div>
    </div>

    <div class="flex items-center space-x-2">
        <Search class="h-4 w-4 text-muted-foreground" />
        <Input v-model="searchQuery" placeholder="Buscar por nombre o código..." class="max-w-sm" />
    </div>

    <div class="border rounded-md">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Código INEI</TableHead>
            <TableHead>Departamento</TableHead>
            <TableHead>Provincia</TableHead>
            <TableHead>Distrito</TableHead>
            <TableHead class="text-right">Acciones</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="item in ubigeos" :key="item.id">
            <TableCell class="font-medium">{{ item.ubigeo_inei }}</TableCell>
            <TableCell>{{ item.departamento }}</TableCell>
            <TableCell>{{ item.provincia }}</TableCell>
            <TableCell>{{ item.distrito }}</TableCell>
            <TableCell class="text-right">
              <Button variant="ghost" size="icon" @click="openEditModal(item)">
                <Pencil class="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" class="text-red-600" @click="deleteUbigeo(item.id)">
                <Trash2 class="h-4 w-4" />
              </Button>
            </TableCell>
          </TableRow>
          <TableRow v-if="ubigeos.length === 0 && !isLoading">
            <TableCell colspan="5" class="text-center h-24 text-muted-foreground">
              No se encontraron resultados.
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <Dialog :open="isModalOpen" @update:open="isModalOpen = $event">
      <DialogContent class="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{{ isEditing ? 'Editar Ubigeo' : 'Crear Ubigeo' }}</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="code" class="text-right">Código INEI</Label>
            <Input id="code" v-model="form.ubigeo_inei" class="col-span-3" placeholder="Ej: 150101" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="dep" class="text-right">Departamento</Label>
            <Input id="dep" v-model="form.departamento" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="prov" class="text-right">Provincia</Label>
            <Input id="prov" v-model="form.provincia" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="dist" class="text-right">Distrito</Label>
            <Input id="dist" v-model="form.distrito" class="col-span-3" />
          </div>
        </div>
        <DialogFooter>
          <Button type="submit" @click="saveUbigeo">Guardar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
