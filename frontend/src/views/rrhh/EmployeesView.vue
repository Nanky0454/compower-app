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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Loader2, Plus, Users } from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const { getAccessTokenSilently } = useAuth0()

// Estado
const employees = ref([])
const isLoading = ref(true)
const isDialogOpen = ref(false)
const isSubmitting = ref(false)
const error = ref(null)

// Formulario
const initialForm = {
  first_name: '',
  last_name: '',
  document_type: 'DNI',
  document_number: '',
  position: '',
  salary: '',
  start_date: '',
  birth_date: '',
  phone: '',
  email: '',
  licenses: [] // Array de { license_number, category, expiration_date }
}
const formData = ref({ ...initialForm })

// Formatter de moneda
const currencyFormatter = new Intl.NumberFormat('es-PE', {
  style: 'currency',
  currency: 'PEN',
})

// Cargar empleados
async function fetchEmployees() {
  isLoading.value = true
  error.value = null
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/hr/employees`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('Error cargando empleados')
    employees.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}

// Abrir modal
function openRegisterModal() {
  formData.value = { 
      ...initialForm,
      licenses: [] 
  }
  isDialogOpen.value = true
}

// Agregar licencia
function addLicense() {
    formData.value.licenses.push({
        license_number: '',
        category: 'A-I',
        expiration_date: ''
    })
}

// Remover licencia
function removeLicense(index) {
    formData.value.licenses.splice(index, 1)
}

// Registrar empleado
async function handleRegister() {
  isSubmitting.value = true
  error.value = null
  try {
    const token = await getAccessTokenSilently()
    
    // Validaciones básicas
    if (!formData.value.first_name || !formData.value.last_name || !formData.value.document_number) {
        throw new Error("Nombre, Apellido y Documento son obligatorios")
    }

    const payload = {
        ...formData.value,
        salary: parseFloat(formData.value.salary) || 0
    }

    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/hr/employees`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.error || 'Error al registrar empleado')
    }

    await fetchEmployees()
    isDialogOpen.value = false

  } catch (e) {
    error.value = e.message
  } finally {
    isSubmitting.value = false
  }
}

onMounted(fetchEmployees)
</script>

<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-3xl font-bold tracking-tight">Gestión de Empleados</h1>
      <Button @click="openRegisterModal">
        <Plus class="mr-2 h-4 w-4" />
        Registrar Empleado
      </Button>
    </div>

    <div v-if="error" class="bg-red-50 text-red-500 p-4 rounded-md">
      {{ error }}
    </div>

    <Card>
      <CardHeader>
        <CardTitle>Directorio de Personal</CardTitle>
      </CardHeader>
      <CardContent>
        <div v-if="isLoading" class="flex justify-center p-8">
          <Loader2 class="h-8 w-8 animate-spin text-gray-500" />
        </div>
        
        <Table v-else>
          <TableHeader>
            <TableRow>
              <TableHead>Nombres</TableHead>
              <TableHead>Apellidos</TableHead>
              <TableHead>Contacto</TableHead>
              <TableHead>Documento</TableHead>
              <TableHead>Cargo</TableHead>
              <TableHead>Licencias</TableHead>
              <TableHead class="text-right">Salario</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-if="employees.length === 0">
              <TableCell colspan="7" class="text-center text-gray-500 py-8">
                No hay empleados registrados.
              </TableCell>
            </TableRow>
            <TableRow v-for="emp in employees" :key="emp.id">
              <TableCell class="font-medium">{{ emp.first_name }}</TableCell>
              <TableCell class="font-medium">{{ emp.last_name }}</TableCell>
              <TableCell>
                  <div class="flex flex-col text-xs">
                      <span v-if="emp.phone">{{ emp.phone }}</span>
                      <span v-if="emp.email" class="text-gray-500">{{ emp.email }}</span>
                      <span v-if="!emp.phone && !emp.email" class="text-gray-400">-</span>
                  </div>
              </TableCell>
              <TableCell>
                <span class="text-xs font-semibold text-gray-500 mr-1">{{ emp.document_type }}:</span>
                {{ emp.document_number }}
              </TableCell>
              <TableCell>{{ emp.position || '-' }}</TableCell>
              <TableCell>
                  <div v-if="emp.licenses && emp.licenses.length > 0" class="flex flex-col gap-1">
                      <span v-for="lic in emp.licenses" :key="lic.id" class="text-xs bg-gray-100 px-2 py-1 rounded border">
                          {{ lic.category }} - {{ lic.license_number }}
                      </span>
                  </div>
                  <span v-else class="text-gray-400 text-xs">Sin licencias</span>
              </TableCell>
              <TableCell class="text-right">{{ currencyFormatter.format(emp.salary || 0) }}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>

    <Dialog :open="isDialogOpen" @update:open="isDialogOpen = $event">
      <DialogContent class="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Registrar Nuevo Empleado</DialogTitle>
          <DialogDescription>
            Ingresa los datos personales, laborales y licencias.
          </DialogDescription>
        </DialogHeader>
        
        <div class="grid gap-4 py-4">
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label for="first_name">Nombres</Label>
              <Input id="first_name" v-model="formData.first_name" placeholder="Juan" />
            </div>
            <div class="space-y-2">
              <Label for="last_name">Apellidos</Label>
              <Input id="last_name" v-model="formData.last_name" placeholder="Pérez" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
                <Label for="birth_date">Fecha de Nacimiento</Label>
                <Input id="birth_date" type="date" v-model="formData.birth_date" />
            </div>
            <div class="space-y-2">
                <Label for="start_date">Fecha de Ingreso</Label>
                <Input id="start_date" type="date" v-model="formData.start_date" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label for="phone">Celular</Label>
              <Input id="phone" v-model="formData.phone" placeholder="999..." />
            </div>
            <div class="space-y-2">
              <Label for="email">Correo Electrónico</Label>
              <Input id="email" type="email" v-model="formData.email" placeholder="ejemplo@compower.pe" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label for="doc_type">Tipo Doc.</Label>
              <Select v-model="formData.document_type">
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="DNI">DNI</SelectItem>
                  <SelectItem value="CE">CE</SelectItem>
                  <SelectItem value="PASAPORTE">Pasaporte</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div class="space-y-2">
              <Label for="doc_num">Nro. Documento</Label>
              <Input id="doc_num" v-model="formData.document_number" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
                <Label for="position">Cargo / Puesto</Label>
                <Input id="position" v-model="formData.position" placeholder="Ej. Analista" />
            </div>
            <div class="space-y-2">
                <Label for="salary">Salario Mensual (S/)</Label>
                <Input id="salary" type="number" v-model="formData.salary" placeholder="0.00" />
            </div>
          </div>

          <!-- Sección Licencias -->
          <div class="border-t pt-4 mt-2">
              <div class="flex justify-between items-center mb-2">
                  <Label class="font-semibold">Licencias de Conducir</Label>
                  <Button type="button" variant="outline" size="sm" @click="addLicense">
                      <Plus class="h-3 w-3 mr-1" /> Agregar
                  </Button>
              </div>
              
              <div v-if="formData.licenses.length === 0" class="text-sm text-gray-500 italic">
                  No se han agregado licencias.
              </div>

              <div v-else class="space-y-3">
                  <div v-for="(lic, index) in formData.licenses" :key="index" class="flex gap-2 items-end border p-2 rounded bg-gray-50">
                      <div class="flex-1 space-y-1">
                          <Label class="text-xs">Categoría</Label>
                          <Select v-model="lic.category">
                            <SelectTrigger class="h-8">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="A-I">A-I</SelectItem>
                                <SelectItem value="A-IIa">A-IIa</SelectItem>
                                <SelectItem value="A-IIb">A-IIb</SelectItem>
                                <SelectItem value="A-IIIa">A-IIIa</SelectItem>
                                <SelectItem value="A-IIIb">A-IIIb</SelectItem>
                                <SelectItem value="A-IIIc">A-IIIc</SelectItem>
                            </SelectContent>
                          </Select>
                      </div>
                      <div class="flex-1 space-y-1">
                          <Label class="text-xs">Nro. Licencia</Label>
                          <Input v-model="lic.license_number" class="h-8" placeholder="Q123..." />
                      </div>
                      <div class="flex-1 space-y-1">
                          <Label class="text-xs">Vencimiento</Label>
                          <Input type="date" v-model="lic.expiration_date" class="h-8" />
                      </div>
                      <Button type="button" variant="ghost" size="icon" class="h-8 w-8 text-red-500" @click="removeLicense(index)">
                          <span class="sr-only">Eliminar</span>
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trash-2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>
                      </Button>
                  </div>
              </div>
          </div>

        </div>

        <DialogFooter>
          <Button variant="secondary" @click="isDialogOpen = false">Cancelar</Button>
          <Button @click="handleRegister" :disabled="isSubmitting">
            <Loader2 v-if="isSubmitting" class="mr-2 h-4 w-4 animate-spin" />
            Registrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
