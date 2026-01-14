<script setup>
import { ref, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { debounce } from 'lodash-es'

// Importar componentes de UI
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Search, X, Loader2 } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()

// --- State ---
const searchQuery = ref('')
const searchResults = ref([])
const isSearching = ref(false)
const printQueue = ref([])
const isGenerating = ref(false)

// --- API Calls ---
const searchProducts = async (query) => {
  if (query.length < 2) {
    searchResults.value = []
    return
  }
  isSearching.value = true
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/products/search?q=${query}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) throw new Error('Error al buscar productos')
    const data = await response.json()
    // Filtrar resultados para no mostrar los que ya están en la cola
    const queueIds = printQueue.value.map(item => item.id)
    searchResults.value = data.filter(product => !queueIds.includes(product.id))
  } catch (error) {
    console.error(error)
    // Aquí podrías mostrar una notificación de error
  } finally {
    isSearching.value = false
  }
}

const debouncedSearch = debounce(searchProducts, 300)

watch(searchQuery, (newQuery) => {
  debouncedSearch(newQuery)
})

// --- Queue Management ---
const addToQueue = (product) => {
  // Asegurarse de no añadir duplicados
  if (printQueue.value.some(item => item.id === product.id)) return

  printQueue.value.push({ ...product, quantity: 1 })
  searchQuery.value = '' // Limpiar búsqueda
  searchResults.value = [] // Limpiar resultados
}

const removeFromQueue = (productId) => {
  printQueue.value = printQueue.value.filter(item => item.id !== productId)
}

const updateQuantity = (productId, newQuantity) => {
  const item = printQueue.value.find(item => item.id === productId)
  if (item) {
    const quantity = parseInt(newQuantity, 10)
    item.quantity = quantity > 0 ? quantity : 1
  }
}

// --- Label Generation ---
const generateLabels = async () => {
  if (printQueue.value.length === 0) {
    alert('No hay productos en la cola para generar etiquetas.')
    return
  }

  isGenerating.value = true
  try {
    const token = await getAccessTokenSilently()
    // --- FIX: Mapear las claves del producto a las esperadas por el backend ---
    const payload = {
      products: printQueue.value.map(item => ({
        product_sku: item.sku,
        product_name: item.name,
        quantity: item.quantity
      }))
    }

    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/inventory/generate-labels`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Error al generar el PDF de etiquetas.')
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    window.open(url, '_blank')
    window.URL.revokeObjectURL(url)

    // Opcional: limpiar la cola después de generar
    printQueue.value = []

  } catch (e) {
    alert(e.message)
  } finally {
    isGenerating.value = false
  }
}
</script>

<template>
  <DialogContent class="sm:max-w-6xl w-[95vw] h-[80vh] flex flex-col p-6">
    <DialogHeader class="mb-4"> <DialogTitle>Generador de Etiquetas</DialogTitle>
      <DialogDescription>
        Busca productos por nombre o SKU, añádelos a la lista y especifica la cantidad de etiquetas.
      </DialogDescription>
    </DialogHeader>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 flex-grow overflow-hidden min-h-0">

      <div class="flex flex-col gap-4 h-full min-h-0"> <div class="relative flex-shrink-0"> <Input
            v-model="searchQuery"
            placeholder="Buscar por SKU o nombre..."
            class="pl-10"
          />
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        </div>

        <div class="flex-grow border rounded-md overflow-y-auto relative">
          <div v-if="isSearching" class="flex items-center justify-center h-full">
            <Loader2 class="h-8 w-8 animate-spin text-primary" />
          </div>
          <ul v-else-if="searchResults.length > 0" class="divide-y">
            <li
              v-for="product in searchResults"
              :key="product.id"
              class="p-3 flex justify-between items-center hover:bg-muted/50"
            >
              <div>
                <p class="font-semibold">{{ product.name }}</p>
                <p class="text-sm text-muted-foreground">SKU: {{ product.sku }}</p>
              </div>
              <Button size="sm" variant="secondary" @click="addToQueue(product)">
                Añadir
              </Button>
            </li>
          </ul>
          <div v-else-if="searchQuery" class="flex items-center justify-center h-full text-muted-foreground">
            No se encontraron productos.
          </div>
          <div v-else class="flex items-center justify-center h-full text-muted-foreground">
            Escribe para buscar productos.
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-4 h-full min-h-0">
        <h3 class="text-lg font-semibold flex-shrink-0">Cola de Impresión ({{ printQueue.length }})</h3>

        <Card class="flex-grow overflow-hidden flex flex-col">
          <CardContent class="p-0 flex-grow overflow-y-auto"> <Table>
              <TableHeader class="sticky top-0 bg-background z-10 shadow-sm"> <TableRow>
                  <TableHead>Producto</TableHead>
                  <TableHead class="w-[100px] text-center">Cant.</TableHead>
                  <TableHead class="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <template v-if="printQueue.length > 0">
                  <TableRow v-for="item in printQueue" :key="item.id">
                    <TableCell class="py-2">
                      <div class="font-medium line-clamp-2">{{ item.name }}</div>
                      <div class="text-xs text-muted-foreground">SKU: {{ item.sku }}</div>
                    </TableCell>
                    <TableCell class="py-2 text-center">
                      <Input
                        type="number"
                        min="1"
                        class="w-16 text-center h-8 mx-auto"
                        :model-value="item.quantity"
                        @update:model-value="updateQuantity(item.id, $event)"
                      />
                    </TableCell>
                    <TableCell class="py-2 text-right">
                      <Button variant="ghost" size="icon" class="h-8 w-8 text-red-500 hover:text-red-700" @click="removeFromQueue(item.id)">
                        <X class="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                </template>
                <template v-else>
                  <TableRow>
                    <TableCell colspan="3" class="h-32 text-center text-muted-foreground">
                      La cola está vacía.
                    </TableCell>
                  </TableRow>
                </template>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>

    <DialogFooter class="mt-4">
      <Button
        @click="generateLabels"
        class="w-full sm:w-auto"
        :disabled="isGenerating || printQueue.length === 0"
      >
        <Loader2 v-if="isGenerating" class="mr-2 h-4 w-4 animate-spin" />
        Generar {{ printQueue.length }} Etiqueta(s)
      </Button>
    </DialogFooter>
  </DialogContent>
</template>
