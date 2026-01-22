<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
// Componentes UI
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Badge } from '@/components/ui/badge/index.js'

// Iconos
import { Download, Search, Loader2, Printer, FileText, Layers } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()

// --- ESTADO GENERAL ---
const activeTab = ref('stock') // 'stock' | 'costos'

// Fechas por defecto
const now = new Date()
const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0]
const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0]


// =========================================================
// LÓGICA TAB 1: REPORTE DE STOCK (Tu código original)
// =========================================================
const warehouses = ref([])
const stockReportData = ref([])
const isLoadingStock = ref(false)

const stockFilters = ref({
    start_date: firstDay,
    end_date: lastDay,
    warehouse_id: 'all'
})

// Cargar almacenes al inicio
onMounted(async () => {
    try {
        const token = await getAccessTokenSilently()
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/warehouses`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        if (response.ok) {
            warehouses.value = await response.json()
        }
    } catch (e) {
        console.error("Error cargando almacenes:", e)
    }
})

async function generateStockReport(format = 'json') {
    isLoadingStock.value = true
    try {
        const token = await getAccessTokenSilently()

        const paramsToSend = { ...stockFilters.value, format: format }
        if (paramsToSend.warehouse_id === 'all') delete paramsToSend.warehouse_id

        const params = new URLSearchParams(paramsToSend)
        const url = `${import.meta.env.VITE_API_URL}/api/reports/stock-transfers?${params.toString()}`

        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        })

        if (!response.ok) throw new Error('Error generando reporte')

        if (format === 'json') {
            stockReportData.value = await response.json()
        } else {
            const blob = await response.blob()
            const urlBlob = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = urlBlob
            a.download = `Stock_${stockFilters.value.start_date}_al_${stockFilters.value.end_date}.pdf`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
        }

    } catch (e) {
        console.error(e)
        alert(e.message)
    } finally {
        isLoadingStock.value = false
    }
}


// =========================================================
// LÓGICA TAB 2: REPORTE DE COSTOS (Nuevo requerimiento)
// =========================================================
const costReportData = ref([])
const isLoadingCost = ref(false)
const costFilters = ref({
    start_date: firstDay,
    end_date: lastDay
})

async function generateCostReport(format = 'json') {
  isLoadingCost.value = true
  try {
    const token = await getAccessTokenSilently()
    const params = new URLSearchParams()

    // Parámetros básicos
    if (costFilters.value.start_date) params.append('start_date', costFilters.value.start_date)
    if (costFilters.value.end_date) params.append('end_date', costFilters.value.end_date)

    // Parámetro de formato ('json' o 'pdf')
    params.append('format', format)

    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/reports/gre-by-cost-center?${params.toString()}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (!response.ok) throw new Error('Error generando el reporte')

    if (format === 'json') {
        // Carga normal en pantalla
        costReportData.value = await response.json()
    } else {
        // Descarga de PDF
        const blob = await response.blob()
        const urlBlob = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = urlBlob
        a.download = `Costos_Proyecto_${costFilters.value.start_date}_al_${costFilters.value.end_date}.pdf`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
    }

  } catch (e) {
    console.error(e)
    alert("Error: " + e.message)
  } finally {
    isLoadingCost.value = false
  }
}

// --- Helpers para Cálculos en el Frontend ---
function formatCurrency(val) {
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(val || 0)
}

function getItemSubtotal(item) {
  // Asumimos que el backend trae 'unit_price' (o 'cost') y 'cantidad'
  const price = parseFloat(item.unit_price || item.cost || 0)
  const qty = parseFloat(item.cantidad || 0)
  return price * qty
}

function getGuideTotal(gre) {
  if (!gre.items) return 0
  return gre.items.reduce((acc, item) => acc + getItemSubtotal(item), 0)
}

function getCCTotal(cc) {
  if (!cc.gres) return 0
  return cc.gres.reduce((acc, gre) => acc + getGuideTotal(gre), 0)
}
</script>

<template>
    <div class="space-y-6">

        <div class="flex justify-between items-center">
            <h1 class="text-2xl font-bold tracking-tight">Reportes de Almacén</h1>
        </div>

        <div class="flex space-x-1 border-b pb-1">
            <Button
                :variant="activeTab === 'stock' ? 'secondary' : 'ghost'"
                @click="activeTab = 'stock'"
                class="rounded-none border-b-2"
                :class="activeTab === 'stock' ? 'border-primary bg-secondary' : 'border-transparent'"
            >
                <Layers class="w-4 h-4 mr-2"/> Movimientos (Kardex)
            </Button>
            <Button
                :variant="activeTab === 'costos' ? 'secondary' : 'ghost'"
                @click="activeTab = 'costos'"
                class="rounded-none border-b-2"
                :class="activeTab === 'costos' ? 'border-primary bg-secondary' : 'border-transparent'"
            >
                <FileText class="w-4 h-4 mr-2"/> Costos por Proyecto
            </Button>
        </div>

        <div v-if="activeTab === 'stock'" class="space-y-4 animate-in fade-in">
            <Card class="p-4 bg-gray-50">
                <div class="flex flex-wrap gap-4 items-end">
                    <div class="w-64">
                        <label class="text-xs font-bold text-gray-500 mb-1 block">Almacén</label>
                        <Select v-model="stockFilters.warehouse_id">
                            <SelectTrigger class="bg-white">
                                <SelectValue placeholder="Todos los almacenes" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="all">Todos los almacenes</SelectItem>
                                <SelectItem v-for="wh in warehouses" :key="wh.id" :value="wh.id.toString()">
                                    {{ wh.name }}
                                </SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div>
                        <label class="text-xs font-bold text-gray-500 mb-1 block">Fecha Inicio</label>
                        <Input type="date" v-model="stockFilters.start_date" class="bg-white" />
                    </div>
                    <div>
                        <label class="text-xs font-bold text-gray-500 mb-1 block">Fecha Fin</label>
                        <Input type="date" v-model="stockFilters.end_date" class="bg-white" />
                    </div>

                    <div class="flex gap-2">
                        <Button @click="generateStockReport('json')" :disabled="isLoadingStock">
                            <Loader2 v-if="isLoadingStock" class="mr-2 h-4 w-4 animate-spin" />
                            <Search v-else class="mr-2 h-4 w-4" /> Consultar
                        </Button>
                        <Button variant="outline" @click="generateStockReport('pdf')" :disabled="isLoadingStock">
                            <Download class="mr-2 h-4 w-4" /> PDF
                        </Button>
                    </div>
                </div>
            </Card>

            <Card v-if="stockReportData.length > 0">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Código</TableHead>
                            <TableHead>Descripción</TableHead>
                            <TableHead>U.M.</TableHead>
                            <TableHead class="text-right">Saldo Inicial</TableHead>
                            <TableHead class="text-right text-green-600">Entradas</TableHead>
                            <TableHead class="text-right text-red-600">Salidas</TableHead>
                            <TableHead class="text-right font-bold">Stock Final</TableHead>
                            <TableHead class="text-right">Costo Prom.</TableHead>
                            <TableHead class="text-right">Importe</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        <TableRow v-for="item in stockReportData" :key="item.codigo">
                            <TableCell class="font-mono text-xs">{{ item.codigo }}</TableCell>
                            <TableCell class="whitespace-normal min-w-[200px] text-xs font-medium">
                                {{ item.descripcion }}
                            </TableCell>
                            <TableCell class="text-xs">{{ item.unidad }}</TableCell>
                            <TableCell class="text-right text-xs">{{ item.saldo_inicial }}</TableCell>
                            <TableCell class="text-right text-xs text-green-600">{{ item.entradas }}</TableCell>
                            <TableCell class="text-right text-xs text-red-600">{{ item.salidas }}</TableCell>
                            <TableCell class="text-right text-xs font-bold">{{ item.stock_final }}</TableCell>
                            <TableCell class="text-right text-xs">{{ Number(item.costo_prom).toFixed(2) }}</TableCell>
                            <TableCell class="text-right text-xs font-bold">{{ Number(item.importe).toFixed(2) }}</TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
            </Card>
            <div v-else-if="!isLoadingStock" class="text-center py-10 text-gray-400 border-2 border-dashed rounded-lg">
                Seleccione los filtros y presione Consultar para ver los movimientos.
            </div>
        </div>

        <div v-if="activeTab === 'costos'" class="space-y-6 animate-in fade-in">

            <Card class="p-4 bg-gray-50">
                <div class="flex flex-wrap gap-4 items-end">
                    <div>
                        <label class="text-xs font-bold text-gray-500 mb-1 block">Fecha Inicio</label>
                        <Input type="date" v-model="costFilters.start_date" class="bg-white" />
                    </div>
                    <div>
                        <label class="text-xs font-bold text-gray-500 mb-1 block">Fecha Fin</label>
                        <Input type="date" v-model="costFilters.end_date" class="bg-white" />
                    </div>
                    <div class="flex gap-2">
                        <Button @click="generateCostReport('json')" :disabled="isLoadingCost">
                            <Loader2 v-if="isLoadingCost" class="mr-2 h-4 w-4 animate-spin" />
                            <Search v-else class="mr-2 h-4 w-4" /> Consultar
                        </Button>

                        <Button variant="outline" @click="generateCostReport('pdf')" :disabled="isLoadingCost" class="ml-auto">
                            <Printer class="mr-2 h-4 w-4" /> Imprimir / PDF
                        </Button>
                    </div>
                </div>
            </Card>

            <div v-if="costReportData.length > 0" class="space-y-8">
                <Card v-for="cc in costReportData" :key="cc.cost_center_id" class="overflow-hidden border-t-4 border-t-blue-600 shadow-sm">
                    <CardHeader class="bg-gray-50/50 border-b py-3 px-4">
                        <div class="flex justify-between items-center">
                            <div>
                                <CardTitle class="text-base font-bold text-gray-800 flex items-center gap-2">
                                    {{ cc.cost_center_code }}
                                </CardTitle>
                            </div>
                            <div class="text-right">
                                <span class="text-[10px] text-gray-500 uppercase font-bold tracking-wider">Total Proyecto</span>
                                <div class="text-lg font-bold text-blue-700 leading-tight">{{ formatCurrency(getCCTotal(cc)) }}</div>
                            </div>
                        </div>
                    </CardHeader>

                    <CardContent class="p-0">
                        <div v-for="gre in cc.gres" :key="gre.id" class="border-b last:border-0 p-4 hover:bg-gray-50/20">

                            <div class="flex flex-wrap justify-between items-center mb-3">
                                <div class="flex items-center gap-3">
                                    <Badge variant="secondary" class="font-mono">{{ gre.serie }}-{{ gre.numero }}</Badge>
                                    <span class="text-xs text-gray-500">{{ gre.fecha_emision }}</span>
                                    <span class="text-xs font-semibold text-gray-700">→ {{ gre.destinatario }}</span>
                                </div>
                            </div>

                            <div class="border rounded-md overflow-hidden">
                                <Table class="text-xs">
                                    <TableHeader>
                                        <TableRow class="bg-gray-100 hover:bg-gray-100 h-8">
                                            <TableHead class="h-8 pl-4">Descripción del Item</TableHead>
                                            <TableHead class="h-8 text-right w-24">Valor Unit.</TableHead>
                                            <TableHead class="h-8 text-center w-20">Cant.</TableHead>
                                            <TableHead class="h-8 text-right w-24 pr-4">Subtotal</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        <TableRow v-for="(item, i) in gre.items" :key="i" class="border-b last:border-0 h-8">
                                            <TableCell class="py-1 pl-4 font-medium">{{ item.descripcion }}</TableCell>
                                            <TableCell class="py-1 text-right text-gray-500">
                                                {{ formatCurrency(item.unit_price || item.cost || 0) }}
                                            </TableCell>
                                            <TableCell class="py-1 text-center font-mono bg-gray-50/50">{{ item.cantidad }}</TableCell>
                                            <TableCell class="py-1 text-right font-bold text-gray-700 pr-4">
                                                {{ formatCurrency(getItemSubtotal(item)) }}
                                            </TableCell>
                                        </TableRow>
                                        <TableRow class="bg-gray-50 h-8">
                                            <TableCell colspan="3" class="text-right font-bold text-gray-600 py-1">Total Guía:</TableCell>
                                            <TableCell class="text-right font-bold text-gray-900 py-1 pr-4">{{ formatCurrency(getGuideTotal(gre)) }}</TableCell>
                                        </TableRow>
                                    </TableBody>
                                </Table>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <div v-else-if="!isLoadingCost" class="text-center py-10 text-gray-400 border-2 border-dashed rounded-lg">
                No hay información de costos para el rango de fechas seleccionado.
            </div>
        </div>

    </div>
</template>