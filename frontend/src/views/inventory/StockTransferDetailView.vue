<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Badge } from '@/components/ui/badge/index.js'

const route = useRoute()
const { getAccessTokenSilently } = useAuth0()

const transfer = ref(null)
const isLoading = ref(true)
const error = ref(null)

onMounted(async () => {
  const transferId = route.params.id
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/transfers/${transferId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) {
      throw new Error('No se pudo cargar el detalle de la transferencia.')
    }
    transfer.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }
  return new Date(dateString).toLocaleDateString('es-ES', options)
}
</script>

<template>
  <div>
    <div v-if="isLoading" class="text-center">Cargando detalle...</div>
    <div v-else-if="error" class="text-red-500 p-4 bg-red-50 rounded-md">{{ error }}</div>

    <div v-else-if="transfer" class="space-y-6">
      <div class="flex justify-between items-start">
        <div>
          <h1 class="text-3xl font-bold">Detalle de Transferencia #{{ transfer.id }}</h1>
          <p class="text-gray-500">Realizada el: {{ formatDate(transfer.transfer_date) }}</p>
        </div>
        <Badge :variant="transfer.status === 'Completada (GRE)' ? 'default' : 'secondary'">
          {{ transfer.status }}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Información General</CardTitle>
        </CardHeader>
        <CardContent class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p class="text-sm font-medium text-gray-500">Almacén de Origen</p>
            <p class="font-semibold">{{ transfer.origin_warehouse }}</p>
          </div>
          <div>
            <p class="text-sm font-medium text-gray-500">Destino</p>
            <p class="font-semibold">
              {{ transfer.destination_warehouse !== 'N/A' ? transfer.destination_warehouse : transfer.destination_external }}
            </p>
          </div>
          <div v-if="transfer.gre_series">
            <p class="text-sm font-medium text-gray-500">Documento Asociado (GRE)</p>
            <p class="font-semibold">{{ transfer.gre_series }}-{{ transfer.gre_number }}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Productos Transferidos</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>SKU</TableHead>
                <TableHead>Producto</TableHead>
                <TableHead class="text-right">Cantidad</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="item in transfer.items" :key="item.id">
                <TableCell>{{ item.product_sku }}</TableCell>
                <TableCell class="font-medium">{{ item.product_name }}</TableCell>
                <TableCell class="text-right">{{ item.quantity }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
