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

const filteredProviders = computed(() => {
  if (!searchQuery.value) return providers.value
  const q = searchQuery.value.toLowerCase()
  return providers.value.filter(p =>
    p.ruc.toLowerCase().includes(q) ||
    p.name.toLowerCase().includes(q)||
    p.address.toLowerCase().includes(q)
  )
})

const fetchProviders = async () => {
  isLoading.value = true
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch('/api/purchases/providerslist', {
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
    </div>

    <!-- Tabla -->
    <div class="border rounded-md bg-white shadow-sm">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[120px]">ID</TableHead>
            <TableHead>Razon Social</TableHead>
            <TableHead class="w-[120px]">RUC</TableHead>
            <TableHead class="text-right">Dirección</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="isLoading && units.length === 0">
            <TableCell colspan="4" class="h-24 text-center">
              <Loader2 class="h-6 w-6 animate-spin mx-auto text-blue-600"/>
            </TableCell>
          </TableRow>

          <TableRow v-else v-for="item in filteredProviders" :key="item.id">
            <TableCell class="font-bold font-mono text-blue-700 bg-blue-50/50">
              {{ item.id }}
            </TableCell>
            <TableCell>{{ item.name }}</TableCell>
            <TableCell>
                <span class="px-2 py-1 rounded bg-gray-100 text-xs font-semibold text-gray-700">
                    {{ item.ruc }}
                </span>
            </TableCell>
            <TableCell>
               {{ item.address }}
            </TableCell>
          </TableRow>

          <TableRow v-if="filteredProviders.length === 0 && !isLoading">
            <TableCell colspan="4" class="text-center h-24 text-muted-foreground">
              No se encontraron resultados.
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
</div>
</template>

<style scoped>

</style>