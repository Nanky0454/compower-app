<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
// Componentes UI
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Badge } from '@/components/ui/badge/index.js'
import { Checkbox } from '@/components/ui/checkbox'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'

// Iconos
import { Download, Search, Loader2, Printer, FileText, Layers, ChevronsUpDown, X } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()

// --- ESTADO GENERAL ---
const activeTab = ref('stock') // 'stock' | 'costos' | 'detailedItem'

// Fechas por defecto
const now = new Date()
const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0]
const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0]


// =========================================================
// LÓGICA TAB 1: REPORTE DE STOCK
// =========================================================
const warehouses = ref([])
const stockReportData = ref([])
const isLoadingStock = ref(false)

const stockFilters = ref({
    start_date: firstDay,
    end_date: lastDay,
    warehouse_id: 'all'
})

// Cargar almacenes y productos al inicio
onMounted(async () => {
    // Cargar Almacenes
    try {
        const token = await getAccessTokenSilently()
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/inventory/warehouses`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        if (response.ok) {
            warehouses.value = await response.json()
        }
    } catch (e) {
        console.error("Error cargando almacenes:", e)
    }

    // Cargar Productos
    await fetchAllProducts()
})

async function generateStockReport(format = 'json') {
    isLoadingStock.value = true
    try {
        const token = await getAccessTokenSilently()

        const paramsToSend = { ...stockFilters.value, format: format }
        if (paramsToSend.warehouse_id === 'all') delete paramsToSend.warehouse_id

        const params = new URLSearchParams(paramsToSend)
        const url = `${import.meta.env.VITE_API_URL}/api/reports/stock-movement?${params.toString()}`

        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        })

        if (!response.ok) throw new Error('Error generando reporte de stock')

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
// LÓGICA TAB 2: REPORTE DE COSTOS
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

    if (costFilters.value.start_date) params.append('start_date', costFilters.value.start_date)
    if (costFilters.value.end_date) params.append('end_date', costFilters.value.end_date)
    params.append('format', format)

    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/reports/gre-by-cost-center?${params.toString()}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (!response.ok) throw new Error('Error generando el reporte de costos')

    if (format === 'json') {
        costReportData.value = await response.json()
    } else {
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

// =========================================================
// LÓGICA TAB 3: REPORTE DETALLADO POR ITEM (CORREGIDO)
// =========================================================
const allProducts = ref([])
const isLoadingDetailed = ref(false)
const detailedFilters = ref({
    start_date: firstDay,
    end_date: lastDay,
    selectedProducts: []
})
const searchTerm = ref('')

const filteredProducts = computed(() => {
    if (!searchTerm.value) return allProducts.value
    return allProducts.value.filter(p =>
        p.name.toLowerCase().includes(searchTerm.value.toLowerCase()) ||
        p.sku.toLowerCase().includes(searchTerm.value.toLowerCase())
    )
})

async function fetchAllProducts() {
    try {
        const token = await getAccessTokenSilently()
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/products/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        if (response.ok) {
            allProducts.value = await response.json()
        }
    } catch (e) {
        console.error("Error cargando productos:", e)
    }
}

// --- NUEVA LÓGICA DE SELECCIÓN ROBUSTA ---
function isProductSelected(productId) {
    // Usamos '==' para que coincida aunque uno sea string y el otro number
    return detailedFilters.value.selectedProducts.some(id => id == productId)
}

function toggleProduct(product) {
    const rawId = product.id
    const index = detailedFilters.value.selectedProducts.findIndex(id => id == rawId)

    if (index > -1) {
        detailedFilters.value.selectedProducts.splice(index, 1)
    } else {
        detailedFilters.value.selectedProducts.push(rawId)
    }
}

function removeProductFromSelection(productId) {
    const index = detailedFilters.value.selectedProducts.findIndex(id => id == productId)
    if (index > -1) {
        detailedFilters.value.selectedProducts.splice(index, 1)
    }
}

// Computed para mostrar los chips abajo
const selectedProductDetails = computed(() => {
    return allProducts.value.filter(p =>
        detailedFilters.value.selectedProducts.some(id => id == p.id)
    )
})
// -------------------------------------------

async function generateDetailedReport() {
    if (detailedFilters.value.selectedProducts.length === 0) {
        alert("Por favor, seleccione al menos un producto.")
        return
    }

    isLoadingDetailed.value = true
    try {
        const token = await getAccessTokenSilently()
        const params = new URLSearchParams({
            start_date: detailedFilters.value.start_date,
            end_date: detailedFilters.value.end_date,
            product_ids: detailedFilters.value.selectedProducts.join(',')
        })

        const url = `${import.meta.env.VITE_API_URL}/api/reports/item-movement-report?${params.toString()}`

        const response = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } })

        if (!response.ok) {
            const err = await response.json()
            throw new Error(err.error || 'Error generando el reporte detallado')
        }

        const blob = await response.blob()
        const urlBlob = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = urlBlob
        a.download = `Reporte_Detallado_Items.pdf`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)

    } catch (e) {
        console.error(e)
        alert("Error: " + e.message)
    } finally {
        isLoadingDetailed.value = false
    }
}


// --- Helpers para Cálculos en el Frontend ---
function formatCurrency(val) {
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(val || 0)
}

function getItemSubtotal(item) {
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

        <div class="flex space-x-1 border-b">
            <Button
                :variant="activeTab === 'stock' ? 'secondary' : 'ghost'"
                @click="activeTab = 'stock'"
                class="rounded-b-none border-b-2"
                :class="activeTab === 'stock' ? 'border-primary' : 'border-transparent'"
            >
                <Layers class="w-4 h-4 mr-2"/> Movimientos (Kardex)
            </Button>
            <Button
                :variant="activeTab === 'costos' ? 'secondary' : 'ghost'"
                @click="activeTab = 'costos'"
                class="rounded-b-none border-b-2"
                :class="activeTab === 'costos' ? 'border-primary' : 'border-transparent'"
            >
                <FileText class="w-4 h-4 mr-2"/> Costos por Proyecto
            </Button>
            <Button
                :variant="activeTab === 'detailedItem' ? 'secondary' : 'ghost'"
                @click="activeTab = 'detailedItem'"
                class="rounded-b-none border-b-2"
                :class="activeTab === 'detailedItem' ? 'border-primary' : 'border-transparent'"
            >
                <Printer class="w-4 h-4 mr-2"/> Reporte Detallado por Item
            </Button>
        </div>

        <div v-if="activeTab === 'stock'" class="space-y-4 animate-in fade-in">
             <Card class="p-4 bg-gray-50/50 border-dashed">
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

             <Card class="p-4 bg-gray-50/50 border-dashed">
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

        <div v-if="activeTab === 'detailedItem'" class="space-y-4 animate-in fade-in">

            <Card class="p-4 bg-gray-50/50">
                <div class="flex flex-wrap gap-4 items-end">
                    <div>
                        <label class="text-xs font-bold text-gray-500 mb-1 block">Fecha Inicio</label>
                        <Input type="date" v-model="detailedFilters.start_date" class="bg-white" />
                    </div>

                    <div>
                        <label class="text-xs font-bold text-gray-500 mb-1 block">Fecha Fin</label>
                        <Input type="date" v-model="detailedFilters.end_date" class="bg-white" />
                    </div>

                    <div class="w-96">
                        <label class="text-xs font-bold text-gray-500 mb-1 block">Agregar Productos</label>
                         <DropdownMenu>
                            <DropdownMenuTrigger as-child>
                              <Button variant="outline" class="w-full justify-between bg-white text-left font-normal">
                                <span class="truncate">
                                    {{ detailedFilters.selectedProducts.length > 0
                                        ? `${detailedFilters.selectedProducts.length} seleccionados`
                                        : 'Buscar y seleccionar...'
                                    }}
                                </span>
                                <ChevronsUpDown class="ml-2 h-4 w-4 shrink-0 opacity-50" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent class="w-96 max-h-80 overflow-y-auto" align="start">
                                <div class="p-2 sticky top-0 bg-white z-10 border-b mb-2">
                                    <Input
                                        v-model="searchTerm"
                                        placeholder="Escribe para filtrar..."
                                        class="h-8"
                                        @keydown.stop
                                    />
                                </div>

                                <DropdownMenuItem
                                    v-for="product in filteredProducts"
                                    :key="product.id"
                                    class="cursor-pointer focus:bg-gray-100"
                                    @select.prevent
                                    @click="toggleProduct(product)"
                                >
                                    <div class="flex items-center space-x-2 w-full py-1 pointer-events-none">
                                        <DropdownMenuItem
                                            v-for="product in filteredProducts"
                                            :key="product.id"
                                            class="cursor-pointer focus:bg-gray-100"
                                            @select.prevent
                                            @click="toggleProduct(product)"
                                        >
                                            <div class="flex items-center space-x-2 w-full py-1 pointer-events-none">
                                                <Checkbox
                                                    :id="'prod-' + product.id"
                                                    :checked="isProductSelected(product.id)"
                                                    :model-value="isProductSelected(product.id)"
                                                    class="pointer-events-none"
                                                />
                                                <label :for="'prod-' + product.id" class="text-xs w-full cursor-pointer">
                                                    <span class="font-bold text-blue-600 block">{{ product.sku }}</span>
                                                    <span class="text-gray-700 leading-tight">{{ product.name }}</span>
                                                </label>
                                            </div>
                                        </DropdownMenuItem>
                                        <label :for="'prod-' + product.id" class="text-xs w-full cursor-pointer">
                                            <span class="font-bold text-blue-600 block">{{ product.sku }}</span>
                                            <span class="text-gray-700 leading-tight">{{ product.name }}</span>
                                        </label>
                                    </div>
                                </DropdownMenuItem>

                                <div v-if="filteredProducts.length === 0" class="p-2 text-xs text-center text-gray-400">
                                    No se encontraron productos
                                </div>
                            </DropdownMenuContent>
                        </DropdownMenu>
                    </div>

                    <div class="flex gap-2 ml-auto">
                        <Button @click="generateDetailedReport" :disabled="isLoadingDetailed || detailedFilters.selectedProducts.length === 0">
                            <Loader2 v-if="isLoadingDetailed" class="mr-2 h-4 w-4 animate-spin" />
                            <Printer v-else class="mr-2 h-4 w-4" /> Imprimir Reporte
                        </Button>
                    </div>
                </div>
            </Card>


            <div class="min-h-[150px] border-2 border-dashed rounded-lg p-6 transition-colors"
                 :class="detailedFilters.selectedProducts.length > 0 ? 'bg-white border-blue-200' : 'bg-gray-50 border-gray-200'">

                <div v-if="detailedFilters.selectedProducts.length > 0">
                    <h3 class="text-sm font-bold text-gray-500 mb-3 flex items-center gap-2">
                        <Layers class="w-4 h-4"/> Productos a incluir en el reporte:
                    </h3>

                    <div class="flex flex-wrap gap-2">
                        <Badge
                            v-for="product in selectedProductDetails"
                            :key="product.id"
                            variant="secondary"
                            class="pl-3 pr-1 py-1.5 flex items-center gap-2 bg-blue-50 text-blue-700 border-blue-100 shadow-sm"
                        >
                            <div class="flex flex-col text-left">
                                <span class="text-[10px] font-bold text-gray-500">{{ product.sku }}</span>
                                <span class="text-xs font-medium max-w-[200px] truncate">{{ product.name }}</span>
                            </div>
                            <Button
                                variant="ghost"
                                size="icon"
                                class="h-6 w-6 ml-1 rounded-full hover:bg-red-100 hover:text-red-600 text-gray-400"
                                @click="removeProductFromSelection(product.id)"
                            >
                                <X class="h-3 w-3" />
                            </Button>
                        </Badge>
                    </div>
                </div>

                <div v-else class="h-full flex flex-col items-center justify-center text-gray-400 gap-2 py-4">
                    <Search class="h-8 w-8 opacity-20" />
                    <p class="text-sm">Selecciona productos en el buscador superior para verlos aquí.</p>
                </div>

            </div>

        </div>

    </div>
</template>