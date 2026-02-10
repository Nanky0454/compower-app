<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableFooter } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Pencil } from 'lucide-vue-next'
import EditReceiptItemModal from './components/EditReceiptItemModal.vue'

const route = useRoute()
const { getAccessTokenSilently, user } = useAuth0()
const FLASK_API_URL = `${import.meta.env.VITE_API_URL}/api`
const AUTH0_NAMESPACE = 'https://appcompower.com' // Define the namespace here

const receiptDetails = ref(null)
const isLoading = ref(true)
const error = ref(null)

// Edit Item Modal State
const isEditItemModalOpen = ref(false)
const selectedItemForEdit = ref(null)

const currencyFormatter = new Intl.NumberFormat('es-PE', {
  style: 'currency',
  currency: 'PEN',
});

const grandTotal = computed(() => {
  if (!receiptDetails.value || !receiptDetails.value.items) return 0
  return receiptDetails.value.items.reduce((acc, item) => acc + (item.quantity * item.unit_price), 0)
})

const isAdmin = computed(() => {
  const rolesKey = AUTH0_NAMESPACE + '/roles';
  if (user.value && user.value[rolesKey] && Array.isArray(user.value[rolesKey])) {
    const userRoles = user.value[rolesKey].map(role => role.toLowerCase());
    return userRoles.includes('admin');
  }
  return false;
})

async function fetchReceiptDetails() {
  const receiptId = route.params.id
  if (!receiptId) {
    error.value = 'ID de recepción no proporcionado.'
    isLoading.value = false
    return
  }

  isLoading.value = true
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${FLASK_API_URL}/inventory/receipts/${receiptId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('No se pudo cargar el detalle de la recepción.')
    receiptDetails.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}

function openEditItemModal(item) {
  selectedItemForEdit.value = { ...item }
  isEditItemModalOpen.value = true
}

async function handleItemUpdate(updatedItem) {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${FLASK_API_URL}/inventory/receipt-items/${updatedItem.id}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        quantity: updatedItem.quantity,
        unit_price: updatedItem.unit_price
      })
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Error al actualizar el ítem.')
    }

    isEditItemModalOpen.value = false
    await fetchReceiptDetails() // Refresh data

  } catch (e) {
    console.error(e)
    alert(e.message)
  }
}

onMounted(fetchReceiptDetails)
</script>

<template>
  <div class="container mx-auto p-4">
    <h1 class="text-3xl font-bold mb-6">Detalle de Recepción</h1>

    <div v-if="isLoading" class="text-center text-lg">Cargando detalle de recepción...</div>
    <div v-else-if="error" class="text-red-500 text-center text-lg">{{ error }}</div>

    <div v-else-if="receiptDetails">
      <!-- Card para la cabecera de la recepción -->
      <Card class="mb-6">
        <CardHeader>
          <CardTitle>Información General de la Recepción</CardTitle>
          <CardDescription>Detalles principales de la recepción.</CardDescription>
        </CardHeader>
        <CardContent class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p class="font-semibold">Número de Factura:</p>
            <p>{{ receiptDetails.invoice_number }}</p>
          </div>
          <div>
            <p class="font-semibold">Proveedor:</p>
            <p>{{ receiptDetails.provider_name }}</p>
          </div>
          <div>
            <p class="font-semibold">Centro de Costo:</p>
            <p>{{ receiptDetails.cost_center_name }}</p>
          </div>
          <div>
            <p class="font-semibold">Fecha de Recepción:</p>
            <p>{{ new Date(receiptDetails.receipt_date).toLocaleDateString() }}</p>
          </div>
          <div>
            <p class="font-semibold">Almacén:</p>
            <p>{{ receiptDetails.warehouse_name }}</p>
          </div>
        </CardContent>
      </Card>

      <!-- Card para los ítems recepcionados -->
      <Card>
        <CardHeader>
          <CardTitle>Ítems Recepcionados</CardTitle>
          <CardDescription>Lista de productos incluidos en esta recepción.</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>SKU</TableHead>
                <TableHead>Producto</TableHead>
                <TableHead class="text-right">Cantidad</TableHead>
                <TableHead class="text-right">P. Unitario</TableHead>
                <TableHead class="text-right">Subtotal</TableHead>
                <TableHead>Ubicación</TableHead>
                <TableHead v-if="isAdmin" >Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-if="receiptDetails.items.length === 0">
                <TableCell colspan="7" class="text-center">No hay ítems en esta recepción.</TableCell>
              </TableRow>
              <TableRow v-for="item in receiptDetails.items" :key="item.product_sku">
                <TableCell class="font-medium">{{ item.product_sku }}</TableCell>
                <TableCell>{{ item.product_name }}</TableCell>
                <TableCell class="text-right">{{ item.quantity }}</TableCell>
                <TableCell class="text-right">{{ currencyFormatter.format(item.unit_price) }}</TableCell>
                <TableCell class="text-right">{{ currencyFormatter.format(item.quantity * item.unit_price) }}</TableCell>
                <TableCell>
                  <Badge variant="secondary" v-if="item.location">{{ item.location }}</Badge>
                  <span v-else>N/A</span>
                </TableCell>
                <TableCell>
                  <Button v-if="isAdmin" @click="openEditItemModal(item)" size="sm" variant="outline">
                    <Pencil class="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell colspan="4" class="text-right font-bold">Total General</TableCell>
                <TableCell class="text-right font-bold">{{ currencyFormatter.format(grandTotal) }}</TableCell>
                <TableCell colspan="2"></TableCell>
              </TableRow>
            </TableFooter>
          </Table>
        </CardContent>
      </Card>
    </div>
     <EditReceiptItemModal
      v-model:open="isEditItemModalOpen"
      :item="selectedItemForEdit"
      @save="handleItemUpdate"
    />
  </div>
</template>

<style scoped>
/* Puedes añadir estilos específicos si es necesario */
</style>