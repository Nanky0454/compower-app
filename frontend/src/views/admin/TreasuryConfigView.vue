 <script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Pencil, Trash2, Plus } from 'lucide-vue-next'

const { getAccessTokenSilently } = useAuth0()

const activeTab = ref('account-types')
const items = ref([])
const banks = ref([])
const accountTypes = ref([])
const isModalOpen = ref(false)
const isEditing = ref(false)

const form = ref({})

// --- API Helpers ---
const apiBase = '/api/treasury'

const fetchItems = async () => {
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${apiBase}/${activeTab.value}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) items.value = await res.json()
  } catch (error) {
    console.error(error)
  }
}

const fetchDependencies = async () => {
    try {
        const token = await getAccessTokenSilently()
        const [resBanks, resTypes] = await Promise.all([
            fetch(`${apiBase}/banks`, { headers: { Authorization: `Bearer ${token}` } }),
            fetch(`${apiBase}/account-types`, { headers: { Authorization: `Bearer ${token}` } })
        ])
        if (resBanks.ok) banks.value = await resBanks.json()
        if (resTypes.ok) accountTypes.value = await resTypes.json()
    } catch (e) { console.error(e) }
}

const saveItem = async () => {
  try {
    const token = await getAccessTokenSilently()
    const method = isEditing.value ? 'PUT' : 'POST'
    const url = isEditing.value ? `${apiBase}/${activeTab.value}/${form.value.id}` : `${apiBase}/${activeTab.value}`
    
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(form.value)
    })

    if (!res.ok) throw new Error('Error saving item')
    
    await fetchItems()
    closeModal()
  } catch (error) {
    alert(error.message)
  }
}

const deleteItem = async (id) => {
  if (!confirm('¿Eliminar elemento?')) return
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch(`${apiBase}/${activeTab.value}/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) throw new Error('Error deleting item')
    await fetchItems()
  } catch (error) {
    alert(error.message)
  }
}

// --- UI Helpers ---
const openCreateModal = () => {
  isEditing.value = false
  form.value = {}
  if (activeTab.value === 'bank-accounts') fetchDependencies()
  isModalOpen.value = true
}

const openEditModal = (item) => {
  isEditing.value = true
  form.value = { ...item }
  if (activeTab.value === 'bank-accounts') fetchDependencies()
  isModalOpen.value = true
}

const closeModal = () => {
  isModalOpen.value = false
}

const handleTabChange = (val) => {
    activeTab.value = val
    fetchItems()
}

onMounted(() => {
  fetchItems()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <div>
        <h2 class="text-3xl font-bold tracking-tight">Configuración de Caja</h2>
        <p class="text-muted-foreground">Gestiona los catálogos de tesorería.</p>
      </div>
      <Button @click="openCreateModal">
        <Plus class="mr-2 h-4 w-4" /> Nuevo
      </Button>
    </div>

    <Tabs default-value="account-types" class="w-full" @update:modelValue="handleTabChange">
      <TabsList>
        <TabsTrigger value="account-types">Tipos de Cuenta</TabsTrigger>
        <TabsTrigger value="banks">Bancos</TabsTrigger>
        <TabsTrigger value="bank-accounts">Cuentas Bancarias</TabsTrigger>
        <TabsTrigger value="expense-types">Tipos de Egreso</TabsTrigger>
        <TabsTrigger value="income-types">Tipos de Ingreso</TabsTrigger>
      </TabsList>

      <!-- Generic Table Wrapper -->
      <div class="border rounded-md mt-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead v-if="activeTab === 'account-types' || activeTab === 'banks' || activeTab === 'expense-types' || activeTab === 'income-types'">Nombre</TableHead>
              <TableHead v-if="activeTab === 'expense-types' || activeTab === 'income-types'">Sigla</TableHead>
              
              <TableHead v-if="activeTab === 'bank-accounts'">Banco</TableHead>
              <TableHead v-if="activeTab === 'bank-accounts'">Tipo</TableHead>
              <TableHead v-if="activeTab === 'bank-accounts'">Moneda</TableHead>
              <TableHead v-if="activeTab === 'bank-accounts'">Número</TableHead>
              <TableHead v-if="activeTab === 'bank-accounts'">Alias</TableHead>
              
              <TableHead class="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="item in items" :key="item.id">
              <TableCell v-if="activeTab === 'account-types' || activeTab === 'banks' || activeTab === 'expense-types' || activeTab === 'income-types'">{{ item.name }}</TableCell>
              <TableCell v-if="activeTab === 'expense-types' || activeTab === 'income-types'">{{ item.acronym }}</TableCell>

              <TableCell v-if="activeTab === 'bank-accounts'">{{ item.bank_name }}</TableCell>
              <TableCell v-if="activeTab === 'bank-accounts'">{{ item.account_type_name }}</TableCell>
              <TableCell v-if="activeTab === 'bank-accounts'">{{ item.currency }}</TableCell>
              <TableCell v-if="activeTab === 'bank-accounts'">{{ item.account_number }}</TableCell>
              <TableCell v-if="activeTab === 'bank-accounts'">{{ item.alias }}</TableCell>

              <TableCell class="text-right">
                <Button variant="ghost" size="icon" @click="openEditModal(item)">
                  <Pencil class="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" class="text-red-600" @click="deleteItem(item.id)">
                  <Trash2 class="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </Tabs>

    <Dialog :open="isModalOpen" @update:open="isModalOpen = $event">
      <DialogContent class="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{{ isEditing ? 'Editar' : 'Crear' }} Elemento</DialogTitle>
        </DialogHeader>
        <div class="grid gap-4 py-4">
            
          <!-- Fields for Account Types & Banks -->
          <div v-if="activeTab === 'account-types' || activeTab === 'banks' || activeTab === 'expense-types' || activeTab === 'income-types'" class="grid grid-cols-4 items-center gap-4">
            <Label class="text-right">Nombre</Label>
            <Input v-model="form.name" class="col-span-3" />
          </div>

          <!-- Fields for Expense/Income Types -->
          <div v-if="activeTab === 'expense-types' || activeTab === 'income-types'" class="grid grid-cols-4 items-center gap-4">
            <Label class="text-right">Sigla</Label>
            <Input v-model="form.acronym" class="col-span-3" placeholder="Ej: VIA" />
          </div>

          <!-- Fields for Bank Accounts -->
          <template v-if="activeTab === 'bank-accounts'">
              <div class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">Banco</Label>
                <Select v-model="form.bank_id">
                  <SelectTrigger class="col-span-3">
                    <SelectValue placeholder="Seleccione Banco" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="b in banks" :key="b.id" :value="String(b.id)">{{ b.name }}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">Tipo</Label>
                <Select v-model="form.account_type_id">
                  <SelectTrigger class="col-span-3">
                    <SelectValue placeholder="Seleccione Tipo" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem v-for="t in accountTypes" :key="t.id" :value="String(t.id)">{{ t.name }}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">Moneda</Label>
                <Select v-model="form.currency">
                  <SelectTrigger class="col-span-3">
                    <SelectValue placeholder="Seleccione Moneda" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PEN">Soles (PEN)</SelectItem>
                    <SelectItem value="USD">Dólares (USD)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">Número</Label>
                <Input v-model="form.account_number" class="col-span-3" />
              </div>
              <div class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">Alias</Label>
                <Input v-model="form.alias" class="col-span-3" placeholder="Opcional" />
              </div>
          </template>

        </div>
        <DialogFooter>
          <Button type="submit" @click="saveItem">Guardar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
