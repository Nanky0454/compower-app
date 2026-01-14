<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PlusCircle, Download } from 'lucide-vue-next'
import TransactionForm from '@/components/treasury/TransactionForm.vue'
import TransactionTable from '@/components/treasury/TransactionTable.vue'

const { getAccessTokenSilently } = useAuth0()

const accounts = ref([])
const transactions = ref([])
const isFormOpen = ref(false)
const isExporting = ref(false)
const activeTab = ref('all')

// Filters
const currentDate = new Date()
const selectedMonth = ref(String(currentDate.getMonth() + 1))
const selectedYear = ref(String(currentDate.getFullYear()))
const selectedTypes = ref(['INGRESO', 'EGRESO'])

const months = [
  { value: '1', label: 'Enero' },
  { value: '2', label: 'Febrero' },
  { value: '3', label: 'Marzo' },
  { value: '4', label: 'Abril' },
  { value: '5', label: 'Mayo' },
  { value: '6', label: 'Junio' },
  { value: '7', label: 'Julio' },
  { value: '8', label: 'Agosto' },
  { value: '9', label: 'Septiembre' },
  { value: '10', label: 'Octubre' },
  { value: '11', label: 'Noviembre' },
  { value: '12', label: 'Diciembre' }
]

const years = computed(() => {
  const current = new Date().getFullYear()
  const yrs = []
  for (let i = current - 2; i <= current + 1; i++) {
    yrs.push(String(i))
  }
  return yrs
})

const filteredTransactions = computed(() => {
  return transactions.value.filter(t => selectedTypes.value.includes(t.type))
})

const monthlyTotals = computed(() => {
  const totals = {}
  
  transactions.value.forEach(t => {
    const currency = t.account_currency || 'PEN'
    if (!totals[currency]) {
      totals[currency] = { income: 0, expense: 0 }
    }
    
    const amount = parseFloat(t.amount)
    if (t.type === 'INGRESO') {
      totals[currency].income += amount
    } else {
      totals[currency].expense += amount
    }
  })
  
  return Object.entries(totals).map(([currency, data]) => ({
    currency,
    income: data.income,
    expense: data.expense,
    balance: data.income - data.expense
  }))
})

function formatCurrency(amount, currency = 'PEN') {
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency: currency }).format(amount)
}

function toggleType(type, checked) {
  if (checked) {
    if (!selectedTypes.value.includes(type)) {
      selectedTypes.value.push(type)
    }
  } else {
    selectedTypes.value = selectedTypes.value.filter(t => t !== type)
  }
}

async function fetchAccounts() {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/accounts`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.ok) {
      accounts.value = await response.json()
    }
  } catch (error) {
    console.error('Error fetching accounts:', error)
  }
}

async function fetchTransactions() {
  try {
    const token = await getAccessTokenSilently()
    
    // Calculate dates
    const year = parseInt(selectedYear.value)
    const month = parseInt(selectedMonth.value)
    const startDate = new Date(year, month - 1, 1)
    const endDate = new Date(year, month, 0) // Last day of month

    const params = new URLSearchParams()
    if (activeTab.value !== 'all') {
      params.append('account_id', activeTab.value)
    }
    
    params.append('start_date', startDate.toISOString().split('T')[0])
    params.append('end_date', endDate.toISOString().split('T')[0])
    
    // Removed type param to fetch all for summary calculation

    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/transactions?${params.toString()}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.ok) {
      transactions.value = await response.json()
    }
  } catch (error) {
    console.error('Error fetching transactions:', error)
  }
}

async function exportToExcel() {
  isExporting.value = true
  try {
    const token = await getAccessTokenSilently()
    
    const year = parseInt(selectedYear.value)
    const month = parseInt(selectedMonth.value)
    const startDate = new Date(year, month - 1, 1)
    const endDate = new Date(year, month, 0)

    const params = new URLSearchParams()
    params.append('start_date', startDate.toISOString().split('T')[0])
    params.append('end_date', endDate.toISOString().split('T')[0])

    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/treasury/export?${params.toString()}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (response.ok) {
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Movimientos_${month}_${year}.xlsx`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } else {
      console.error('Export failed')
    }
  } catch (error) {
    console.error('Error exporting:', error)
  } finally {
    isExporting.value = false
  }
}

function handleTabChange(value) {
  activeTab.value = value
  fetchTransactions()
}

// Watchers for filters
watch([selectedMonth, selectedYear], () => {
  fetchTransactions()
})

onMounted(() => {
  fetchAccounts()
  fetchTransactions()
})
</script>

<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h2 class="text-3xl font-bold tracking-tight">Módulo de Caja</h2>
      <div class="flex items-center gap-2">
        <Button variant="outline" @click="exportToExcel" :disabled="isExporting">
          <Download class="mr-2 h-4 w-4" />
          {{ isExporting ? 'Exportando...' : 'Exportar Excel' }}
        </Button>
        <Button @click="isFormOpen = true">
          <PlusCircle class="mr-2 h-4 w-4" />
          Nuevo Movimiento
        </Button>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-6 bg-card p-4 rounded-lg border shadow-sm">
      <div class="flex items-center gap-4">
        <span class="text-sm font-medium">Mostrar:</span>
        <div class="flex items-center gap-2">
          <Checkbox 
            id="filter-ingreso" 
            :model-value="selectedTypes.includes('INGRESO')"
            @update:model-value="(v) => toggleType('INGRESO', v)"
          />
          <Label for="filter-ingreso" class="cursor-pointer">Ingresos</Label>
        </div>
        <div class="flex items-center gap-2">
          <Checkbox 
            id="filter-egreso" 
            :model-value="selectedTypes.includes('EGRESO')"
            @update:model-value="(v) => toggleType('EGRESO', v)"
          />
          <Label for="filter-egreso" class="cursor-pointer">Egresos</Label>
        </div>
      </div>

      <div class="h-6 w-px bg-border hidden sm:block"></div>

      <div class="flex items-center gap-4">
        <span class="text-sm font-medium">Periodo:</span>
        <Select v-model="selectedMonth">
          <SelectTrigger class="w-[140px]">
            <SelectValue placeholder="Mes" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="m in months" :key="m.value" :value="m.value">
              {{ m.label }}
            </SelectItem>
          </SelectContent>
        </Select>

        <Select v-model="selectedYear">
          <SelectTrigger class="w-[100px]">
            <SelectValue placeholder="Año" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="y in years" :key="y" :value="y">
              {{ y }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>

    <Tabs :default-value="'all'" class="space-y-4" @update:modelValue="handleTabChange">
      <TabsList>
        <TabsTrigger value="all">Resumen General</TabsTrigger>
        <TabsTrigger v-for="acc in accounts" :key="acc.id" :value="String(acc.id)">
          {{ acc.alias || acc.bank_name }}
        </TabsTrigger>
      </TabsList>

      <TabsContent value="all" class="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Todos los Movimientos</CardTitle>
          </CardHeader>
          <CardContent>
            <TransactionTable :transactions="filteredTransactions" />
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent v-for="acc in accounts" :key="acc.id" :value="String(acc.id)">
        <Card>
          <CardHeader>
            <CardTitle>Movimientos - {{ acc.alias || acc.bank_name }}</CardTitle>
          </CardHeader>
          <CardContent>
            <TransactionTable :transactions="filteredTransactions" />
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>

    <!-- Summary Section -->
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <Card v-for="total in monthlyTotals" :key="total.currency">
        <CardHeader class="pb-2">
          <CardTitle class="text-sm font-medium">
            Resumen Mensual ({{ total.currency }})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="space-y-2">
            <div class="flex justify-between text-sm">
              <span class="text-muted-foreground">Ingresos:</span>
              <span class="text-green-600 font-medium">+ {{ formatCurrency(total.income, total.currency) }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-muted-foreground">Egresos:</span>
              <span class="text-red-600 font-medium">- {{ formatCurrency(total.expense, total.currency) }}</span>
            </div>
            <div class="border-t pt-2 mt-2 flex justify-between font-bold">
              <span>Balance:</span>
              <span :class="total.balance >= 0 ? 'text-green-600' : 'text-red-600'">
                {{ formatCurrency(total.balance, total.currency) }}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <TransactionForm 
      v-model:isOpen="isFormOpen" 
      :accounts="accounts"
      @transaction-added="fetchTransactions"
    />
  </div>
</template>
