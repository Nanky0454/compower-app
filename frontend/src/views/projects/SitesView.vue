<script setup>
import { ref, onMounted, computed } from 'vue'
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
import { Badge } from '@/components/ui/badge'
import { Pencil, Trash2, Plus } from 'lucide-vue-next'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const { getAccessTokenSilently } = useAuth0()

const sites = ref([])
const providers = ref([])
const costCenters = ref([])
const ubigeos = ref([]) // Para búsqueda de ubigeo (opcional, o input simple)
const isLoading = ref(false)
const isModalOpen = ref(false)
const isEditing = ref(false)

const form = ref({
  id: null,
  name: '',
  ruc: '',
  address: '',
  ubigeo_code: '',
  provider_id: null,
  cost_center_id: null,
  status: 'ACTIVE'
})

// --- API Calls ---

const fetchSites = async () => {
  isLoading.value = true
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch('/api/locations/', {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('Error fetching sites')
    sites.value = await res.json()
  } catch (error) {
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

const fetchProviders = async () => {
    // Asumiendo que existe endpoint para proveedores, si no, habrá que crearlo o usar mock
    // Por ahora simularemos o intentaremos llamar a una API existente si la hay
    // Revisando archivos anteriores, existe provider.py pero no vi provider_api.py explícito completo
    // Intentaremos llamar a /api/purchases/providers si existe, o similar.
    // Si no, dejaremos vacío por ahora.
    try {
        const token = await getAccessTokenSilently()
        // Ajustar endpoint según existencia real
        const res = await fetch('/api/purchases/providers', { 
             headers: { Authorization: `Bearer ${token}` }
        })
        if (res.ok) providers.value = await res.json()
    } catch (e) {
        console.warn("No se pudieron cargar proveedores", e)
    }
}

const fetchCostCenters = async () => {
    try {
        const token = await getAccessTokenSilently()
        const res = await fetch('/api/cost-centers/', { 
             headers: { Authorization: `Bearer ${token}` }
        })
        if (res.ok) costCenters.value = await res.json()
    } catch (e) {
        console.warn("No se pudieron cargar centros de costo", e)
    }
}

const saveSite = async () => {
  try {
    const token = await getAccessTokenSilently()
    const method = isEditing.value ? 'PUT' : 'POST'
    const url = isEditing.value ? `/api/locations/${form.value.id}` : '/api/locations/'
    
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
        throw new Error(err.error || 'Error saving site')
    }

    await fetchSites()
    closeModal()
  } catch (error) {
    alert(error.message)
  }
}

const deleteSite = async (id) => {
  if (!confirm('¿Estás seguro de eliminar este site?')) return
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`/api/locations/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('Error deleting site')
    await fetchSites()
  } catch (error) {
    alert(error.message)
  }
}

// --- UI Helpers ---

const openCreateModal = () => {
  isEditing.value = false
  form.value = {
    id: null, name: '', ruc: '', address: '', ubigeo_code: '',
    provider_id: null, cost_center_id: null, status: 'ACTIVE'
  }
  isModalOpen.value = true
}

const openEditModal = (site) => {
  isEditing.value = true
  form.value = { ...site }
  isModalOpen.value = true
}

const closeModal = () => {
  isModalOpen.value = false
}

onMounted(() => {
  fetchSites()
  fetchProviders()
  fetchCostCenters()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-3xl font-bold tracking-tight">Sites</h2>
        <p class="text-muted-foreground">Gestiona los sites y sus asociaciones.</p>
      </div>
      <Button @click="openCreateModal">
        <Plus class="mr-2 h-4 w-4" /> Crear Site
      </Button>
    </div>

    <div class="border rounded-md">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nombre</TableHead>
            <TableHead>RUC</TableHead>
            <TableHead>Dirección</TableHead>
            <TableHead>Ubigeo</TableHead>
            <TableHead>Proveedor</TableHead>
            <TableHead>Centro de Costo</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead class="text-right">Acciones</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="site in sites" :key="site.id">
            <TableCell class="font-medium">{{ site.name }}</TableCell>
            <TableCell>{{ site.ruc }}</TableCell>
            <TableCell>{{ site.address }}</TableCell>
            <TableCell>{{ site.ubigeo_code }}</TableCell>
            <TableCell>{{ site.provider_name || '-' }}</TableCell>
            <TableCell>{{ site.cost_center_name || '-' }}</TableCell>
            <TableCell>
              <Badge :variant="site.status === 'ACTIVE' ? 'default' : 'secondary'">
                {{ site.status }}
              </Badge>
            </TableCell>
            <TableCell class="text-right">
              <Button variant="ghost" size="icon" @click="openEditModal(site)">
                <Pencil class="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" class="text-red-600" @click="deleteSite(site.id)">
                <Trash2 class="h-4 w-4" />
              </Button>
            </TableCell>
          </TableRow>
          <TableRow v-if="sites.length === 0 && !isLoading">
            <TableCell colspan="8" class="text-center h-24 text-muted-foreground">
              No hay sites registrados.
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <Dialog :open="isModalOpen" @update:open="isModalOpen = $event">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{{ isEditing ? 'Editar Site' : 'Crear Site' }}</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 py-4">
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="name" class="text-right">Nombre</Label>
            <Input id="name" v-model="form.name" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="ruc" class="text-right">RUC</Label>
            <Input id="ruc" v-model="form.ruc" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="address" class="text-right">Dirección</Label>
            <Input id="address" v-model="form.address" class="col-span-3" />
          </div>
          <div class="grid grid-cols-4 items-center gap-4">
            <Label for="ubigeo" class="text-right">Ubigeo</Label>
            <Input id="ubigeo" v-model="form.ubigeo_code" placeholder="Ej: 150101" class="col-span-3" />
          </div>
          
          <div class="grid grid-cols-4 items-center gap-4">
            <Label class="text-right">Proveedor</Label>
            <Select v-model="form.provider_id">
              <SelectTrigger class="col-span-3">
                <SelectValue placeholder="Seleccionar proveedor" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="p in providers" :key="p.id" :value="p.id">
                  {{ p.name }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="grid grid-cols-4 items-center gap-4">
            <Label class="text-right">Centro Costo</Label>
            <Select v-model="form.cost_center_id">
              <SelectTrigger class="col-span-3">
                <SelectValue placeholder="Seleccionar C.C." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="cc in costCenters" :key="cc.id" :value="cc.id">
                  {{ cc.name }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

           <div class="grid grid-cols-4 items-center gap-4">
            <Label class="text-right">Estado</Label>
            <Select v-model="form.status">
              <SelectTrigger class="col-span-3">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ACTIVE">Activo</SelectItem>
                <SelectItem value="INACTIVE">Inactivo</SelectItem>
              </SelectContent>
            </Select>
          </div>

        </div>
        <DialogFooter>
          <Button type="submit" @click="saveSite">Guardar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
