<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Badge } from '@/components/ui/badge/index.js'
import { RouterLink } from 'vue-router'
import { Eye, Download, Loader2, Ban } from 'lucide-vue-next'
import KardexView from './KardexView.vue'
import { useToast } from '@/components/ui/toast/use-toast'

const activeTab = ref('transferencias')

const { user, getAccessTokenSilently } = useAuth0()
const { toast } = useToast()
const transfers = ref([])
const isLoading = ref(true)
const error = ref(null)

const downloadingId = ref(null)
const anullingId = ref(null)

const AUTH0_NAMESPACE = 'https://appcompower.com'

const isAdmin = computed(() => {
  const rolesKey = AUTH0_NAMESPACE + '/roles';
  if (user.value && user.value[rolesKey] && Array.isArray(user.value[rolesKey])) {
    const userRoles = user.value[rolesKey].map(role => role.toLowerCase());
    return userRoles.includes('admin');
  }
  return false;
})

async function fetchTransfers() {
  // isLoading.value = true // Opcional: comentar para que no parpadee al recargar
  error.value = null
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/transfers`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('No se pudieron cargar las transferencias.')
    transfers.value = await response.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
}

async function downloadPDF(transferId, serie, numero) {
  if (!transferId) return
  try {
    downloadingId.value = transferId
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/gre/download-pdf/${transferId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('Error al generar el PDF')
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `GRE-${serie}-${numero}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  } catch (e) {
    console.error(e)
    toast({ title: "Error", description: "No se pudo descargar el PDF.", variant: "destructive" })
  } finally {
    downloadingId.value = null
  }
}

async function handleAnular(transfer) {
  // Usamos el gre_id si viene del backend, o el ID de la transferencia si tu lógica lo permite
  // Asegúrate de que tu backend en to_dict() envíe 'gre_id'
  const targetId = transfer.gre_id;

  if (!targetId) {
     toast({ title: "Error", description: "No se encontró ID de guía asociada.", variant: "destructive" })
     return;
  }

  if (!confirm(`PELIGRO: ¿Anular la Guía ${transfer.gre_series}-${transfer.gre_number}?\n\nEl stock retornará al almacén de origen.`)) return;

  anullingId.value = transfer.id
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/gre/anular/${targetId}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })

    const data = await res.json()

    if (res.ok) {
        toast({ title: "Anulado", description: "Guía anulada correctamente.", variant: "default" })
        await fetchTransfers() // Recarga los datos para actualizar la tabla
    } else {
        toast({ title: "Error", description: data.error, variant: "destructive" })
    }
  } catch (e) {
    console.error(e)
    toast({ title: "Error", description: "Fallo de conexión", variant: "destructive" })
  } finally {
    anullingId.value = null
  }
}

onMounted(fetchTransfers)

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const options = { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }
  return new Date(dateString).toLocaleString('es-ES', options)
}

// --- NUEVA FUNCIÓN PARA MOSTRAR ESTADO CORRECTO ---
function formatStatus(status) {
  if (status === 'Completada') return 'EMITIDO'
  if (status === 'Anulada') return 'ANULADO'
  return status
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">Transferencias y Kardex</h1>
      <Button as-child v-if="activeTab === 'transferencias'">
        <RouterLink to="/inventory/transfers/create">Crear GRE</RouterLink>
      </Button>
    </div>

    <div class="flex space-x-2 border-b">
      <Button :variant="activeTab === 'transferencias' ? 'secondary' : 'ghost'" @click="activeTab = 'transferencias'">Transferencias</Button>
      <Button :variant="activeTab === 'kardex' ? 'secondary' : 'ghost'" @click="activeTab = 'kardex'">Kardex</Button>
    </div>

    <div>
      <div v-if="activeTab === 'transferencias'">
        <div v-if="isLoading" class="flex justify-center p-8"><Loader2 class="animate-spin" /></div>
        <div v-else-if="error" class="text-red-500">{{ error }}</div>
        <Card v-else>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Fecha</TableHead>
                <TableHead>Almacén Origen</TableHead>
                <TableHead>Destino</TableHead>
                <TableHead>Documento</TableHead>
                <TableHead>C.C.</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead class="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-if="transfers.length === 0">
                <TableCell colspan="8" class="text-center py-8 text-gray-500">No hay registros.</TableCell>
              </TableRow>
              <TableRow v-for="transfer in transfers" :key="transfer.id">
                <TableCell class="font-medium">{{ transfer.id }}</TableCell>
                <TableCell class="text-xs">{{ formatDate(transfer.transfer_date) }}</TableCell>
                <TableCell class="text-xs">{{ transfer.origin_warehouse }}</TableCell>
                <TableCell class="text-xs">
                  {{ transfer.destination_warehouse !== 'N/A' ? transfer.destination_warehouse : transfer.destination_external }}
                </TableCell>
                <TableCell>
                  <span v-if="transfer.gre_series" class="font-mono font-bold text-xs text-blue-600">
                    {{ transfer.gre_series }}-{{ transfer.gre_number }}
                  </span>
                  <span v-else class="text-gray-400">-</span>
                </TableCell>
                <TableCell>
                  <Badge variant="outline" class="text-[10px]" v-if="transfer.cost_center">{{ transfer.cost_center }}</Badge>
                </TableCell>

                <TableCell>
                  <Badge
                    :class="transfer.status === 'Anulada' ? 'bg-red-100 text-red-700 hover:bg-red-100' : 'bg-green-100 text-green-700 hover:bg-green-100'"
                    class="text-[10px] border-none"
                  >
                    {{ formatStatus(transfer.status) }}
                  </Badge>
                </TableCell>

                <TableCell class="text-right">
                  <div class="flex justify-end gap-2">
                    <Button
                      v-if="transfer.gre_series"
                      variant="outline"
                      size="icon"
                      class="h-8 w-8"
                      :disabled="downloadingId === transfer.id"
                      @click="downloadPDF(transfer.id, transfer.gre_series, transfer.gre_number)"
                      title="Descargar PDF"
                    >
                      <Loader2 v-if="downloadingId === transfer.id" class="h-4 w-4 animate-spin" />
                      <Download v-else class="h-4 w-4" />
                    </Button>

                    <Button as-child variant="ghost" size="icon" class="h-8 w-8" title="Ver Detalle">
                      <RouterLink :to="`/inventory/transfers/${transfer.id}`">
                        <Eye class="h-4 w-4" />
                      </RouterLink>
                    </Button>

                    <Button
                        v-if="isAdmin && transfer.gre_series && transfer.status !== 'Anulada'"
                        variant="destructive"
                        size="icon"
                        class="h-8 w-8"
                        title="Anular Guía"
                        :disabled="anullingId === transfer.id"
                        @click="handleAnular(transfer)"
                    >
                        <Loader2 v-if="anullingId === transfer.id" class="h-4 w-4 animate-spin" />
                        <Ban v-else class="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>

              </TableRow>
            </TableBody>
          </Table>
        </Card>
      </div>
      <div v-if="activeTab === 'kardex'">
        <KardexView />
      </div>
    </div>
  </div>
</template>