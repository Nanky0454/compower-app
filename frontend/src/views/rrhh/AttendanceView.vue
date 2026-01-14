<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Loader2, Upload, FileText, RefreshCw, Download } from 'lucide-vue-next'
import { utils, writeFile } from 'xlsx'

const { getAccessTokenSilently } = useAuth0()

const fileInput = ref(null)
const isUploading = ref(false)
const isLoading = ref(true)
const error = ref(null)
const uploadMessage = ref(null)

const attendanceData = ref({ dates: [], employees: [] })

// Cargar asistencia
async function fetchAttendance() {
  isLoading.value = true
  error.value = null
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/hr/attendance`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('Error cargando asistencia')
    attendanceData.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}

// Descargar Excel
function downloadExcel() {
  if (!attendanceData.value.dates.length) return

  // 1. Fila 1: Fechas (y columnas vacías para merge)
  const header1 = ["Empleado", "DNI"]
  const merges = [
    { s: { r: 0, c: 0 }, e: { r: 1, c: 0 } }, // Merge Empleado vertical
    { s: { r: 0, c: 1 }, e: { r: 1, c: 1 } }  // Merge DNI vertical
  ]
  
  let colIndex = 2
  attendanceData.value.dates.forEach(date => {
    header1.push(date, "", "") // 3 espacios por fecha
    // Merge horizontal para la fecha (3 columnas)
    merges.push({ s: { r: 0, c: colIndex }, e: { r: 0, c: colIndex + 2 } })
    colIndex += 3
  })

  // 2. Fila 2: Sub-encabezados
  const header2 = ["", ""]
  attendanceData.value.dates.forEach(() => {
    header2.push("Ingreso", "Salida", "Tardanza")
  })

  // 3. Filas de Datos
  const rows = attendanceData.value.employees.map(emp => {
    const row = [emp.employee, emp.dni]
    attendanceData.value.dates.forEach(date => {
      const data = emp.attendance[date] || {}
      row.push(data.ingreso || "", data.salida || "", data.tardanza || "")
    })
    return row
  })

  // 4. Crear Hoja
  const ws_data = [header1, header2, ...rows]
  const ws = utils.aoa_to_sheet(ws_data)
  ws['!merges'] = merges

  // Ancho de columnas (opcional)
  const wscols = [{ wch: 30 }, { wch: 12 }] // Empleado, DNI
  attendanceData.value.dates.forEach(() => {
    wscols.push({ wch: 10 }, { wch: 10 }, { wch: 10 })
  })
  ws['!cols'] = wscols

  // 5. Crear Libro y Descargar
  const wb = utils.book_new()
  utils.book_append_sheet(wb, ws, "Asistencia")
  writeFile(wb, "Reporte_Asistencia.xlsx")
}

// Subir archivo
async function handleUpload() {
    // Fix: Acceder correctamente al archivo desde el input ref
    const file = fileInput.value.files ? fileInput.value.files[0] : null
    
    // Debug
    console.log("File selected:", file)
    
    if (!file) {
        error.value = "Por favor selecciona un archivo primero."
        return
    }

    isUploading.value = true
    uploadMessage.value = null
    error.value = null

    const formData = new FormData()
    formData.append('file', file)

    try {
        const token = await getAccessTokenSilently()
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/hr/attendance/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        })

        const data = await response.json()
        if (!response.ok) throw new Error(data.error || 'Error al subir archivo')

        uploadMessage.value = data.message
        fileInput.value.value = '' // Limpiar input
        await fetchAttendance() // Recargar tabla
    } catch (e) {
        error.value = e.message
    } finally {
        isUploading.value = false
    }
}

onMounted(fetchAttendance)
</script>

<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold tracking-tight">Control de Asistencia</h1>
      <div class="flex gap-2">
        <Button variant="outline" @click="downloadExcel" :disabled="attendanceData.employees.length === 0">
            <Download class="mr-2 h-4 w-4" />
            Descargar Excel
        </Button>
        <Button variant="outline" @click="fetchAttendance">
            <RefreshCw class="mr-2 h-4 w-4" />
            Actualizar
        </Button>
      </div>
    </div>

    <!-- Sección de Carga -->
    <Card>
        <CardHeader>
            <CardTitle>Cargar Registros</CardTitle>
            <CardDescription>Sube el archivo .txt exportado del reloj biométrico. Solo se procesarán registros desde el 21/11/2025.</CardDescription>
        </CardHeader>
        <CardContent>
            <div class="flex items-end gap-4">
                <div class="grid w-full max-w-sm items-center gap-1.5">
                    <Label for="logFile">Archivo de Log</Label>
                    <input 
                        id="logFile" 
                        type="file" 
                        ref="fileInput" 
                        accept=".txt"
                        class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    />
                </div>
                <Button @click="handleUpload" :disabled="isUploading">
                    <Loader2 v-if="isUploading" class="mr-2 h-4 w-4 animate-spin" />
                    <Upload v-else class="mr-2 h-4 w-4" />
                    Procesar Archivo
                </Button>
            </div>
            <div v-if="uploadMessage" class="mt-2 text-sm text-green-600 font-medium">
                {{ uploadMessage }}
            </div>
            <div v-if="error" class="mt-2 text-sm text-red-600 font-medium">
                {{ error }}
            </div>
        </CardContent>
    </Card>

    <!-- Tabla de Asistencia -->
    <Card>
      <CardHeader>
        <CardTitle>Reporte de Asistencia</CardTitle>
      </CardHeader>
      <CardContent>
        <div v-if="isLoading" class="flex justify-center p-8">
          <Loader2 class="h-8 w-8 animate-spin text-gray-500" />
        </div>
        
        <div v-else class="overflow-x-auto">
            <Table class="border-collapse border border-gray-200">
            <TableHeader>
                <!-- Fila Superior: Fechas -->
                <TableRow>
                    <TableHead rowspan="2" class="w-[250px] border border-gray-200 bg-gray-50 sticky left-0 z-20">Empleado</TableHead>
                    <TableHead v-for="date in attendanceData.dates" :key="date" colspan="3" class="text-center border border-gray-200 bg-gray-100 font-bold text-gray-700">
                        {{ date }}
                    </TableHead>
                </TableRow>
                <!-- Fila Inferior: Columnas de Detalle -->
                <TableRow>
                    <template v-for="date in attendanceData.dates" :key="date + '-sub'">
                        <TableHead class="text-center border border-gray-200 text-xs w-[80px] bg-gray-50">INGRESO</TableHead>
                        <TableHead class="text-center border border-gray-200 text-xs w-[80px] bg-gray-50">SALIDA</TableHead>
                        <TableHead class="text-center border border-gray-200 text-xs w-[80px] bg-gray-50">TARDANZA</TableHead>
                    </template>
                </TableRow>
            </TableHeader>
            <TableBody>
                <TableRow v-if="attendanceData.employees.length === 0">
                <TableCell :colspan="attendanceData.dates.length * 3 + 1" class="text-center text-gray-500 py-8">
                    No hay registros de asistencia para mostrar.
                </TableCell>
                </TableRow>
                <TableRow v-for="emp in attendanceData.employees" :key="emp.dni" class="hover:bg-gray-50">
                    <TableCell class="font-medium border border-gray-200 sticky left-0 bg-white z-10">
                        <div class="flex flex-col">
                            <span class="text-sm font-semibold">{{ emp.employee }}</span>
                            <span class="text-xs text-gray-400">{{ emp.dni }}</span>
                        </div>
                    </TableCell>
                    
                    <template v-for="date in attendanceData.dates" :key="date + '-' + emp.dni">
                        <!-- Ingreso -->
                        <TableCell class="text-center border border-gray-200 text-xs p-2">
                            {{ emp.attendance[date]?.ingreso || '' }}
                        </TableCell>
                        <!-- Salida -->
                        <TableCell class="text-center border border-gray-200 text-xs p-2">
                            {{ emp.attendance[date]?.salida || '' }}
                        </TableCell>
                        <!-- Tardanza -->
                        <TableCell class="text-center border border-gray-200 text-xs p-2 font-medium" 
                            :class="{'text-red-600 bg-red-50': emp.attendance[date]?.tardanza !== '00:00:00' && emp.attendance[date]?.tardanza}">
                            {{ emp.attendance[date]?.tardanza !== '00:00:00' ? emp.attendance[date]?.tardanza : '' }}
                        </TableCell>
                    </template>
                </TableRow>
            </TableBody>
            </Table>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
