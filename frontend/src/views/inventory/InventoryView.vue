<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Badge } from '@/components/ui/badge'
import { RouterLink } from 'vue-router'
import { Eye, Pencil } from 'lucide-vue-next'
import EditReceiptModal from './components/EditReceiptModal.vue'

const { getAccessTokenSilently, user } = useAuth0()
const receivableOrders = ref([])
const isLoading = ref(true)
const error = ref(null)

// Nuevos estados para las recepciones pasadas
const pastReceipts = ref([])
const isLoadingPastReceipts = ref(true)
const errorPastReceipts = ref(null)

// State for the edit modal
const isEditModalOpen = ref(false)
const selectedReceipt = ref(null)

const AUTH0_NAMESPACE = 'https://appcompower.com'
const isAdmin = computed(() => {
  const rolesKey = AUTH0_NAMESPACE + '/roles';
  if (user.value && user.value[rolesKey] && Array.isArray(user.value[rolesKey])) {
    const userRoles = user.value[rolesKey].map(role => role.toLowerCase());
    return userRoles.includes('admin');
  }
  return false;
})

function openEditModal(receipt) {
  selectedReceipt.value = receipt
  isEditModalOpen.value = true
}

async function fetchPastReceipts() {
  isLoadingPastReceipts.value = true
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/inventory/receipts`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('No se pudieron cargar las recepciones pasadas.')
    pastReceipts.value = await response.json()
  } catch (e) {
    errorPastReceipts.value = e.message
  } finally {
    isLoadingPastReceipts.value = false
  }
}

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

  // Llamar a la nueva función para cargar recepciones pasadas
  await fetchPastReceipts()
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
            <TableCell>{{ order.cost_center_name }}</TableCell>
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
  <br>
  <div>
    <h1 class="text-2xl font-bold mb-4">
     Recepciones pasadas
    </h1>

    <div v-if="isLoadingPastReceipts">Cargando recepciones pasadas...</div>
    <div v-else-if="errorPastReceipts" class="text-red-500">{{ errorPastReceipts }}</div>

    <Card v-else>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Número de Factura</TableHead>
            <TableHead>Proveedor</TableHead>
            <TableHead>Centro de Costo</TableHead>
            <TableHead>Fecha de Recepción</TableHead>
            <TableHead>Acción</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="pastReceipts.length === 0">
            <TableCell colspan="5" class="text-center">No hay recepciones pasadas.</TableCell>
          </TableRow>
          <TableRow v-for="receipt in pastReceipts" :key="receipt.id">
            <TableCell class="font-medium">{{ receipt.invoice_number }}</TableCell>
            <TableCell>{{ receipt.provider_name }}</TableCell>
            <TableCell>{{ receipt.cost_center_name }}</TableCell>
            <TableCell>{{ new Date(receipt.receipt_date).toLocaleDateString() }}</TableCell>
            <TableCell class="flex gap-2">
              <Button as-child size="sm" variant="outline">
                <RouterLink :to="`/inventory/receipts/${receipt.id}`">
                  <Eye class="h-4 w-4"/>
                </RouterLink>
              </Button>
              <Button v-if="isAdmin" @click="openEditModal(receipt)" size="sm" variant="outline">
                  <Pencil class="h-4 w-4" />
              </Button>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Card>
  </div>
  <EditReceiptModal v-model:open="isEditModalOpen" :receipt="selectedReceipt" @receipt-updated="fetchPastReceipts" />
</template>
