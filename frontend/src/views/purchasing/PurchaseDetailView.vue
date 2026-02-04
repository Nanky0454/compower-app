<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableFooter } from '@/components/ui/table'
import { ArrowLeft, FileText, Wrench, ListTree, CheckCircle2, ShieldAlert, ScrollText } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const { getAccessTokenSilently } = useAuth0()
const FLASK_API_URL = `${import.meta.env.VITE_API_URL}/api`

const order = ref(null)
const isLoading = ref(true)
const error = ref(null)

// Formateadores
const currencyFormatter = (amount, currency = 'PEN') => {
  if (isNaN(amount) || amount === null) return '-'
  return new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency: currency,
  }).format(amount)
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  // Ajuste para evitar problemas de zona horaria con fechas YYYY-MM-DD simples
  const [year, month, day] = dateString.split('T')[0].split('-')
  return `${day}/${month}/${year}`
}

// Parsear Alcance (JSON vs Texto)
const parsedScope = computed(() => {
  if (!order.value || !order.value.alcance) return null;
  try {
    if (order.value.alcance.trim().startsWith('{')) {
       return JSON.parse(order.value.alcance);
    }
  } catch (e) { console.warn("El alcance no es un JSON válido."); }
  return null;
})

// Parsear Condiciones Comerciales (Lista)
const commercialData = computed(() => {
    if (!order.value || !order.value.condiciones_comerciales) return { penalty: null, list: [] }
    const list = order.value.condiciones_comerciales
    if (Array.isArray(list) && list.length > 0) {
        return {
            penalty: list[0], // El primero es la penalidad
            list: list.slice(1) // El resto son condiciones
        }
    }
    return { penalty: null, list: [] }
})

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
  router.push('/purchases')
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
      <p class="text-sm text-gray-500" v-if="order && order.document_class">
        Tipo Tributario: <span class="font-semibold">{{ order.document_class }}</span>
      </p>
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
            <br>
            <p class="text-xs font-bold text-gray-400 uppercase">Centro de costo</p>
            <span class="text-sm font-medium">{{ order.cost_center_name }}</span>
          </div>


          <div class="space-y-1">
            <p class="text-xs font-bold text-gray-400 uppercase">Contacto</p>
            <p class="text-sm font-medium">{{ order.atencion || '-' }}</p>
            <div v-if="order.contacto && order.contacto !== 'N/A'" class="text-xs text-gray-500 mb-2">
                 {{ order.contacto }}
            </div>

            <div v-if="order.coordinador">
               <span class="text-xs font-bold text-gray-400 uppercase block">Solicitante</span>
               <span class="text-sm font-medium">{{ order.coordinador }}</span>
            </div>
            <div v-if="order.site" class="mt-1">
               <span class="text-xs font-bold text-gray-400 uppercase block">Site / Lugar</span>
               <span class="text-sm font-medium">{{ order.site }}</span>
            </div>
          </div>

          <div class="space-y-2">
            <p class="text-xs font-bold text-gray-400 uppercase">Detalles Comerciales</p>

            <div class="flex justify-between text-sm border-b pb-1 border-dashed">
              <span class="text-gray-500">F. Emisión:</span>
              <span class="font-mono opacity" >{{ formatDate(order.fecha_emision) }}</span>
            </div>

            <div class="flex justify-between text-sm border-b pb-1 border-dashed">
              <span class="text-gray-500">Moneda:</span>
              <span class="font-bold">{{ order.moneda }}</span>
            </div>

            <div v-if="order.order_type === 'OC'" class="flex justify-between text-sm border-b pb-1 border-dashed">
               <span class="text-gray-500">F. Entrega:</span>
               <span class="font-mono">{{ formatDate(order.fecha_traslado) }}</span>
            </div>
            <div v-else class="flex justify-between text-sm border-b pb-1 border-dashed">
               <span class="text-gray-500">Ejecución:</span>
               <span class="font-mono text-xs">{{ formatDate(order.fecha_inicio) }} - {{ formatDate(order.fecha_fin) }}</span>
            </div>

            <div class="text-sm pt-1">
              <span class="text-gray-500 block text-xs">Forma de Pago:</span>
              <span class="text-xs">{{ order.forma_pago || '-' }}</span>
            </div>
          </div>

          <div v-if="order.alcance && !parsedScope" class="col-span-1 md:col-span-3 bg-orange-50 p-3 rounded-md border border-orange-100 text-sm">
             <p class="text-xs font-bold text-orange-700 uppercase mb-1">Alcance / Detalle Técnico</p>
             <p class="text-gray-800 whitespace-pre-wrap break-words font-mono text-xs">{{ order.alcance }}</p>
          </div>

        </CardContent>
      </Card>

      <div v-if="parsedScope && parsedScope.groups" class="space-y-6">
          <h2 class="text-lg font-bold text-gray-800 flex items-center gap-2">
             <ListTree class="w-5 h-5 text-orange-600"/> Detalle del Servicio
          </h2>

          <div v-for="(group, gIdx) in parsedScope.groups" :key="gIdx" class="border rounded-lg overflow-hidden shadow-sm bg-white">
             <div class="bg-orange-50/80 px-4 py-2 border-b border-orange-100 flex justify-between items-center">
                <div class="font-bold text-sm text-orange-900">
                    <span class="font-mono mr-2">{{ gIdx + 1 }}.00</span> {{ group.title }}
                </div>
             </div>
             <Table>
                <TableHeader>
                   <TableRow class="bg-gray-50/30">
                      <TableHead class="w-[10%] text-center text-xs">Item</TableHead>
                      <TableHead class="w-[50%] text-xs">Descripción</TableHead>
                      <TableHead class="w-[10%] text-xs">Und</TableHead>
                      <TableHead class="w-[10%] text-right text-xs">Cant</TableHead>
                      <TableHead class="w-[10%] text-right text-xs">P. Unit</TableHead>
                      <TableHead class="w-[10%] text-right text-xs font-bold text-gray-700">Subtotal</TableHead>
                   </TableRow>
                </TableHeader>
                <TableBody>
                   <TableRow v-for="(item, iIdx) in group.items" :key="iIdx" class="hover:bg-transparent">
                      <TableCell class="text-center font-mono text-xs text-gray-500 py-2 align-top">
                          {{ gIdx + 1 }}.{{ String(iIdx + 1).padStart(2, '0') }}
                      </TableCell>
                      <TableCell class="text-sm py-2 whitespace-pre-wrap break-words min-w-[300px]">
                          {{ item.invoice_detail_text }}
                      </TableCell>
                      <TableCell class="text-xs text-gray-500 py-2 align-top">{{ item.um }}</TableCell>
                      <TableCell class="text-right text-sm py-2 align-top">{{ item.quantity }}</TableCell>
                      <TableCell class="text-right text-sm py-2 align-top">{{ currencyFormatter(item.unit_price, order.moneda) }}</TableCell>
                      <TableCell class="text-right font-medium text-sm py-2 align-top">
                          {{ currencyFormatter(item.quantity * item.unit_price, order.moneda) }}
                      </TableCell>
                   </TableRow>
                </TableBody>
             </Table>
          </div>

          <Card v-if="parsedScope.includes && parsedScope.includes.length > 0" class="border-t-4 border-t-gray-500">
             <CardHeader class="pb-2 bg-gray-50">
                <CardTitle class="text-xs font-bold uppercase text-gray-700">Incluye</CardTitle>
             </CardHeader>
             <CardContent class="pt-4 space-y-2">
                <div v-for="(inc, idx) in parsedScope.includes" :key="idx" class="flex items-start gap-2 text-sm text-gray-700">
                   <CheckCircle2 class="w-4 h-4 text-green-600 mt-0.5 shrink-0"/>
                   <span>{{ inc.text }}</span>
                </div>
             </CardContent>
          </Card>

          <div class="flex justify-end pt-4 border-t">
              <div class="text-right space-y-1">
                  <p class="text-sm text-gray-500">Total General</p>
                  <p class="text-2xl font-bold text-gray-900">{{ currencyFormatter(order.total_amount, order.moneda) }}</p>
                  <p class="text-xs text-gray-400">Incluye IGV (18%)</p>
              </div>
          </div>
      </div>

      <Card v-else>
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
                <TableCell class="font-medium whitespace-pre-wrap">{{ item.invoice_detail_text }}</TableCell>
                <TableCell class="text-xs text-gray-500">{{ item.unit_of_measure }}</TableCell>
                <TableCell class="text-right">{{ item.quantity }}</TableCell>
                <TableCell class="text-right">{{ currencyFormatter(item.unit_price, order.moneda) }}</TableCell>
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

      <Card v-if="commercialData.penalty || commercialData.list.length > 0 || order.notas_pie" class="border-l-4 border-l-blue-600 bg-slate-50">
          <CardHeader class="pb-2">
              <CardTitle class="text-sm font-bold uppercase text-gray-700 flex items-center gap-2">
                  <ScrollText class="w-4 h-4"/> Condiciones Comerciales y Legales
              </CardTitle>
          </CardHeader>
          <CardContent class="space-y-4 text-sm text-gray-700">

              <div v-if="commercialData.penalty" class="flex gap-2 items-start bg-white p-3 rounded border border-gray-200">
                  <ShieldAlert class="w-5 h-5 text-red-500 shrink-0 mt-0.5"/>
                  <div>
                      <span class="font-bold text-gray-900 block mb-1">Penalidad:</span>
                      <p>{{ commercialData.penalty }}</p>
                  </div>
              </div>

              <div v-if="commercialData.list.length > 0">
                  <h4 class="font-bold text-gray-900 mb-2">Condiciones Generales:</h4>
                  <ul class="list-disc pl-5 space-y-1">
                      <li v-for="(cond, idx) in commercialData.list" :key="idx">{{ cond }}</li>
                  </ul>
              </div>

              <div v-if="order.notas_pie" class="mt-4 pt-4 border-t border-gray-300">
                  <h4 class="font-bold text-gray-500 text-xs uppercase mb-2">Nota:</h4>
                  <div class="whitespace-pre-wrap text-xs text-gray-500 italic bg-yellow-50 p-2 rounded border border-yellow-100">
                      {{ order.notas_pie }}
                  </div>
              </div>

          </CardContent>
      </Card>

    </div>
  </div>
</template>