<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router' // <-- Para leer el ID de la URL
import { useAuth0 } from '@auth0/auth0-vue'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableFooter } from '@/components/ui/table/index.js'

// Hooks
const route = useRoute()
const { getAccessTokenSilently } = useAuth0()

// Refs
const order = ref(null)
const isLoading = ref(true)
const error = ref(null)

// Helper de moneda
const currencyFormatter = new Intl.NumberFormat('es-PE', {
  style: 'currency',
  currency: 'PEN',
})

// Cargar los datos de la orden
onMounted(async () => {
  const orderId = route.params.id // Obtenemos el ID de la URL (ej. /compras/8)
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/purchases/${orderId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (response.status === 403) throw new Error('No tienes permiso para ver esta orden.')
    if (!response.ok) throw new Error('No se pudo cargar la orden.')

    order.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div>
    <div v-if="isLoading">Cargando detalle de la orden...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <div v-else-if="order" class="space-y-6">

      <h1 class="text-3xl font-bold">
        Detalle de Orden: {{ order.document_number }}
      </h1>

      <Card>
        <CardHeader>
          <CardTitle>Resumen de la Orden</CardTitle>
        </CardHeader>
        <CardContent class="grid grid-cols-3 gap-4">
          <div>
            <p class="text-sm font-medium text-gray-500">Proveedor</p>
            <p class="font-semibold">{{ order.provider }}</p>
          </div>
          <div>
            <p class="text-sm font-medium text-gray-500">Centro de Costo</p>
            <p class="font-semibold">{{ order.cost_center }}</p>
          </div>
          <div>
            <p class="text-sm font-medium text-gray-500">Estado</p>
            <p class="font-semibold">{{ order.status }}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Items Incluidos</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Detalle</TableHead>
                <TableHead>UM</TableHead>
                <TableHead class="text-right">Cantidad</TableHead>
                <TableHead class="text-right">P. Unitario</TableHead>
                <TableHead class="text-right">Subtotal</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="item in order.items" :key="item.id">
                <TableCell class="font-medium">{{ item.invoice_detail_text }}</TableCell>
                <TableCell>{{ item.unit_of_measure }}</TableCell>
                <TableCell class="text-right">{{ item.quantity }}</TableCell>
                <TableCell class="text-right">{{ currencyFormatter.format(item.unit_price) }}</TableCell>
                <TableCell class="text-right font-medium">
                  {{ currencyFormatter.format(item.quantity * item.unit_price) }}
                </TableCell>
              </TableRow>
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell colspan="4" class="text-right font-bold text-lg">Monto Total</TableCell>
                <TableCell class="text-right font-bold text-lg">
                  {{ currencyFormatter.format(order.total_amount) }}
                </TableCell>
              </TableRow>
            </TableFooter>
          </Table>
        </CardContent>
      </Card>

    </div>
  </div>
</template>
