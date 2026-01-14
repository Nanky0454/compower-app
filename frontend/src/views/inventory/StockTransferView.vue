<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Button } from '@/components/ui/button/index.js'
import { Badge } from '@/components/ui/badge/index.js'
import { RouterLink } from 'vue-router'
// --- CAMBIO 1: Importar iconos adicionales ---
import { Eye, Download, Loader2 } from 'lucide-vue-next'
import KardexView from './KardexView.vue'

const activeTab = ref('transferencias')

const { getAccessTokenSilently } = useAuth0()
const transfers = ref([])
const isLoading = ref(true)
const error = ref(null)

// --- CAMBIO 2: Estado para saber qué ID se está descargando ---
const downloadingId = ref(null)

async function fetchTransfers() {
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

// --- CAMBIO 3: Función de Descarga ---
async function downloadPDF(transferId, serie, numero) {
  if (!transferId) return

  try {
    downloadingId.value = transferId // Activamos spinner para este ID
    const token = await getAccessTokenSilently()

    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/gre/download-pdf/${transferId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (!response.ok) throw new Error('Error al generar el PDF')

    // Procesar el archivo binario (Blob)
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)

    // Crear enlace temporal y descargar
    const a = document.createElement('a')
    a.href = url
    a.download = `GRE-${serie}-${numero}.pdf`
    document.body.appendChild(a)
    a.click()

    // Limpieza
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)

  } catch (e) {
    console.error(e)
    alert("No se pudo descargar el PDF. Verifique que la guía exista.")
  } finally {
    downloadingId.value = null // Desactivamos spinner
  }
}

onMounted(fetchTransfers)

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const options = { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }
  return new Date(dateString).toLocaleString('es-ES', options)
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-3xl font-bold">
        Transferencias y Kardex
      </h1>
      <Button as-child v-if="activeTab === 'transferencias'">
        <RouterLink to="/inventory/transfers/create">
          Crear GRE
        </RouterLink>
      </Button>
    </div>

    <div class="flex space-x-2 border-b">
      <Button :variant="activeTab === 'transferencias' ? 'secondary' : 'ghost'" @click="activeTab = 'transferencias'">
        Transferencias
      </Button>
      <Button :variant="activeTab === 'kardex' ? 'secondary' : 'ghost'" @click="activeTab = 'kardex'">
        Kardex
      </Button>
    </div>

    <div>
      <div v-if="activeTab === 'transferencias'">
        <div v-if="isLoading">Cargando transferencias...</div>
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
                <TableHead>Estado</TableHead>
                <TableHead class="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-if="transfers.length === 0">
                <TableCell colspan="7" class="text-center">No se han realizado transferencias.</TableCell>
              </TableRow>
              <TableRow v-for="transfer in transfers" :key="transfer.id">
                <TableCell class="font-medium">{{ transfer.id }}</TableCell>
                <TableCell>{{ formatDate(transfer.transfer_date) }}</TableCell>
                <TableCell>{{ transfer.origin_warehouse }}</TableCell>
                <TableCell>
                  {{ transfer.destination_warehouse !== 'N/A' ? transfer.destination_warehouse : transfer.destination_external }}
                </TableCell>
                <TableCell>
                  <span v-if="transfer.gre_series">{{ transfer.gre_series }}-{{ transfer.gre_number }}</span>
                  <span v-else>-</span>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">
                    {{ transfer.status }}
                  </Badge>
                </TableCell>

                <TableCell class="text-right">
                  <div class="flex justify-end gap-2">

                    <Button
                      v-if="transfer.gre_series"
                      variant="outline"
                      size="icon"
                      :disabled="downloadingId === transfer.id"
                      @click="downloadPDF(transfer.id, transfer.gre_series, transfer.gre_number)"
                      title="Descargar PDF"
                    >
                      <Loader2 v-if="downloadingId === transfer.id" class="h-4 w-4 animate-spin" />
                      <Download v-else class="h-4 w-4" />
                    </Button>

                    <Button as-child variant="ghost" size="icon" title="Ver Detalle">
                      <RouterLink :to="`/inventory/transfers/${transfer.id}`">
                        <Eye class="h-4 w-4" />
                      </RouterLink>
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