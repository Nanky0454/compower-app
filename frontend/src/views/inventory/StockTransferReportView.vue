<script setup>
import { ref, onMounted } from 'vue' // <--- Agregar onMounted
import { useAuth0 } from '@auth0/auth0-vue'
import { Card } from '@/components/ui/card/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
// --- CAMBIO 1: Importar componentes Select ---
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Download, Search, Loader2 } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()

const now = new Date()
const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0]
const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0]

const filters = ref({
    start_date: firstDay,
    end_date: lastDay,
    warehouse_id: 'all' // 'all' o '' para indicar todos
})

// --- CAMBIO 2: Estado para almacenes ---
const warehouses = ref([])
const reportData = ref([])
const isLoading = ref(false)

// --- CAMBIO 3: Cargar almacenes al inicio ---
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

async function generateReport(format = 'json') {
    isLoading.value = true
    try {
        const token = await getAccessTokenSilently()

        // --- CAMBIO 4: Limpiar filtro si es 'all' ---
        const paramsToSend = { ...filters.value, format: format }
        if (paramsToSend.warehouse_id === 'all') delete paramsToSend.warehouse_id

        const params = new URLSearchParams(paramsToSend)
        // ---------------------------------------------

        const url = `${import.meta.env.VITE_API_URL}/api/reports/stock-transfers?${params.toString()}`

        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        })

        if (!response.ok) throw new Error('Error generando reporte')

        if (format === 'json') {
            reportData.value = await response.json()
        } else {
            const blob = await response.blob()
            const urlBlob = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = urlBlob
            a.download = `Stock_${filters.value.start_date}_al_${filters.value.end_date}.pdf`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
        }

    } catch (e) {
        console.error(e)
        alert(e.message)
    } finally {
        isLoading.value = false
    }
}
</script>

<template>
    <div class="space-y-4">
        <h1 class="text-2xl font-bold">Reporte de Transferencias</h1>

        <Card class="p-4">
            <div class="flex flex-wrap gap-4 items-end">

                <div class="w-64"> <label class="text-sm font-medium">Almacén</label>
                    <Select v-model="filters.warehouse_id">
                        <SelectTrigger>
                            <SelectValue placeholder="Todos los almacenes" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">Todos los almacenes</SelectItem>

                            <SelectItem
                                v-for="wh in warehouses"
                                :key="wh.id"
                                :value="wh.id.toString()"
                            >
                                {{ wh.name }}
                            </SelectItem>
                        </SelectContent>
                    </Select>
                </div>
                <div>
                    <label class="text-sm font-medium">Fecha Inicio</label>
                    <Input type="date" v-model="filters.start_date" />
                </div>
                <div>
                    <label class="text-sm font-medium">Fecha Fin</label>
                    <Input type="date" v-model="filters.end_date" />
                </div>

                <div class="flex gap-2">
                    <Button @click="generateReport('json')" :disabled="isLoading">
                        <Search class="mr-2 h-4 w-4" /> Consultar
                    </Button>
                    <Button variant="outline" @click="generateReport('pdf')" :disabled="isLoading">
                        <Loader2 v-if="isLoading" class="mr-2 h-4 w-4 animate-spin" />
                        <Download v-else class="mr-2 h-4 w-4" /> PDF
                    </Button>
                </div>
            </div>
        </Card>

        <Card v-if="reportData.length > 0">
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
                    <TableRow v-for="item in reportData" :key="item.codigo">
                        <TableCell>{{ item.codigo }}</TableCell>

                        <TableCell class="whitespace-normal min-w-[250px]">
                            {{ item.descripcion }}
                        </TableCell>

                        <TableCell>{{ item.unidad }}</TableCell>
                        <TableCell class="text-right">{{ item.saldo_inicial }}</TableCell>
                        <TableCell class="text-right">{{ item.entradas }}</TableCell>
                        <TableCell class="text-right">{{ item.salidas }}</TableCell>
                        <TableCell class="text-right font-bold">{{ item.stock_final }}</TableCell>
                        <TableCell class="text-right">{{ Number(item.costo_prom).toFixed(2) }}</TableCell>
                        <TableCell class="text-right">{{ Number(item.importe).toFixed(2) }}</TableCell>
                    </TableRow>
                </TableBody>
            </Table>
        </Card>
    </div>
</template>