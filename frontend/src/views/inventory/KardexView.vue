<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Loader2 } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()

// --- State ---
const transactions = ref([])
const products = ref([])
const warehouses = ref([])
const isLoading = ref(true)
const error = ref(null)

// --- Filters ---
const filters = ref({
  product_id: null,
  warehouse_id: null,
})

// --- Data Fetching ---
async function fetchData(entity, url) {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } })
    if (!response.ok) throw new Error(`No se pudo cargar ${entity}.`)
    return await response.json()
  } catch (e) {
    error.value = e.message
    return []
  }
}

async function fetchKardex() {
  isLoading.value = true
  error.value = null

  const params = new URLSearchParams()
  if (filters.value.product_id) params.append('product_id', filters.value.product_id)
  if (filters.value.warehouse_id) params.append('warehouse_id', filters.value.warehouse_id)

  transactions.value = await fetchData('el Kardex', `${import.meta.env.VITE_API_URL}/api/inventory/transactions?${params.toString()}`)
  isLoading.value = false
}

onMounted(async () => {
  products.value = await fetchData('productos', `${import.meta.env.VITE_API_URL}/api/products`)
  warehouses.value = await fetchData('almacenes', `${import.meta.env.VITE_API_URL}/api/warehouses`)
  await fetchKardex()
})

watch(filters, fetchKardex, { deep: true })

// --- Helpers ---
function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const options = { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }
  return new Date(dateString).toLocaleString('es-ES', options)
}

function clearFilters() {
  filters.value = { product_id: null, warehouse_id: null }
}
</script>

<template>
  <div class="space-y-4">
    <h2 class="text-2xl font-bold">Kardex de Inventario</h2>

    <Card class="p-4">
      <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 items-end">
        <div>
          <label class="text-sm font-medium">Producto</label>
          <Select v-model="filters.product_id">
            <SelectTrigger>
              <SelectValue class="truncate" placeholder="Todos los productos" />
            </SelectTrigger>

            <SelectContent class="max-w-[90vw] md:max-w-[400px]">
              <SelectItem
                v-for="product in products"
                :key="product.id"
                :value="product.id.toString()"
                class="whitespace-normal h-auto py-2 block"
              >
               {{ product.name }} ({{ product.sku }})
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <label class="text-sm font-medium">Almacén</label>
          <Select v-model="filters.warehouse_id">
            <SelectTrigger>
              <SelectValue class="truncate" placeholder="Todos los almacenes" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="wh in warehouses" :key="wh.id" :value="wh.id.toString()">
                {{ wh.name }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <Button variant="outline" @click="clearFilters">Limpiar Filtros</Button>
        </div>
      </div>
    </Card>

    <div v-if="isLoading" class="text-center p-8">
      <Loader2 class="h-8 w-8 animate-spin mx-auto" />
      <p>Cargando Kardex...</p>
    </div>
    <div v-else-if="error" class="text-red-500 p-4 bg-red-50 rounded-md">{{ error }}</div>
    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[120px]">Fecha</TableHead>
            <TableHead>Producto</TableHead>
            <TableHead>Almacén</TableHead>
            <TableHead>Tipo Movimiento</TableHead>
            <TableHead>Referencia</TableHead>
            <TableHead class="text-right">Cambio</TableHead>
            <TableHead class="text-right">Saldo</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="transactions.length === 0">
            <TableCell colspan="7" class="text-center">No se encontraron movimientos.</TableCell>
          </TableRow>
          <TableRow v-for="tx in transactions" :key="tx.id">
            <TableCell class="text-xs">{{ formatDate(tx.timestamp) }}</TableCell>

            <TableCell class="max-w-[150px] md:max-w-[250px]">
              <div class="font-medium whitespace-normal break-words leading-tight">
                {{ tx.product_name }}
              </div>
              <div class="text-xs text-gray-500 mt-1">{{ tx.product_sku }}</div>
            </TableCell>

            <TableCell>{{ tx.warehouse_name }}</TableCell>

            <TableCell class="whitespace-normal max-w-[120px]">
                {{ tx.type }}
            </TableCell>

            <TableCell class="max-w-[150px]">
                <div class="whitespace-normal break-words text-sm">
                    {{ tx.reference || '-' }}
                </div>
            </TableCell>

            <TableCell :class="['text-right font-mono', tx.quantity_change > 0 ? 'text-green-600' : 'text-red-600']">
              {{ tx.quantity_change > 0 ? '+' : '' }}{{ tx.quantity_change }}
            </TableCell>
            <TableCell class="text-right font-mono font-semibold">{{ tx.new_quantity }}</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>
  </div>
</template>