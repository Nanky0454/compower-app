<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router' // Import useRouter
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Pencil, Trash2 } from 'lucide-vue-next'

const props = defineProps({
  transactions: Array
})

const emit = defineEmits(['edit-transaction', 'delete-transaction'])

const router = useRouter() // Initialize router

const selectedDocument = ref(null)
const isDocumentOpen = ref(false)

function formatCurrency(amount, currency = 'PEN') {
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency: currency }).format(amount)
}

function formatDate(dateString) {
  if (!dateString) return ''
  
  // Normalize string: take only the date part (YYYY-MM-DD)
  const str = String(dateString)
  const datePart = str.split(/[T ]/)[0]
  const parts = datePart.split('-').map(Number)
  
  if (parts.length === 3 && !parts.some(isNaN)) {
    const [year, month, day] = parts
    // new Date(year, monthIndex, day) creates a date in local time
    const date = new Date(year, month - 1, day)
    return date.toLocaleDateString('es-PE')
  }
  
  // Fallback for other formats
  return new Date(str).toLocaleDateString('es-PE')
}

function viewDocument(doc) {
    selectedDocument.value = doc
    isDocumentOpen.value = true
}

function goToAllocationDetail(transactionId) {
  router.push({ name: 'treasury-allocation-detail', params: { id: transactionId } })
}
</script>

<template>
  <div class="rounded-md border">
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Fecha</TableHead>
          <TableHead>Correlativo</TableHead>
          <TableHead>Descripción</TableHead>
          <TableHead>Cuenta</TableHead>
          <TableHead>Tipo</TableHead>
          <TableHead>Categoría</TableHead>
          <TableHead>Beneficiario</TableHead>
          <TableHead>Documento</TableHead>
          <TableHead>Estado</TableHead> <!-- NEW STATUS COLUMN -->
          <TableHead class="text-right">Monto</TableHead>
          <TableHead class="text-right">Acciones</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow 
          v-for="t in transactions" 
          :key="t.id"
          :class="{'cursor-pointer hover:bg-muted/50': t.type === 'EGRESO' && t.expense_type_name === 'ASIGNACION'}"
          @click="t.type === 'EGRESO' && t.expense_type_name === 'ASIGNACION' ? goToAllocationDetail(t.id) : null"
        >
          <TableCell>{{ formatDate(t.date) }}</TableCell>
          <TableCell>{{ t.correlative || '-' }}</TableCell>
          <TableCell>{{ t.description }}</TableCell>
          <TableCell>{{ t.account_alias || 'Cuenta Principal' }}</TableCell>
          <TableCell>
            <Badge :variant="t.type === 'INGRESO' ? 'default' : 'destructive'">
              {{ t.type }}
            </Badge>
          </TableCell>
          <TableCell>{{ t.expense_type_name || t.income_type_name || '-' }}</TableCell>
          <TableCell>{{ t.beneficiary_name || '-' }}</TableCell>
          <TableCell>
            <Button v-if="t.document" variant="outline" size="sm" @click.stop="viewDocument(t.document)">
                Ver Doc
            </Button>
            <span v-else class="text-gray-400">-</span>
          </TableCell>
          <TableCell> <!-- NEW STATUS CELL -->
            <Badge 
              v-if="t.type === 'EGRESO' && t.expense_type_name === 'ASIGNACION'"
              :variant="t.status === 'Finalizada' ? 'default' : 'secondary'"
            >
              {{ t.status }}
            </Badge>
            <span v-else>-</span>
          </TableCell>
          <TableCell class="text-right font-medium" :class="t.type === 'INGRESO' ? 'text-green-600' : 'text-red-600'">
            {{ t.type === 'INGRESO' ? '+' : '-' }} {{ formatCurrency(t.amount, t.account_currency) }}
          </TableCell>
          <TableCell class="text-right">
            <div class="flex justify-end gap-2">
              <Button variant="ghost" size="sm" @click.stop="emit('edit-transaction', t)">
                <Pencil class="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" @click.stop="emit('delete-transaction', t.id)">
                <Trash2 class="h-4 w-4 text-red-500" />
              </Button>
            </div>
          </TableCell>
        </TableRow>
        <TableRow v-if="transactions.length === 0">
          <TableCell colspan="10" class="text-center py-4 text-gray-500">
            No hay movimientos registrados
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>

    <!-- Document Details Dialog -->
    <Dialog :open="isDocumentOpen" @update:open="isDocumentOpen = $event">
        <DialogContent>
            <DialogHeader>
                <DialogTitle>Detalle del Documento</DialogTitle>
            </DialogHeader>
            <div v-if="selectedDocument" class="grid gap-4 py-4">
                <div class="grid grid-cols-4 items-center gap-4">
                    <span class="font-semibold text-right">Tipo:</span>
                    <span class="col-span-3">{{ selectedDocument.document_type_name }}</span>
                </div>
                <div class="grid grid-cols-4 items-center gap-4">
                    <span class="font-semibold text-right">Serie/Nro:</span>
                    <span class="col-span-3">{{ selectedDocument.series }} - {{ selectedDocument.number }}</span>
                </div>
                <div class="grid grid-cols-4 items-center gap-4">
                    <span class="font-semibold text-right">RUC Emisor:</span>
                    <span class="col-span-3">{{ selectedDocument.issuer_ruc || '-' }}</span>
                </div>
                <div class="grid grid-cols-4 items-center gap-4">
                    <span class="font-semibold text-right">Razón Social:</span>
                    <span class="col-span-3">{{ selectedDocument.issuer_name || '-' }}</span>
                </div>
                <div class="grid grid-cols-4 items-center gap-4">
                    <span class="font-semibold text-right">Fecha:</span>
                    <span class="col-span-3">{{ formatDate(selectedDocument.issue_date) }}</span>
                </div>
                <div class="grid grid-cols-4 items-center gap-4">
                    <span class="font-semibold text-right">Monto:</span>
                    <span class="col-span-3">{{ formatCurrency(selectedDocument.amount) }}</span>
                </div>
            </div>
        </DialogContent>
    </Dialog>
  </div>
</template>
