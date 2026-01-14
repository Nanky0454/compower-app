<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
// import { useToast } from '@/components/ui/toast/use-toast'

const props = defineProps({
  isOpen: Boolean,
  accounts: Array
})

const emit = defineEmits(['update:isOpen', 'transaction-added'])

const { getAccessTokenSilently } = useAuth0()
// const { toast } = useToast()

const form = ref({
  date: new Date().toISOString().substr(0, 10),
  description: '',
  amount: '',
  type: 'INGRESO',
  account_id: null,
  expense_type_id: null,
  income_type_id: null,
  beneficiary_type: null, // 'PROVIDER', 'EMPLOYEE', 'ACCOUNT', 'OTHER'
  beneficiary_provider_id: null,
  beneficiary_employee_id: null,
  beneficiary_account_id: null,
  // Document Fields
  has_document: false,
  document: {
    document_type_id: null,
    series: '',
    number: '',
    issuer_ruc: '',
    issuer_name: '',
    issue_date: new Date().toISOString().substr(0, 10),
    amount: ''
  }
})

const expenseTypes = ref([])
const incomeTypes = ref([])
const documentTypes = ref([])
const providers = ref([])
const employees = ref([])
const beneficiarySearch = ref('')
const isSearching = ref(false)
const isSearchingIssuer = ref(false)

const isExpense = computed(() => form.value.type === 'EGRESO')
const isIncome = computed(() => form.value.type === 'INGRESO')

async function fetchExpenseTypes() {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch('/api/treasury/expense-types', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.ok) {
      expenseTypes.value = await response.json()
    }
  } catch (error) {
    console.error('Error fetching expense types:', error)
  }
}

async function fetchIncomeTypes() {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch('/api/treasury/income-types', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.ok) {
      incomeTypes.value = await response.json()
    }
  } catch (error) {
    console.error('Error fetching income types:', error)
  }
}

async function fetchDocumentTypes() {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch('/api/treasury/document-types', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.ok) {
      documentTypes.value = await response.json()
    }
  } catch (error) {
    console.error('Error fetching document types:', error)
  }
}

// --- Beneficiary Search Logic ---
async function searchBeneficiary() {
  if (!beneficiarySearch.value) return
  isSearching.value = true
  
  try {
    const token = await getAccessTokenSilently()
    
    if (form.value.beneficiary_type === 'PROVIDER') {
      // Check if it looks like a RUC (11 digits)
      if (/^\d{11}$/.test(beneficiarySearch.value)) {
        // Try lookup/create by RUC
        const res = await fetch(`/api/treasury/lookup-provider/${beneficiarySearch.value}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        if (res.ok) {
            const provider = await res.json()
            providers.value = [provider]
            form.value.beneficiary_provider_id = String(provider.id)
            // Auto-select found provider
            return
        }
      }
      
      // Normal search
      const res = await fetch(`/api/treasury/providers?q=${beneficiarySearch.value}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) providers.value = await res.json()
      
    } else if (form.value.beneficiary_type === 'EMPLOYEE') {
      const res = await fetch(`/api/treasury/employees?q=${beneficiarySearch.value}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) employees.value = await res.json()
    }
  } catch (e) {
    console.error(e)
  } finally {
    isSearching.value = false
  }
}

async function searchIssuer() {
    const ruc = form.value.document.issuer_ruc
    if (!ruc || ruc.length !== 11) return
    
    isSearchingIssuer.value = true
    try {
        const token = await getAccessTokenSilently()
        const res = await fetch(`/api/treasury/lookup-provider/${ruc}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        if (res.ok) {
            const data = await res.json()
            form.value.document.issuer_name = data.name || data.razon_social
        }
    } catch (e) {
        console.error(e)
    } finally {
        isSearchingIssuer.value = false
    }
}

// Watch for type changes to reset beneficiary
watch(() => form.value.beneficiary_type, () => {
    form.value.beneficiary_provider_id = null
    form.value.beneficiary_employee_id = null
    form.value.beneficiary_account_id = null
    beneficiarySearch.value = ''
    providers.value = []
    employees.value = []
})

async function handleSubmit() {
  try {
    const token = await getAccessTokenSilently()
    
    // Prepare payload
    const payload = { ...form.value }
    if (!payload.has_document) {
        delete payload.document
    }
    
    const response = await fetch('/api/treasury/transactions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) throw new Error('Error creating transaction')

    // toast({ title: 'Éxito', description: 'Movimiento registrado correctamente' })
    alert('Movimiento registrado correctamente')
    emit('transaction-added')
    emit('update:isOpen', false)
    
    // Reset form
    form.value = {
      date: new Date().toISOString().substr(0, 10),
      description: '',
      amount: '',
      type: 'INGRESO',
      account_id: null,
      expense_type_id: null,
      income_type_id: null,
      beneficiary_type: null,
      beneficiary_provider_id: null,
      beneficiary_employee_id: null,
      beneficiary_account_id: null,
      has_document: false,
      document: {
        document_type_id: null,
        series: '',
        number: '',
        issuer_ruc: '',
        issuer_name: '',
        issue_date: new Date().toISOString().substr(0, 10),
        amount: ''
      }
    }
    beneficiarySearch.value = ''
  } catch (error) {
    // toast({ title: 'Error', description: 'No se pudo registrar el movimiento', variant: 'destructive' })
    alert('Error: No se pudo registrar el movimiento')
  }
}

onMounted(() => {
  fetchExpenseTypes()
  fetchIncomeTypes()
  fetchDocumentTypes()
})
</script>

<template>
  <Dialog :open="isOpen" @update:open="$emit('update:isOpen', $event)">
    <DialogContent :class="form.has_document ? 'sm:max-w-[900px]' : 'sm:max-w-[500px]'">
      <DialogHeader>
        <DialogTitle>Registrar Movimiento</DialogTitle>
      </DialogHeader>
      
      <div class="flex gap-6 py-4">
        <!-- LEFT COLUMN: Main Transaction Data -->
        <div class="flex-1 grid gap-4 content-start">
            <div class="grid grid-cols-4 items-center gap-4">
            <Label for="type" class="text-right">Tipo</Label>
            <Select v-model="form.type">
                <SelectTrigger class="col-span-3">
                <SelectValue placeholder="Seleccione tipo" />
                </SelectTrigger>
                <SelectContent>
                <SelectItem value="INGRESO">Ingreso</SelectItem>
                <SelectItem value="EGRESO">Egreso</SelectItem>
                </SelectContent>
            </Select>
            </div>
            
            <div class="grid grid-cols-4 items-center gap-4">
            <Label for="date" class="text-right">Fecha</Label>
            <Input id="date" type="date" v-model="form.date" class="col-span-3" />
            </div>

            <div class="grid grid-cols-4 items-center gap-4">
            <Label for="account" class="text-right">Cuenta</Label>
            <Select v-model="form.account_id">
                <SelectTrigger class="col-span-3">
                <SelectValue placeholder="Seleccione cuenta" />
                </SelectTrigger>
                <SelectContent>
                <SelectItem v-for="acc in accounts" :key="acc.id" :value="String(acc.id)">
                    {{ acc.alias || acc.bank_name + ' - ' + acc.account_number }}
                </SelectItem>
                </SelectContent>
            </Select>
            </div>

            <div v-if="isExpense" class="grid grid-cols-4 items-center gap-4">
            <Label for="expense_type" class="text-right">Tipo Egreso</Label>
            <Select v-model="form.expense_type_id">
                <SelectTrigger class="col-span-3">
                <SelectValue placeholder="Seleccione tipo de egreso" />
                </SelectTrigger>
                <SelectContent>
                <SelectItem v-for="type in expenseTypes" :key="type.id" :value="String(type.id)">
                    {{ type.name }}
                </SelectItem>
                </SelectContent>
            </Select>
            </div>

            <div v-if="isIncome" class="grid grid-cols-4 items-center gap-4">
            <Label for="income_type" class="text-right">Tipo Ingreso</Label>
            <Select v-model="form.income_type_id">
                <SelectTrigger class="col-span-3">
                <SelectValue placeholder="Seleccione tipo de ingreso" />
                </SelectTrigger>
                <SelectContent>
                <SelectItem v-for="type in incomeTypes" :key="type.id" :value="String(type.id)">
                    {{ type.name }}
                </SelectItem>
                </SelectContent>
            </Select>
            </div>

            <!-- BENEFICIARY SECTION -->
            <div class="border-t pt-4 mt-2">
                <div class="grid grid-cols-4 items-center gap-4 mb-4">
                <Label class="text-right font-semibold">Beneficiario</Label>
                <Select v-model="form.beneficiary_type">
                    <SelectTrigger class="col-span-3">
                    <SelectValue placeholder="Tipo de Beneficiario" />
                    </SelectTrigger>
                    <SelectContent>
                    <SelectItem value="PROVIDER">Proveedor</SelectItem>
                    <SelectItem value="EMPLOYEE">Empleado</SelectItem>
                    <SelectItem value="ACCOUNT">Cuenta Propia</SelectItem>
                    <SelectItem value="OTHER">Otro</SelectItem>
                    </SelectContent>
                </Select>
                </div>

                <!-- Provider Search -->
                <div v-if="form.beneficiary_type === 'PROVIDER'" class="grid grid-cols-4 items-start gap-4">
                    <Label class="text-right pt-2">Buscar</Label>
                    <div class="col-span-3 space-y-2">
                        <div class="flex gap-2">
                            <Input v-model="beneficiarySearch" placeholder="RUC o Nombre" @keyup.enter="searchBeneficiary" />
                            <Button type="button" variant="secondary" @click="searchBeneficiary" :disabled="isSearching">
                                {{ isSearching ? '...' : 'Buscar' }}
                            </Button>
                        </div>
                        <Select v-if="providers.length > 0" v-model="form.beneficiary_provider_id">
                            <SelectTrigger>
                                <SelectValue placeholder="Seleccione Proveedor" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem v-for="p in providers" :key="p.id" :value="String(p.id)">
                                    {{ p.ruc }} - {{ p.name }}
                                </SelectItem>
                            </SelectContent>
                        </Select>
                        <p v-else-if="beneficiarySearch && !isSearching" class="text-xs text-muted-foreground">
                            No se encontraron proveedores. Si ingresa un RUC válido, se creará automáticamente.
                        </p>
                    </div>
                </div>

                <!-- Employee Search -->
                <div v-if="form.beneficiary_type === 'EMPLOYEE'" class="grid grid-cols-4 items-start gap-4">
                    <Label class="text-right pt-2">Buscar</Label>
                    <div class="col-span-3 space-y-2">
                        <div class="flex gap-2">
                            <Input v-model="beneficiarySearch" placeholder="Nombre o DNI" @keyup.enter="searchBeneficiary" />
                            <Button type="button" variant="secondary" @click="searchBeneficiary" :disabled="isSearching">
                                {{ isSearching ? '...' : 'Buscar' }}
                            </Button>
                        </div>
                        <Select v-if="employees.length > 0" v-model="form.beneficiary_employee_id">
                            <SelectTrigger>
                                <SelectValue placeholder="Seleccione Empleado" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem v-for="e in employees" :key="e.id" :value="String(e.id)">
                                    {{ e.first_name }} {{ e.last_name }}
                                </SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                <!-- Account Select -->
                <div v-if="form.beneficiary_type === 'ACCOUNT'" class="grid grid-cols-4 items-center gap-4">
                    <Label class="text-right">Cuenta</Label>
                    <Select v-model="form.beneficiary_account_id">
                        <SelectTrigger class="col-span-3">
                            <SelectValue placeholder="Seleccione Cuenta Destino" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem v-for="acc in accounts" :key="acc.id" :value="String(acc.id)">
                                {{ acc.alias || acc.bank_name + ' - ' + acc.account_number }}
                            </SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            </div>

            <div class="grid grid-cols-4 items-center gap-4 mt-2 border-t pt-4">
                <Label for="description" class="text-right">Descripción</Label>
                <Input id="description" v-model="form.description" class="col-span-3" />
            </div>

            <div class="grid grid-cols-4 items-center gap-4">
                <Label for="amount" class="text-right">Monto</Label>
                <Input id="amount" type="number" step="0.01" v-model="form.amount" class="col-span-3" />
            </div>

            <!-- Toggle Document -->
            <div class="flex items-center space-x-2 mt-2 pt-2 border-t">
                <input type="checkbox" id="has_document" v-model="form.has_document" class="rounded border-gray-300 text-primary focus:ring-primary" />
                <Label for="has_document" class="font-semibold cursor-pointer">Registrar Comprobante</Label>
            </div>
        </div>

        <!-- RIGHT COLUMN: Document Data -->
        <div v-if="form.has_document" class="flex-1 grid gap-4 border-l pl-6 content-start">
            <h3 class="font-semibold text-lg mb-2">Datos del Comprobante</h3>
            
            <div class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">Tipo Doc.</Label>
                <Select v-model="form.document.document_type_id">
                    <SelectTrigger class="col-span-3">
                        <SelectValue placeholder="Seleccione Tipo" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem v-for="dt in documentTypes" :key="dt.id" :value="String(dt.id)">
                            {{ dt.name }}
                        </SelectItem>
                    </SelectContent>
                </Select>
            </div>

            <div class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">Serie / Nro</Label>
                <div class="col-span-3 flex gap-2">
                    <Input v-model="form.document.series" placeholder="Serie" class="w-1/3" />
                    <Input v-model="form.document.number" placeholder="Número" class="w-2/3" />
                </div>
            </div>

            <div class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">RUC Emisor</Label>
                <div class="col-span-3 flex gap-2">
                    <Input v-model="form.document.issuer_ruc" placeholder="RUC" @blur="searchIssuer" @keyup.enter="searchIssuer" />
                    <Button type="button" variant="ghost" size="sm" @click="searchIssuer" :disabled="isSearchingIssuer">
                        🔍
                    </Button>
                </div>
            </div>

            <div class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">Razón Social</Label>
                <Input v-model="form.document.issuer_name" class="col-span-3" placeholder="Nombre del Emisor" />
            </div>

            <div class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">Fecha Emisión</Label>
                <Input type="date" v-model="form.document.issue_date" class="col-span-3" />
            </div>
            
            <div class="grid grid-cols-4 items-center gap-4">
                <Label class="text-right">Monto Doc.</Label>
                <Input type="number" step="0.01" v-model="form.document.amount" class="col-span-3" placeholder="Monto del comprobante" />
            </div>
        </div>
      </div>

      <DialogFooter>
        <Button type="submit" @click="handleSubmit">Guardar</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
