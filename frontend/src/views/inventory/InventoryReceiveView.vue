<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Loader2, Check, ChevronsUpDown, Plus } from 'lucide-vue-next'

// Combobox
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command/index.js'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover/index.js'
import ProductFormModal from '@/components/ProductFormModal.vue'

// Hooks
const route = useRoute()
const router = useRouter()
const { getAccessTokenSilently } = useAuth0()

// Refs de Estado
const order = ref(null)
const warehouses = ref([])
const productCatalog = ref([])
const categories = ref([])
const isLoading = ref(true)
const error = ref(null)
const isSubmitting = ref(false)

// Refs del Formulario
const selectedWarehouse = ref(null)
const receptionItems = ref([])

const isProductModalOpen = ref(false)
const currentReceivingItem = ref(null)

async function fetchProductCatalog() {
  try {
    const token = await getAccessTokenSilently()
    const prodRes = await fetch(`${import.meta.env.VITE_API_URL}/api/products`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    productCatalog.value = await prodRes.json()
  } catch (e) {
    console.error("Error cargando catálogo de productos:", e)
  }
}

// Cargar todos los datos necesarios
onMounted(async () => {
  const orderId = route.params.id
  try {
    const token = await getAccessTokenSilently()

    const orderRes = await fetch(`${import.meta.env.VITE_API_URL}/api/purchases/${orderId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!orderRes.ok) throw new Error('No se pudo cargar la orden.')
    order.value = await orderRes.json()

    const whRes = await fetch(`${import.meta.env.VITE_API_URL}/api/inventory/warehouses`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    warehouses.value = await whRes.json()

    await fetchProductCatalog()

    const catRes = await fetch(`${import.meta.env.VITE_API_URL}/api/categories`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    categories.value = await catRes.json()

    // --- CAMBIO: Añadir 'location' al inicializar los items ---
    receptionItems.value = order.value.items.map(item => ({
      po_item_id: item.id,
      invoice_detail_text: item.invoice_detail_text,
      quantity_ordered: item.quantity,
      product_id: null,
      quantity_received: item.quantity,
      location: '', // <-- Campo añadido
    }))

  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})

function handleProductSelect(item, selectedProductId) {
  item.product_id = selectedProductId
  // --- CAMBIO: Pre-rellenar ubicación si el producto ya la tiene ---
  const product = productCatalog.value.find(p => p.id === selectedProductId)
  if (product && product.location) {
    item.location = product.location
  }
}

function openProductModal(item) {
  currentReceivingItem.value = item
  isProductModalOpen.value = true
}

async function onProductCreated(newProduct) {
  await fetchProductCatalog()
  if (currentReceivingItem.value) {
    currentReceivingItem.value.product_id = newProduct.id
  }
  currentReceivingItem.value = null
}

async function handleSubmitReception() {
  isSubmitting.value = true
  error.value = null

  if (!selectedWarehouse.value) {
    error.value = "Debes seleccionar un almacén de destino."
    isSubmitting.value = false
    return
  }
  for (const item of receptionItems.value) {
    if (!item.product_id) {
      error.value = `Debes asignar un producto del catálogo al item "${item.invoice_detail_text}".`
      isSubmitting.value = false
      return
    }
  }

  try {
    const token = await getAccessTokenSilently()
    // --- CAMBIO: Incluir 'location' en el payload ---
    const payload = {
      warehouse_id: selectedWarehouse.value,
      order_id: order.value.id,
      items: receptionItems.value.map(item => ({
        po_item_id: item.po_item_id,
        product_id: item.product_id,
        quantity_received: item.quantity_received,
        location: item.location, // <-- Campo añadido
      }))
    }

    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/inventory/receive`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      const errData = await response.json()
      throw new Error(errData.error || 'Error al guardar la recepción.')
    }

    router.push('/inventory')

  } catch (e) {
    error.value = e.message
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div>
    <div v-if="isLoading">Cargando datos de recepción...</div>
    <div v-else-if="error" class="text-red-500 p-4 bg-red-50 rounded-md">{{ error }}</div>

    <div v-else-if="order" class="space-y-6">
      <h1 class="text-3xl font-bold">
        Recepcionar Orden: {{ order.document_number }}
      </h1>

      <Card>
        <CardHeader>
          <CardTitle>Datos de la Orden</CardTitle>
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
            <Label for="warehouse" class="text-sm font-medium text-gray-700">Almacén de Destino</Label>
            <Select v-model="selectedWarehouse">
              <SelectTrigger id="warehouse" class="mt-1">
                <SelectValue placeholder="Selecciona un almacén..." />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem v-for="wh in warehouses" :key="wh.id" :value="wh.id">
                    {{ wh.name }} ({{ wh.location }})
                  </SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Mapear Items de Factura a Catálogo</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-[25%]">Detalle (Factura)</TableHead>
                <TableHead class="w-[25%]">Producto (Catálogo)</TableHead>
                <TableHead>Cant. Pedida</TableHead>
                <TableHead>Cant. a Recibir</TableHead>
                <!-- CAMBIO: Nueva columna para Ubicación -->
                <TableHead>Ubicación</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="item in receptionItems" :key="item.po_item_id">

                <TableCell class="font-medium whitespace-normal min-w-[200px]">
                  {{ item.invoice_detail_text }}
                </TableCell>

                <TableCell>
                  <Popover>
                    <PopoverTrigger as-child>
                      <Button
                        variant="outline"
                        role="combobox"
                        class="w-full justify-between h-auto whitespace-normal text-left py-2"
                      >
                        {{ item.product_id ? productCatalog.find(p => p.id === item.product_id)?.name : 'Asignar producto...' }}
                        <ChevronsUpDown class="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      </Button>
                    </PopoverTrigger>

                    <PopoverContent class="p-0">
                      <Command>
                        <CommandInput placeholder="Buscar producto..." />
                        <CommandEmpty>
                          <span>No se encontró.</span>
                          <Button variant="ghost" class="h-8 mt-2 w-full" @click="openProductModal(item)">
                            <Plus class="h-4 w-4 mr-2" />
                            Crear Nuevo Producto
                          </Button>
                        </CommandEmpty>
                        <CommandGroup>
                          <CommandList>
                            <CommandItem
                              v-for="product in productCatalog"
                              :key="product.id"
                              :value="product.name"
                              @select="() => handleProductSelect(item, product.id)"
                            >
                              <Check :class="['mr-2 h-4 w-4', item.product_id === product.id ? 'opacity-100' : 'opacity-0']" />
                              {{ product.name }} ({{ product.sku }})
                            </CommandItem>
                          </CommandList>
                        </CommandGroup>
                      </Command>
                    </PopoverContent>
                  </Popover>
                </TableCell>

                <TableCell>{{ item.quantity_ordered }}</TableCell>
                <TableCell>
                  <Input v-model="item.quantity_received" type="number" min="0" class="w-24" />
                </TableCell>
                <TableCell>
                  <Input v-model="item.location" type="text" class="w-24" placeholder="Ej: A1-B2" />
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>


      <div class="flex justify-end">
        <Button @click="handleSubmitReception" :disabled="isSubmitting">
          <Loader2 v-if="isSubmitting" class="h-4 w-4 animate-spin mr-2" />
          Procesar Recepción y Mover a Stock
        </Button>
      </div>
    </div>
    <ProductFormModal
      :open="isProductModalOpen"
      :categories="categories"
      @update:open="isProductModalOpen = $event"
      @productCreated="onProductCreated"
    />
  </div>

</template>
