<script setup>
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

function formatCurrency(amount, currency = 'PEN') {
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency: currency }).format(amount)
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
          <TableRow v-for="render in renders" :key="render.id">
            <TableCell>{{ render.correlative }}</TableCell>
            <TableCell>{{ render.description }}</TableCell>
            <TableCell>{{ formatCurrency(render.amount) }}</TableCell>
            <TableCell>{{ render.cost_center_name || 'N/A' }}</TableCell>
            <TableCell>{{ new Date(render.created_at).toLocaleDateString() }}</TableCell>
            <TableCell class="text-right">
              <div class="flex justify-end gap-2">
                <Button variant="ghost" size="sm" @click="emit('edit-render', render)" :disabled="isFinalized">
                  <Pencil class="w-4 h-4" />
                </Button>
                <Button variant="ghost" size="sm" @click="emit('delete-render', render.id)" :disabled="isFinalized">
                  <Trash2 class="w-4 h-4 text-red-500" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
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
