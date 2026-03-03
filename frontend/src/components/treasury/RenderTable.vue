<script setup>
import { ref } from 'vue'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Pencil, Trash2 } from 'lucide-vue-next'

// eslint-disable-next-line no-unused-vars
const props = defineProps({
  renders: {
    type: Array,
    default: () => []
  },
  isFinalized: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['edit-render', 'delete-render'])

const openDetailsId = ref(null)

function formatCurrency(amount, currency = 'PEN') {
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency: currency }).format(amount)
}

function formatDate(dateString) {
  if (!dateString) return ''

  const str = String(dateString)

  // 1. Extraemos YYYY-MM-DD usando una expresión regular.
  // Esto captura la fecha ignorando cualquier hora o zona horaria (T00:00:00Z)
  const match = str.match(/(\d{4})[-/](\d{1,2})[-/](\d{1,2})/)

  if (match) {
    // Retornamos exactamente lo que mandó la DB (ej: 27/2/2026)
    // Usamos Number() para quitar ceros a la izquierda y que se vea igual a tu diseño
    return `${Number(match[3])}/${Number(match[2])}/${match[1]}`
  }

  // 2. Fallback súper robusto por si la fecha viene en otro formato (como un Timestamp)
  const date = new Date(str)
  if (!isNaN(date.getTime())) {
    // Al forzar timeZone: 'UTC', evitamos que le reste las 5 horas de Perú
    return date.toLocaleDateString('es-PE', { timeZone: 'UTC' })
  }

  return str
}

function toggleDetails(renderId) {
  openDetailsId.value = openDetailsId.value === renderId ? null : renderId
}
</script>

<template>
  <div class="border rounded-md">
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Correlativo</TableHead>
          <TableHead>Descripción</TableHead>
          <TableHead>Monto</TableHead>
          <TableHead>Centro de Costo</TableHead>
          <TableHead>Fecha</TableHead>
          <TableHead class="text-right">Acciones</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <template v-if="renders.length">
          <template v-for="render in renders" :key="render.id">
            <TableRow>
              <TableCell>{{ render.correlative }}</TableCell>
              <TableCell>{{ render.description }}</TableCell>
              <TableCell>{{ formatCurrency(render.amount) }}</TableCell>
              <TableCell>{{ render.cost_center_code || 'N/A' }}</TableCell>
              <TableCell>{{ formatDate(render.created_at) }}</TableCell>
              <TableCell class="text-right">
                <div class="flex justify-end gap-2">
                  <Button variant="ghost" size="sm" @click="toggleDetails(render.id)">
                      {{ openDetailsId === render.id ? 'Ocultar Detalles' : 'Ver Detalles' }}
                  </Button>
                  <Button variant="ghost" size="sm" @click="emit('edit-render', render)" :disabled="isFinalized">
                    <Pencil class="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm" @click="emit('delete-render', render.id)" :disabled="isFinalized">
                    <Trash2 class="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
            <TableRow v-if="openDetailsId === render.id && render.details && render.details.length">
                <TableCell colspan="6" class="p-0">
                    <div class="bg-gray-50 p-4 border-t">
                        <h5 class="font-bold mb-2 text-sm">Detalles de la Rendición:</h5>
                        <Table class="bg-white">
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Fecha</TableHead>
                                    <TableHead>Proveedor</TableHead>
                                    <TableHead>Factura</TableHead>
                                    <TableHead>Descripción</TableHead>
                                    <TableHead class="text-right">Monto</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                <TableRow v-for="detail in render.details" :key="detail.id">
                                    <TableCell>{{ formatDate(detail.date) }}</TableCell>
                                    <TableCell>{{ detail.provider_name || 'N/A' }}</TableCell>
                                    <TableCell>{{ detail.invoice_series || '' }}-{{ detail.invoice_number || '' }}</TableCell>
                                    <TableCell>{{ detail.description }}</TableCell>
                                    <TableCell class="text-right">{{ formatCurrency(detail.amount) }}</TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    </div>
                </TableCell>
            </TableRow>
          </template>
        </template>
        <template v-else>
          <TableRow>
            <TableCell colspan="6" class="text-center text-muted-foreground py-8">
              No hay rendiciones para esta asignación.
            </TableCell>
          </TableRow>
        </template>
      </TableBody>
    </Table>
  </div>
</template>
