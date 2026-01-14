<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useToast } from '@/components/ui/toast/use-toast'
import { Trash2, FileText } from 'lucide-vue-next'

const props = defineProps({
  open: Boolean,
  transaction: Object
})

const emit = defineEmits(['update:open', 'render-added'])

const { toast } = useToast()
const { getAccessTokenSilently } = useAuth0()
const renders = ref([])
const loading = ref(false)
const documentTypes = ref([])

// Form State
const amount = ref('') // Used when !hasDocument, or as total
const description = ref('')
const hasDocument = ref(false)
const docTypeId = ref('')
const docSeries = ref('')
const docNumber = ref('')
const docRuc = ref('')
const docName = ref('')
const docDate = ref('')
const docAmount = ref('') // Amount covered by document
const otherAmount = ref('') // Amount NOT covered by document

// Document Viewer State
const selectedDocument = ref(null)
const isDocumentOpen = ref(false)

// Computed
const totalRendered = computed(() => {
    return renders.value.reduce((sum, r) => sum + r.amount, 0)
})

const remainingBalance = computed(() => {
    if (!props.transaction) return 0
    return props.transaction.amount - totalRendered.value
})

// Fetch Renders
async function fetchRenders() {
    if (!props.transaction) return
    loading.value = true
    try {
        const token = await getAccessTokenSilently()
        const res = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/transactions/${props.transaction.id}/renders`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        if (res.ok) {
            renders.value = await res.json()
        }
    } catch (error) {
        console.error("Error fetching renders:", error)
    } finally {
        loading.value = false
    }
}

// Fetch Document Types
async function fetchDocumentTypes() {
    try {
        const token = await getAccessTokenSilently()
        const res = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/document-types`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        if (res.ok) {
            documentTypes.value = await res.json()
        }
    } catch (error) {
        console.error("Error fetching document types:", error)
    }
}

// Submit Render
async function submitRender() {
    // Calculate total amount
    let finalAmount = 0
    if (hasDocument.value) {
        finalAmount = (parseFloat(docAmount.value) || 0) + (parseFloat(otherAmount.value) || 0)
    } else {
        finalAmount = parseFloat(amount.value) || 0
    }

    if (finalAmount <= 0 || !description.value) {
        toast({ title: "Error", description: "Monto y descripción son obligatorios", variant: "destructive" })
        return
    }

    if (finalAmount > remainingBalance.value) {
         toast({ title: "Error", description: "El monto excede el saldo pendiente", variant: "destructive" })
         return
    }

    const payload = {
        amount: finalAmount,
        description: description.value,
        document: null
    }

    if (hasDocument.value) {
        if (!docTypeId.value || !docSeries.value || !docNumber.value || !docDate.value || !docAmount.value) {
             toast({ title: "Error", description: "Faltan datos del documento", variant: "destructive" })
             return
        }
        payload.document = {
            document_type_id: parseInt(docTypeId.value),
            series: docSeries.value,
            number: docNumber.value,
            issuer_ruc: docRuc.value,
            issuer_name: docName.value,
            issue_date: docDate.value,
            amount: parseFloat(docAmount.value)
        }
    }

    console.log("Sending payload:", payload)

    try {
        const token = await getAccessTokenSilently()
        const res = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/transactions/${props.transaction.id}/renders`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}` 
            },
            body: JSON.stringify(payload)
        })

        if (res.ok) {
            toast({ title: "Éxito", description: "Rendición agregada correctamente" })
            resetForm()
            fetchRenders()
            emit('render-added')
        } else {
            const err = await res.json()
            console.error("Error response:", err)
            toast({ title: "Error", description: err.error || "Error al guardar", variant: "destructive" })
        }
    } catch (error) {
        console.error("Fetch error:", error)
        toast({ title: "Error", description: "Error de conexión", variant: "destructive" })
    }
}

// Delete Render
async function deleteRender(id) {
    if (!confirm("¿Estás seguro de eliminar esta rendición?")) return

    try {
        const token = await getAccessTokenSilently()
        const res = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/renders/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        })
        if (res.ok) {
            toast({ title: "Éxito", description: "Rendición eliminada" })
            fetchRenders()
            emit('render-added') // Refresh parent if needed
        }
    } catch (error) {
        console.error(error)
    }
}

function resetForm() {
    amount.value = ''
    description.value = ''
    hasDocument.value = false
    docTypeId.value = ''
    docSeries.value = ''
    docNumber.value = ''
    docRuc.value = ''
    docName.value = ''
    docDate.value = ''
    docAmount.value = ''
    otherAmount.value = ''
}

function formatCurrency(val) {
    return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(val)
}

function formatDate(dateString) {
    if (!dateString) return ''
    return new Date(dateString).toLocaleDateString('es-PE')
}

function viewDocument(doc) {
    selectedDocument.value = doc
    isDocumentOpen.value = true
}

// Watchers
watch(() => props.open, (newVal) => {
    if (newVal) {
        fetchRenders()
        fetchDocumentTypes()
    }
})

// Auto-fill doc amount when render amount changes
watch(amount, (newVal) => {
    if (hasDocument.value && !docAmount.value) {
        docAmount.value = newVal
    }
})
</script>

<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="w-full max-w-[95vw] md:max-w-5xl max-h-[90vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>Rendición de Asignación</DialogTitle>
      </DialogHeader>

      <div v-if="transaction" class="grid gap-6 py-4">
        <!-- Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="p-4 border rounded bg-gray-50">
                <div class="text-sm text-gray-500">Monto Asignado</div>
                <div class="text-xl font-bold">{{ formatCurrency(transaction.amount) }}</div>
            </div>
            <div class="p-4 border rounded bg-blue-50">
                <div class="text-sm text-blue-500">Total Rendido</div>
                <div class="text-xl font-bold text-blue-700">{{ formatCurrency(totalRendered) }}</div>
            </div>
            <div class="p-4 border rounded" :class="remainingBalance < 0 ? 'bg-red-50' : 'bg-green-50'">
                <div class="text-sm" :class="remainingBalance < 0 ? 'text-red-500' : 'text-green-500'">Saldo Pendiente</div>
                <div class="text-xl font-bold" :class="remainingBalance < 0 ? 'text-red-700' : 'text-green-700'">
                    {{ formatCurrency(remainingBalance) }}
                </div>
            </div>
        </div>

        <!-- Add Render Form -->
        <div class="border rounded p-4 space-y-4">
            <h3 class="font-semibold">Nueva Rendición</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="space-y-2" v-if="!hasDocument">
                    <Label>Monto a Rendir</Label>
                    <Input type="number" v-model="amount" placeholder="0.00" min="0" />
                </div>
                
                <div class="space-y-2">
                    <Label>Descripción</Label>
                    <Input v-model="description" placeholder="Gastos de viáticos..." />
                </div>
            </div>

            <div class="flex items-center space-x-2">
                <Checkbox id="has-doc" v-model="hasDocument" />
                <Label htmlFor="has-doc">Tiene Documento (Factura/Boleta)</Label>
            </div>

            <!-- Document Fields -->
            <div v-if="hasDocument" class="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded border">
                <div class="space-y-2">
                    <Label>Tipo Doc.</Label>
                    <Select v-model="docTypeId">
                        <SelectTrigger>
                            <SelectValue placeholder="Seleccione" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem v-for="t in documentTypes" :key="t.id" :value="String(t.id)">
                                {{ t.name }}
                            </SelectItem>
                        </SelectContent>
                    </Select>
                </div>
                <div class="space-y-2">
                    <Label>Serie</Label>
                    <Input v-model="docSeries" placeholder="F001" />
                </div>
                <div class="space-y-2">
                    <Label>Número</Label>
                    <Input v-model="docNumber" placeholder="000123" />
                </div>
                <div class="space-y-2">
                    <Label>RUC Emisor</Label>
                    <Input v-model="docRuc" placeholder="20..." />
                </div>
                <div class="space-y-2">
                    <Label>Razón Social</Label>
                    <Input v-model="docName" />
                </div>
                <div class="space-y-2">
                    <Label>Fecha Emisión</Label>
                    <Input type="date" v-model="docDate" />
                </div>
                <div class="space-y-2">
                    <Label>Monto Documento</Label>
                    <Input type="number" v-model="docAmount" placeholder="0.00" min="0" />
                </div>
                <div class="space-y-2">
                    <Label>Otro Monto (Sin Doc.)</Label>
                    <Input type="number" v-model="otherAmount" placeholder="0.00" min="0" />
                </div>
            </div>

            <Button @click="submitRender" :disabled="loading">
                {{ loading ? 'Guardando...' : 'Agregar Rendición' }}
            </Button>
        </div>

        <!-- Renders List -->
        <div>
            <h3 class="font-semibold mb-2">Historial de Rendiciones</h3>
            <div class="border rounded-md overflow-x-auto">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Correlativo</TableHead>
                            <TableHead>Fecha</TableHead>
                            <TableHead>Descripción</TableHead>
                            <TableHead>Documento</TableHead>
                            <TableHead class="text-right">Monto</TableHead>
                            <TableHead></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        <TableRow v-for="render in renders" :key="render.id">
                            <TableCell>{{ render.correlative || '-' }}</TableCell>
                            <TableCell>{{ new Date(render.created_at).toLocaleDateString() }}</TableCell>
                            <TableCell>{{ render.description }}</TableCell>
                            <TableCell>
                                <div v-if="render.document" class="flex items-center space-x-2">
                                    <div>
                                        <div class="font-medium">{{ render.document.document_type_name }}</div>
                                        <div class="text-xs text-gray-500">{{ render.document.series }}-{{ render.document.number }}</div>
                                    </div>
                                    <Button variant="ghost" size="icon" @click="viewDocument(render.document)">
                                        <FileText class="h-4 w-4 text-blue-500" />
                                    </Button>
                                </div>
                                <span v-else>-</span>
                            </TableCell>
                            <TableCell class="text-right">
                                {{ props.transaction?.account_currency === 'USD' ? '$' : 'S/' }} {{ render.amount.toFixed(2) }}
                            </TableCell>
                            <TableCell>
                                <Button variant="ghost" size="icon" @click="deleteRender(render.id)">
                                    <Trash2 class="h-4 w-4 text-red-500" />
                                </Button>
                            </TableCell>
                        </TableRow>
                        <TableRow v-if="renders.length === 0">
                            <TableCell colspan="6" class="text-center py-4 text-gray-500">
                                No hay rendiciones registradas
                            </TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
            </div>
        </div>

      </div>
      <DialogFooter>
        <Button variant="outline" @click="$emit('update:open', false)">Cerrar</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>

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
</template>
