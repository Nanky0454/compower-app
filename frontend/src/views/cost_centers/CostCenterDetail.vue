<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth0 } from '@auth0/auth0-vue'

// --- UI Components ---
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Badge } from '@/components/ui/badge/index.js'
import { ArrowLeft, PieChart, FileText, Truck } from 'lucide-vue-next'



// --- Configuración ---
const route = useRoute()
const router = useRouter()
const { getAccessTokenSilently } = useAuth0()
const ccId = parseInt(route.params.id)

// --- Estado ---
const isLoading = ref(true)
const costCenterData = ref(null) // Datos generales (Presupuesto)
const movements = ref([]) // Lista de movimientos (GRE/OC)

// --- Formateador de Moneda ---
const currencyFormatter = new Intl.NumberFormat('es-PE', {
  style: 'currency',
  currency: 'PEN',
})

// --- Computed para el Gráfico (Barra de Progreso) ---
const budgetPercentage = computed(() => {
  if (!costCenterData.value || !costCenterData.value.budget) return 0
  return (costCenterData.value.consumed_budget / costCenterData.value.budget) * 100
})

const progressBarColorClass = computed(() => {
  if (budgetPercentage.value >= 90) return 'bg-red-500' // Rojo
  if (budgetPercentage.value >= 70) return 'bg-yellow-500' // Amarillo
  return 'bg-green-500' // Verde
})

// --- Carga de Datos ---
onMounted(async () => {
  try {
    const token = await getAccessTokenSilently()
    
    // 1. Obtener datos GENERALES (Presupuesto y Totales)
    const resSummary = await fetch(`${import.meta.env.VITE_API_URL}/api/cost-centers/with-budget-consumption`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (resSummary.ok) {
      const allCenters = await resSummary.json()
      // Filtramos en el cliente para encontrar el actual (esto es temporal hasta tener un endpoint de "get one summary")
      costCenterData.value = allCenters.find(cc => cc.id === ccId)
    }

    // 2. OBTENER LISTA REAL DE MOVIMIENTOS
    // Llamamos al nuevo endpoint que acabamos de crear en Python
    const resMovements = await fetch(`${import.meta.env.VITE_API_URL}/api/cost-centers/${ccId}/movements`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (resMovements.ok) {
      movements.value = await resMovements.json()
    }

  } catch (e) {
    console.error(e)
  } finally {
    isLoading.value = false
  }
})

function goBack() {
  router.push('/cost-centers')
}

// Helper para formatear fecha (agrégalo en tu sección de scripts si no lo tienes así)
const dateFormatter = (dateString) => {
  if (!dateString) return '-'
  // Crea la fecha y corrige la zona horaria si es necesario, o usa split simple
  const date = new Date(dateString)
  return date.toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

</script>

<template>
  <div class="p-6 space-y-6 max-w-7xl mx-auto">
    
    <div class="flex items-center gap-4">
      <Button variant="outline" size="icon" @click="goBack">
        <ArrowLeft class="w-4 h-4" />
      </Button>
      <div>
        <h1 class="text-2xl font-bold" v-if="costCenterData">
          {{ costCenterData.code }} - {{ costCenterData.name }}
        </h1>
        <p v-else class="text-gray-500">Cargando información...</p>
      </div>
    </div>

    <div v-if="costCenterData" class="grid grid-cols-1 md:grid-cols-3 gap-6">
      
      <div class="md:col-span-2">
        <Card class="h-full flex flex-col">
          <CardHeader>
            <CardTitle>Detalle de Movimientos (GRE y OC)</CardTitle>
          </CardHeader>
          <CardContent class="flex-1">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Documento</TableHead>
                  <TableHead>Descripción</TableHead>
                  <TableHead class="text-right">Monto (S/)</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="item in movements" :key="item.id">
                  <TableCell>
                    <Badge :variant="item.type === 'GRE' ? 'secondary' : 'default'">
                      <Truck v-if="item.type === 'GRE'" class="w-3 h-3 mr-1 inline"/>
                      <FileText v-else class="w-3 h-3 mr-1 inline"/>
                      {{ item.type }}
                    </Badge>
                  </TableCell>
                  <TableCell>
                      <div class="font-medium">{{ item.doc_number }}</div>
                      <div class="text-xs text-gray-400">{{ dateFormatter(item.date) }}</div>
                  </TableCell>
                  <TableCell class="text-gray-600 text-sm">{{ item.description }}</TableCell>
                  <TableCell class="text-right font-mono">
                    {{ currencyFormatter.format(item.amount) }}
                  </TableCell>
                </TableRow>
                <TableRow v-if="movements.length === 0">
                  <TableCell colspan="4" class="text-center py-8 text-gray-500">
                    No hay movimientos registrados.
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <div class="space-y-6">
        
        <Card>
          <CardHeader>
            <CardTitle class="text-center text-sm uppercase text-gray-500">Ejecución Presupuestal</CardTitle>
          </CardHeader>
          <CardContent>
            <div class="h-6 relative bg-gray-200 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-500 ease-out"
                :class="progressBarColorClass"
                :style="{ width: budgetPercentage + '%' }"
              ></div>
            </div>
            <div class="text-center mt-2 text-sm font-medium">
              {{ budgetPercentage.toFixed(2) }}% del Presupuesto Consumido
            </div>
            <div class="text-center mt-4 text-sm font-medium">
              Presupuesto Total: {{ currencyFormatter.format(costCenterData.budget) }}
            </div>
          </CardContent>
        </Card>

        <Card class="bg-slate-900 text-white border-slate-800">
          <CardHeader class="pb-2">
            <CardTitle class="text-sm font-normal text-slate-400">Total Gastado / Consumido</CardTitle>
          </CardHeader>
          <CardContent>
            <div class="text-4xl font-bold">
              {{ currencyFormatter.format(costCenterData.consumed_budget) }}
            </div>
            <p class="text-xs text-slate-400 mt-1">
              Incluye Salidas de Almacén y Compras Directas.
            </p>
          </CardContent>
        </Card>

      </div>

    </div>
  </div>
</template>

<style scoped>
/* Ajustes opcionales */
</style>