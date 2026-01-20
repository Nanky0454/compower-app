<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Badge } from '@/components/ui/badge'
import { RouterLink } from 'vue-router'

const { getAccessTokenSilently } = useAuth0()
const receivableOrders = ref([])
const isLoading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/purchases/receivable`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('No se pudieron cargar las órdenes pendientes.')
    receivableOrders.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div>
    <h1 class="text-3xl font-bold mb-4">
      Recepcionar Órdenes de Compra
    </h1>
    <p class="text-gray-600 mb-4">Selecciona una orden "Aprobada" para ingresar sus items al inventario.</p>

    <div v-if="isLoading">Cargando órdenes pendientes...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Código</TableHead>
            <TableHead>Proveedor</TableHead>
            <TableHead>Centro de Costo</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead>Acción</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="receivableOrders.length === 0">
            <TableCell colspan="5" class="text-center">No hay órdenes pendientes de recepción.</TableCell>
          </TableRow>
          <TableRow v-for="order in receivableOrders" :key="order.id">
            <TableCell class="font-medium">{{ order.codigo }}</TableCell>
            <TableCell>{{ order.provider_name }}</TableCell>
            <TableCell>{{ order.cost_center_code }}</TableCell>
            <TableCell>
              <Badge variant="secondary">{{ order.status }}</Badge>
            </TableCell>
            <TableCell>
              <Button as-child size="sm">
                <RouterLink :to="`/inventory/receive/${order.id}`">
                  Recepcionar
                </RouterLink>
              </Button>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>
  </div>
</template>
