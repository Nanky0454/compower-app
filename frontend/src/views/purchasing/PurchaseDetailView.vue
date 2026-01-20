<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableFooter } from '@/components/ui/table'
import { ArrowLeft, Printer, Mail, Phone, FileText, Wrench } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const { getAccessTokenSilently } = useAuth0()
const FLASK_API_URL = `${import.meta.env.VITE_API_URL}/api`

const order = ref(null)
const isLoading = ref(true)
const error = ref(null)

// Formateadores
const currencyFormatter = (amount, currency = 'PEN') => {
  return new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency: currency,
  }).format(amount)
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

onMounted(async () => {
  const orderId = route.params.id
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${FLASK_API_URL}/purchases/${orderId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (!response.ok) throw new Error('No se pudo cargar la orden.')
    order.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})

function goBack() {
  router.push('/purchases') // Ajusta si tu ruta base es distinta
}
</script>

<template>
  <div class="max-w-5xl mx-auto p-6 space-y-6">

    <div class="flex items-center gap-4">
      <Button variant="outline" size="icon" @click="goBack">
        <ArrowLeft class="w-4 h-4" />
      </Button>
      <h1 class="text-2xl font-bold text-gray-900" v-if="order">
        {{ order.tipo_doc_nombre }}: {{ order.codigo }}
      </h1>
      <span v-if="isLoading">Cargando...</span>
    </div>

    <div v-if="error" class="p-4 bg-red-50 text-red-600 rounded-md border border-red-200">
      Error: {{ error }}
    </div>

    <div v-else-if="order" class="space-y-6 animate-in fade-in">

      <Card>
        <CardHeader class="pb-2 border-b bg-gray-50/50">
          <div class="flex justify-between items-center">
            <CardTitle class="text-sm font-bold uppercase text-gray-600 flex items-center gap-2">
              <Wrench v-if="order.order_type === 'OS'" class="w-4 h-4 text-orange-600"/>
              <FileText v-else class="w-4 h-4 text-blue-600"/>
              Resumen de la Orden
            </CardTitle>

            <span class="px-3 py-1 rounded-full text-xs font-bold bg-gray-900 text-white">
              {{ order.status }}
            </span>
          </div>
        </CardHeader>
        <CardContent class="pt-4 grid grid-cols-1 md:grid-cols-3 gap-6">

          <div class="space-y-1">
            <p class="text-xs font-bold text-gray-400 uppercase">Proveedor</p>
            <p class="font-semibold text-gray-900">{{ order.provider_name }}</p>
            <p class="text-xs text-gray-500">RUC: {{ order.ruc }}</p>
            <p class="text-xs text-gray-500">{{ order.direccion }}</p>
          </div>

          <div class="space-y-1">
            <p class="text-xs font-bold text-gray-400 uppercase">Atención / Contacto</p>
            <p class="text-sm font-medium">{{ order.atencion || '-' }}</p>
            <div v-if="order.contacto && order.contacto !== 'N/A'" class="flex items-center gap-2 text-sm text-gray-600 mt-1">
               <span class="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs border border-blue-100">
                 {{ order.contacto }}
               </span>
            </div>
          </div>

          <div class="space-y-1">
            <p class="text-xs font-bold text-gray-400 uppercase">Detalles</p>
            <div class="flex justify-between text-sm">
              <span class="text-gray-500">Fecha Emisión:</span>
              <span>{{ formatDate(order.fecha_emision) }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-gray-500">Moneda:</span>
              <span>{{ order.moneda }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-gray-500">Pago:</span>
              <span>{{ order.forma_pago || '-' }}</span>
            </div>
          </div>

          <div v-if="order.alcance" class="col-span-1 md:col-span-3 bg-orange-50 p-3 rounded-md border border-orange-100 text-sm">
             <p class="text-xs font-bold text-orange-700 uppercase mb-1">Alcance / Detalle Técnico</p>
             <p class="text-gray-800 whitespace-pre-line">{{ order.alcance }}</p>
          </div>

        </CardContent>
      </Card>

      <Card>
        <CardHeader class="pb-2 border-b bg-gray-50/50">
          <CardTitle class="text-sm font-bold uppercase text-gray-600">Items Incluidos</CardTitle>
        </CardHeader>
        <CardContent class="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Descripción</TableHead>
                <TableHead>UM</TableHead>
                <TableHead class="text-right">Cant</TableHead>
                <TableHead class="text-right">P. Unit</TableHead>
                <TableHead class="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="item in order.items" :key="item.id">
                <TableCell class="font-medium">{{ item.descripcion }}</TableCell>
                <TableCell class="text-xs text-gray-500">{{ item.unidad }}</TableCell>
                <TableCell class="text-right">{{ item.cant }}</TableCell>
                <TableCell class="text-right">{{ currencyFormatter(item.pu, order.moneda) }}</TableCell>
                <TableCell class="text-right font-medium">
                  {{ currencyFormatter(item.total_line, order.moneda) }}
                </TableCell>
              </TableRow>
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell colspan="4" class="text-right font-bold text-base">Total General</TableCell>
                <TableCell class="text-right font-bold text-base text-gray-900">
                  {{ currencyFormatter(order.total_amount, order.moneda) }}
                </TableCell>
              </TableRow>
            </TableFooter>
          </Table>
        </CardContent>
      </Card>

    </div>
  </div>
</template>