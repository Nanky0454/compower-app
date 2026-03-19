<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Input } from '@/components/ui/input/index.js'
import { useToast } from '@/components/ui/toast/use-toast'
import { Loader2, ArrowLeft } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const { getAccessTokenSilently } = useAuth0()
const { toast } = useToast()
const transfer = ref(null)
const isLoading = ref(true)
const isSubmitting = ref(false)
const error = ref(null)

// Objeto para v-model de las cantidades a devolver
const returnQuantities = ref({})

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
    // Inicializar las cantidades a devolver
    transfer.value.items.forEach(item => {
      returnQuantities.value[item.id] = ''
    })
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})

const itemsWithReturnDetails = computed(() => {
  if (!transfer.value) return []
  return transfer.value.items.map(item => {
    const sent = item.quantity
    const returned = item.returned_quantity
    const availableToReturn = sent - returned
    return {
      ...item,
      sent,
      returned,
      availableToReturn
    }
  })
})

async function handleSubmitReturn() {
  isSubmitting.value = true
  try {
    const token = await getAccessTokenSilently()
    const transferId = route.params.id

    const itemsToSubmit = Object.entries(returnQuantities.value)
      .map(([id, quantity]) => ({
        id: parseInt(id),
        return_quantity: parseFloat(quantity || 0)
      }))
      .filter(item => item.return_quantity > 0)

    if (itemsToSubmit.length === 0) {
      toast({ title: "Atención", description: "No se ha especificado ninguna cantidad para devolver.", variant: "default" })
      return
    }

    // Validar que la cantidad a devolver no exceda la disponible
    for (const item of itemsToSubmit) {
      const transferItem = itemsWithReturnDetails.value.find(i => i.id === item.id)
      if (item.return_quantity > transferItem.availableToReturn) {
        toast({
          title: "Error de validación",
          description: `La cantidad a devolver para ${transferItem.product_name} excede la cantidad disponible.`,
          variant: "destructive"
        })
        return
      }
    }

    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/transfers/${transferId}/return`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ items: itemsToSubmit })
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.error || 'Error al procesar la devolución.')
    }

    toast({ title: "Éxito", description: "La devolución se ha procesado correctamente." })
    router.push('/inventory/transfers')

  } catch (e) {
    toast({ title: "Error", description: e.message, variant: "destructive" })
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div>
    <div class="mb-4">
        <Button variant="outline" @click="router.go(-1)">
            <ArrowLeft class="mr-2 h-4 w-4" />
            Regresar
        </Button>
    </div>
    <div v-if="isLoading" class="text-center p-8"><Loader2 class="animate-spin" /></div>
    <div v-else-if="error" class="text-red-500 p-4 bg-red-50 rounded-md">{{ error }}</div>

    <div v-else-if="transfer" class="space-y-6">
      <h1 class="text-3xl font-bold">Devolver Stock de Transferencia #{{ transfer.id }}</h1>

      <Card>
        <CardHeader>
          <CardTitle>Información General</CardTitle>
        </CardHeader>
        <CardContent class="grid grid-cols-1 md:grid-cols-4 gap-4">
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
          <div v-if="transfer.cost_center">
            <p class="text-sm font-medium text-gray-500">Centro de Costo</p>
            <p class="font-semibold">{{ transfer.cost_center }}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Productos para Devolver</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Producto</TableHead>
                <TableHead class="text-right">Enviado</TableHead>
                <TableHead class="text-right">Devuelto Previamente</TableHead>
                <TableHead class="text-right">Disponible</TableHead>
                <TableHead class="w-[150px] text-right">Cantidad a Devolver</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="item in itemsWithReturnDetails" :key="item.id">
                <TableCell>{{ item.product_name }} <span class="text-gray-500 text-xs">{{ item.product_sku }}</span></TableCell>
                <TableCell class="text-right">{{ item.sent }}</TableCell>
                <TableCell class="text-right">{{ item.returned }}</TableCell>
                <TableCell class="text-right font-bold">{{ item.availableToReturn }}</TableCell>
                <TableCell class="text-right">
                  <Input
                    type="number"
                    v-model="returnQuantities[item.id]"
                    class="text-right"
                    placeholder="0"
                    min="0"
                    :max="item.availableToReturn"
                  />
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
        <CardFooter class="flex justify-end gap-2">
          <Button @click="handleSubmitReturn" :disabled="isSubmitting">
            <Loader2 v-if="isSubmitting" class="mr-2 h-4 w-4 animate-spin" />
            Confirmar Devolución
          </Button>
        </CardFooter>
      </Card>
    </div>
  </div>
</template>

