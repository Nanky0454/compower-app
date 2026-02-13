<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { ArrowLeft, PlusCircle, CheckCircle, XCircle } from 'lucide-vue-next'
import RenderTable from '@/components/treasury/RenderTable.vue'
import RenderForm from '@/components/treasury/RenderForm.vue'
import { useToast } from '@/components/ui/toast/use-toast'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const route = useRoute()
const router = useRouter()
const { getAccessTokenSilently } = useAuth0()
const { toast } = useToast()

const allocationId = parseInt(route.params.id)
const allocation = ref(null)
const renders = ref([])
const isLoading = ref(true)
const isRenderFormOpen = ref(false)
const renderToEdit = ref(null) // For editing existing renders

// Computed properties for display
const allocationAmount = computed(() => allocation.value ? parseFloat(allocation.value.amount) : 0)
const totalRenderedAmount = computed(() => renders.value.reduce((sum, render) => sum + parseFloat(render.amount), 0))
const balance = computed(() => allocationAmount.value - totalRenderedAmount.value)
const isFinalized = computed(() => allocation.value && allocation.value.status === 'Finalizada')

const balanceClass = computed(() => {
  if (balance.value > 0) return 'text-green-500' //A favor de CP
  if (balance.value < 0) return 'text-red-500'  //A favor de trabajador
  return 'text-gray-500' // Exacto
})

const balanceText = computed(() => {
  if (balance.value > 0) return `Saldo a favor de CP: ${formatCurrency(balance.value)}`
  if (balance.value < 0) return `Saldo a favor de trabajador: ${formatCurrency(Math.abs(balance.value))}`
  return 'Balance Exacto'
})

function formatCurrency(amount, currency = 'PEN') {
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency: currency }).format(amount)
}

async function fetchAllocationDetails() {
  isLoading.value = true
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/transactions/${allocationId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.ok) {
      allocation.value = await response.json()
    } else {
      toast({
        title: 'Error',
        description: 'No se pudo cargar los detalles de la asignación.',
        variant: 'destructive'
      })
      router.push('/treasury') // Redirect if allocation not found
    }
  } catch (error) {
    console.error('Error fetching allocation:', error)
    toast({
      title: 'Error',
      description: 'Ocurrió un error al conectar con el servidor.',
      variant: 'destructive'
    })
    router.push('/treasury')
  } finally {
    isLoading.value = false
  }
}

async function fetchRenders() {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/transactions/${allocationId}/renders`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.ok) {
      renders.value = await response.json()
    } else {
      toast({
        title: 'Error',
        description: 'No se pudieron cargar las rendiciones.',
        variant: 'destructive'
      })
    }
  } catch (error) {
    console.error('Error fetching renders:', error)
    toast({
      title: 'Error',
      description: 'Ocurrió un error al conectar con el servidor para las rendiciones.',
      variant: 'destructive'
    })
  }
}

async function finalizeAllocation() {
  if (isFinalized.value) return // Already finalized

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/transactions/${allocationId}/finalize`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    })

    if (response.ok) {
      const result = await response.json()
      allocation.value.status = result.status // Update status
      toast({
        title: 'Asignación Finalizada',
        description: `Balance final: ${formatCurrency(result.final_balance)}`,
        variant: 'success'
      })
    } else {
      const errorData = await response.json()
      toast({
        title: 'Error al Finalizar',
        description: errorData.error || 'No se pudo finalizar la asignación.',
        variant: 'destructive'
      })
    }
  } catch (error) {
    console.error('Error finalizing allocation:', error)
    toast({
      title: 'Error',
      description: 'Ocurrió un error al conectar con el servidor para finalizar.',
      variant: 'destructive'
    })
  }
}

function handleRenderAdded() {
  fetchRenders()
  isRenderFormOpen.value = false
  renderToEdit.value = null
  toast({
    title: 'Rendición Guardada',
    description: 'La rendición ha sido agregada/actualizada correctamente.',
    variant: 'success'
  })
}

function handleEditRender(render) {
  renderToEdit.value = { ...render } // Clone for editing
  isRenderFormOpen.value = true
}

async function handleDeleteRender(renderId) {
  if (!confirm('¿Estás seguro de eliminar esta rendición?')) return

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/renders/${renderId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (response.ok) {
      toast({
        title: 'Rendición Eliminada',
        description: 'La rendición ha sido eliminada correctamente.',
        variant: 'success'
      })
      fetchRenders() // Refresh the list
    } else {
      const errorData = await response.json()
      toast({
        title: 'Error al Eliminar',
        description: errorData.error || 'No se pudo eliminar la rendición.',
        variant: 'destructive'
      })
    }
  } catch (error) {
    console.error('Error deleting render:', error)
    toast({
      title: 'Error',
      description: 'Ocurrió un error al conectar con el servidor para eliminar la rendición.',
      variant: 'destructive'
    })
  }
}

onMounted(() => {
  fetchAllocationDetails()
  fetchRenders()
})
</script>

<template>
  <div class="p-6 space-y-6 max-w-6xl mx-auto">
    <div v-if="isLoading" class="text-center py-10">Cargando detalles de asignación...</div>
    <div v-else-if="allocation" class="space-y-6">
      <!-- Header Section -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <Button variant="outline" size="icon" @click="router.push('/treasury')">
            <ArrowLeft class="w-4 h-4" />
          </Button>
          <div>
            <h1 class="text-2xl font-bold">Asignación {{ allocation.correlative }}</h1>
            <p class="text-sm text-muted-foreground">{{ allocation.description }}</p>
          </div>
        </div>
        <div>
            <Button @click="finalizeAllocation" :disabled="isFinalized || allocation.type !== 'EGRESO'" :variant="isFinalized ? 'secondary' : 'default'">
                <CheckCircle class="w-4 h-4 mr-2" v-if="!isFinalized" />
                <XCircle class="w-4 h-4 mr-2" v-else />
                {{ isFinalized ? 'Asignación Finalizada' : 'Terminar Asignación' }}
            </Button>
        </div>
      </div>

      <!-- Allocation Details and Summary -->
      <Card>
        <CardHeader>
          <CardTitle>Detalles de la Asignación</CardTitle>
          <CardDescription>Información general y estado de la asignación.</CardDescription>
        </CardHeader>
        <CardContent class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p class="text-sm text-muted-foreground">Fecha:</p>
            <p class="font-medium">{{ new Date(allocation.date).toLocaleDateString() }}</p>
          </div>
          <div>
            <p class="text-sm text-muted-foreground">Monto Asignado:</p>
            <p class="font-medium">{{ formatCurrency(allocationAmount, allocation.account_currency) }}</p>
          </div>
          <div>
            <p class="text-sm text-muted-foreground">Estado:</p>
            <p class="font-medium" :class="{'text-green-600': isFinalized, 'text-orange-500': !isFinalized}">{{ allocation.status }}</p>
          </div>
          <div>
            <p class="text-sm text-muted-foreground">Beneficiario:</p>
            <p class="font-medium">{{ allocation.beneficiary_name || 'N/A' }}</p>
          </div>
          <div>
            <p class="text-sm text-muted-foreground">Cuenta Bancaria:</p>
            <p class="font-medium">{{ allocation.account_alias }} ({{ allocation.account_currency }})</p>
          </div>
        </CardContent>
      </Card>

      <!-- Renders Section -->
      <div class="flex justify-between items-center">
        <h2 class="text-xl font-bold">Rendiciones</h2>
        <Button @click="isRenderFormOpen = true; renderToEdit = null" :disabled="isFinalized">
          <PlusCircle class="w-4 h-4 mr-2" />
          Nueva Rendición
        </Button>
      </div>

      <RenderTable 
        :renders="renders" 
        :is-finalized="isFinalized"
        @edit-render="handleEditRender" 
        @delete-render="handleDeleteRender" 
      />

      <!-- Balance Summary -->
      <Card class="mt-6">
        <CardHeader>
          <CardTitle>Resumen de Rendición</CardTitle>
        </CardHeader>
        <CardContent class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p class="text-sm text-muted-foreground">Monto Asignado:</p>
            <p class="font-bold">{{ formatCurrency(allocationAmount, allocation.account_currency) }}</p>
          </div>
          <div>
            <p class="text-sm text-muted-foreground">Total Rendido:</p>
            <p class="font-bold">{{ formatCurrency(totalRenderedAmount, allocation.account_currency) }}</p>
          </div>
          <div>
            <p class="text-sm text-muted-foreground">Balance:</p>
            <p class="font-bold" :class="balanceClass">{{ balanceText }}</p>
          </div>
        </CardContent>
        <CardContent v-if="isFinalized && balance !== 0" class="pt-0">
            <Alert variant="destructive">
                <AlertTitle>Asignación Finalizada con Desbalance</AlertTitle>
                <AlertDescription>
                    Esta asignación fue finalizada con un balance pendiente.
                    {{ balance > 0 ? `Se debe recuperar ${formatCurrency(balance)}` : `Hay un sobrante de ${formatCurrency(Math.abs(balance))}` }}.
                </AlertDescription>
            </Alert>
        </CardContent>
      </Card>
    </div>
    <div v-else class="text-center py-10 text-red-500">No se pudo cargar la asignación o no existe.</div>

    <RenderForm 
      v-model:isOpen="isRenderFormOpen" 
      :allocation-id="allocationId" 
      :render-to-edit="renderToEdit"
      @render-saved="handleRenderAdded"
    />
  </div>
</template>
