<script setup>
import { ref } from 'vue'
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
import AllocationRenderModal from './AllocationRenderModal.vue'

const props = defineProps({
  transactions: Array
})

const selectedDocument = ref(null)
const isDocumentOpen = ref(false)

// Render Modal State
const selectedTransactionForRender = ref(null)
const isRenderModalOpen = ref(false)

function formatCurrency(amount, currency = 'PEN') {
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency: currency }).format(amount)
}

function formatDate(dateString) {
  if (!dateString) return ''
  return new Date(dateString).toLocaleDateString('es-PE')
}

function viewDocument(doc) {
    selectedDocument.value = doc
    isDocumentOpen.value = true
}

function openRenderModal(transaction) {
    selectedTransactionForRender.value = transaction
    isRenderModalOpen.value = true
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
          <TableHead>Acciones</TableHead>
          <TableHead class="text-right">Monto</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="t in transactions" :key="t.id">
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
            <Button v-if="t.document" variant="outline" size="sm" @click="viewDocument(t.document)">
                Ver Doc
            </Button>
            <span v-else class="text-gray-400">-</span>
          </TableCell>
          <TableCell>
            <!-- Show Rendir button only for EGRESO and ASIGNACION -->
            <Button 
                v-if="t.type === 'EGRESO' && t.expense_type_name === 'ASIGNACION'" 
                variant="secondary" 
                size="sm" 
                @click="openRenderModal(t)"
            >
                Rendir
            </Button>
          </TableCell>
          <TableCell class="text-right font-medium" :class="t.type === 'INGRESO' ? 'text-green-600' : 'text-red-600'">
            {{ t.type === 'INGRESO' ? '+' : '-' }} {{ formatCurrency(t.amount, t.account_currency) }}
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

    <!-- Allocation Render Modal -->
    <AllocationRenderModal 
        :open="isRenderModalOpen" 
        @update:open="isRenderModalOpen = $event"
        :transaction="selectedTransactionForRender"
    />
  </div>
</template>
