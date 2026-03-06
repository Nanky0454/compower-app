<script setup>
import { ref, onMounted, computed, reactive } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button/index.js'
import { Input } from '@/components/ui/input/index.js'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table/index.js'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription
} from '@/components/ui/dialog/index.js'
import { Label } from '@/components/ui/label/index.js'
import { Pencil, Trash2, Plus, Search, Upload, Loader2, FileSpreadsheet } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()

// --- ESTADOS ---
const providers = ref([])
const searchQuery = ref('')
const isLoading = ref(false)
const isAddProviderDialogOpen = ref(false)
const isEditProviderDialogOpen = ref(false)
const isSearchingRuc = ref(false)
const newProvider = reactive({
  ruc: '',
  name: '',
  address: ''
})
const editingProvider = ref(null)

const filteredProviders = computed(() => {
  if (!searchQuery.value) return providers.value
  const q = searchQuery.value.toLowerCase()
  return providers.value.filter(p =>
    (p.ruc && p.ruc.toLowerCase().includes(q)) ||
    (p.name && p.name.toLowerCase().includes(q)) ||
    (p.address && p.address.toLowerCase().includes(q))
  )
})

const fetchProviders = async () => {
  isLoading.value = true
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/purchases/providerslist`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      providers.value = await res.json()
    }
  } catch (error) {
    console.error("Error cargando unidades:", error)
  } finally {
    isLoading.value = false
  }
}

const searchRuc = async () => {
  if (!newProvider.ruc || newProvider.ruc.length !== 11) {
    alert('Por favor, ingrese un RUC válido de 11 dígitos.')
    return
  }
  isSearchingRuc.value = true
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/purchases/lookup-provider/${newProvider.ruc}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      const data = await res.json()
      newProvider.name = data.name
      newProvider.address = data.address
    } else {
      alert('No se encontró el RUC.')
    }
  } catch (error) {
    console.error("Error buscando RUC:", error)
    alert('Ocurrió un error al buscar el RUC.')
  } finally {
    isSearchingRuc.value = false
  }
}

const saveProvider = async () => {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/purchases/providers`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(newProvider)
    })
    if (res.ok) {
      isAddProviderDialogOpen.value = false
      fetchProviders()
      newProvider.ruc = ''
      newProvider.name = ''
      newProvider.address = ''
    } else {
      console.error("Error guardando proveedor:", await res.text())
      alert('Ocurrió un error al guardar el proveedor.')
    }
  } catch (error) {
    console.error("Error guardando proveedor:", error)
    alert('Ocurrió un error al guardar el proveedor.')
  }
}

const openEditDialog = (provider) => {
  editingProvider.value = { ...provider }
  isEditProviderDialogOpen.value = true
}

const updateProvider = async () => {
  if (!editingProvider.value) return
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/purchases/providers/${editingProvider.value.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(editingProvider.value)
    })
    if (res.ok) {
      isEditProviderDialogOpen.value = false
      fetchProviders()
    } else {
      console.error("Error actualizando proveedor:", await res.text())
      alert('Ocurrió un error al actualizar el proveedor.')
    }
  } catch (error) {
    console.error("Error actualizando proveedor:", error)
    alert('Ocurrió un error al actualizar el proveedor.')
  }
}

onMounted(() => {
  fetchProviders()
})
</script>

<template>

<div class="space-y-6 p-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <h2 class="text-3xl font-bold tracking-tight text-gray-900">Lista de proveedores</h2>
      </div>
      <div class="flex items-center gap-2">
        <div class="relative w-full max-w-sm items-center">
          <Input
            id="search"
            type="text"
            placeholder="Buscar por RUC, nombre o dirección..."
            class="pl-10"
            v-model="searchQuery"
          />
          <span class="absolute start-0 inset-y-0 flex items-center justify-center px-2">
            <Search class="h-5 w-5 text-muted-foreground" />
          </span>
        </div>
        <Button @click="isAddProviderDialogOpen = true">
          <Plus class="h-4 w-4 mr-2"/>
          Agregar Proveedor
        </Button>
      </div>
    </div>

    <!-- Tabla -->
    <div class="border rounded-md bg-white shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[120px]">ID</TableHead>
            <TableHead class>Razon Social</TableHead>
            <TableHead class="w-[120px]">RUC</TableHead>
            <TableHead >Dirección</TableHead>
            <TableHead class="w-[100px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="isLoading && providers.length === 0">
            <TableCell colspan="5" class="h-24 text-center">
              <Loader2 class="h-6 w-6 animate-spin mx-auto text-blue-600"/>
            </TableCell>
          </TableRow>

          <TableRow v-else v-for="item in filteredProviders" :key="item.id">
            <TableCell class="font-bold font-mono text-blue-700 bg-blue-50/50">
              {{ item.id }}
            </TableCell>
            <TableCell class="max-w-xs whitespace-normal break-words">{{ item.name }}</TableCell>
            <TableCell>
                <span class="px-2 py-1 rounded bg-gray-100 text-xs font-semibold text-gray-700">
                    {{ item.ruc }}
                </span>
            </TableCell>
            <TableCell class="max-w-xs whitespace-normal break-words">
               {{ item.address }}
            </TableCell>
            <TableCell>
              <Button variant="ghost" size="sm" @click="openEditDialog(item)">
                <Pencil class="h-4 w-4"/>
              </Button>
            </TableCell>
          </TableRow>

          <TableRow v-if="filteredProviders.length === 0 && !isLoading">
            <TableCell colspan="5" class="text-center h-24 text-muted-foreground">
              No se encontraron resultados.
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
</div>

<Dialog :open="isAddProviderDialogOpen" @update:open="isAddProviderDialogOpen = $event">
  <DialogContent class="sm:max-w-md">
    <DialogHeader>
      <DialogTitle>Agregar Nuevo Proveedor</DialogTitle>
    </DialogHeader>
    <div class="grid gap-4 py-4">
      <div class="grid grid-cols-4 items-center gap-4">
        <Label for="ruc" class="text-right">RUC</Label>
        <div class="col-span-3 flex gap-2">
          <Input id="ruc" v-model="newProvider.ruc" class="w-full"/>
          <Button @click="searchRuc" :disabled="isSearchingRuc">
            <Loader2 v-if="isSearchingRuc" class="h-4 w-4 animate-spin"/>
            <Search v-else class="h-4 w-4"/>
          </Button>
        </div>
      </div>
       <div class="grid grid-cols-4 items-center gap-4">
        <Label for="name" class="text-right">Razón Social</Label>
        <Input id="name" v-model="newProvider.name" class="col-span-3"/>
      </div>
      <div class="grid grid-cols-4 items-center gap-4">
        <Label for="address" class="text-right">Dirección</Label>
        <Input id="address" v-model="newProvider.address" class="col-span-3"/>
      </div>
    </div>
    <DialogFooter>
      <Button variant="secondary" @click="isAddProviderDialogOpen = false">Cancelar</Button>
      <Button @click="saveProvider">Guardar Proveedor</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>

<Dialog :open="isEditProviderDialogOpen" @update:open="isEditProviderDialogOpen = $event">
  <DialogContent class="sm:max-w-md">
    <DialogHeader>
      <DialogTitle>Editar Proveedor</DialogTitle>
    </DialogHeader>
    <div v-if="editingProvider" class="grid gap-4 py-4">
      <div class="grid grid-cols-4 items-center gap-4">
        <Label for="edit-ruc" class="text-right">RUC</Label>
        <Input id="edit-ruc" v-model="editingProvider.ruc" class="col-span-3"/>
      </div>
       <div class="grid grid-cols-4 items-center gap-4">
        <Label for="edit-name" class="text-right">Razón Social</Label>
        <Input id="edit-name" v-model="editingProvider.name" class="col-span-3"/>
      </div>
      <div class="grid grid-cols-4 items-center gap-4">
        <Label for="edit-address" class="text-right">Dirección</Label>
        <Input id="edit-address" v-model="editingProvider.address" class="col-span-3"/>
      </div>
    </div>
    <DialogFooter>
      <Button variant="secondary" @click="isEditProviderDialogOpen = false">Cancelar</Button>
      <Button @click="updateProvider">Actualizar Proveedor</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
</template>

<style scoped>

</style>