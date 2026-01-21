<script setup>
import { ref, onMounted, computed, h, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { useRouter } from 'vue-router' // <--- 1. Importar useRouter
import {
  useVueTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  FlexRender,
} from '@tanstack/vue-table'
import * as XLSX from 'xlsx'

// Importar componentes de UI
import { Card } from '@/components/ui/card/index.js'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table/index.js'
import { Input } from '@/components/ui/input/index.js'
import { Button } from '@/components/ui/button/index.js'
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger, DropdownMenuItem, DropdownMenuSeparator } from '@/components/ui/dropdown-menu/index.js'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select/index.js'
import { Dialog, DialogTrigger } from '@/components/ui/dialog'
import { ArrowUpDown, ChevronDown, FileDown, Tags, Plus } from 'lucide-vue-next' // Plus ya estaba importado
import LabelGenerator from '@/views/inventory/components/LabelGenerator.vue'

const { getAccessTokenSilently } = useAuth0()
const router = useRouter() // <--- 2. Inicializar router

// --- State ---
const data = ref([])
const warehouses = ref([])
const categories = ref([])
const isLoading = ref(true)
const error = ref(null)
const showLabelGeneratorDialog = ref(false)

// --- Table State ---
const sorting = ref([])
const columnFilters = ref([])
const globalFilter = ref('')

const columnVisibility = ref({
  product_location: false,
})
const pagination = ref({
  pageIndex: 0,
  pageSize: 15,
})

// --- Estado de Selección de Categorías ---
const selectedCategoryIds = ref([]);

// --- Column Definitions ---
const columns = [
  {
    accessorKey: 'product_sku',
    header: ({ column }) => h(Button, {
      variant: 'ghost',
      onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
    }, () => ['SKU', h(ArrowUpDown, { class: 'ml-2 h-4 w-4' })]),
    label: 'SKU',
  },
  {
    accessorKey: 'product_name',
    header: 'Producto',
    label: 'Producto',
  },
  {
    accessorKey: 'warehouse_name',
    header: 'Almacén',
    label: 'Almacén',
  },
  {
    accessorKey: 'product_location',
    header: 'Ubicación',
    label: 'Ubicación',
  },
  {
    accessorKey: 'category_name',
    header: 'Categoría',
    label: 'Categoría',
    filterFn: (row, columnId, filterValue) => {
      if (!filterValue || filterValue.length === 0) return true
      return filterValue.includes(row.getValue(columnId))
    },
    enableMultiSort: true,
  },
  {
    accessorKey: 'quantity',
    header: ({ column }) => h(Button, {
      variant: 'ghost',
      onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
    }, () => ['Cantidad', h(ArrowUpDown, { class: 'ml-2 h-4 w-4' })]),
    cell: ({ row }) => h('div', { class: 'text-center' }, new Intl.NumberFormat('es-ES').format(row.getValue('quantity'))),
    label: 'Cantidad',
  },
  {
    accessorKey: 'unit_price',
    header: ({ column }) => h(Button, {
      variant: 'ghost',
      onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
    }, () => ['Costo Unit.', h(ArrowUpDown, { class: 'ml-2 h-4 w-4' })]),
    cell: ({ row }) => h('div', { class: 'text-center font-medium' }, new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(row.getValue('unit_price'))),
    label: 'Costo Unit.',
  },
  {
    accessorKey: 'total_value',
    header: ({ column }) => h(Button, {
      variant: 'ghost',
      onClick: () => column.toggleSorting(column.getIsSorted() === 'asc'),
    }, () => ['Valor Total', h(ArrowUpDown, { class: 'ml-2 h-4 w-4' })]),
    cell: ({ row }) => h('div', { class: 'text-center font-medium' }, new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(row.getValue('total_value'))),
    label: 'Valor Total',
  },
]

// --- Table Instance ---
const table = useVueTable({
  get data() { return data.value },
  columns,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel(),
  getFilteredRowModel: getFilteredRowModel(),
  getPaginationRowModel: getPaginationRowModel(),
  state: {
    get sorting() { return sorting.value },
    get columnFilters() { return columnFilters.value },
    get columnVisibility() { return columnVisibility.value },
    get pagination() { return pagination.value },
    get globalFilter() { return globalFilter.value },
  },
  globalFilterFn: (row, columnId, filterValue) => {
    const search = filterValue.toLowerCase()
    const sku = String(row.original.product_sku ?? '').toLowerCase()
    const name = String(row.original.product_name ?? '').toLowerCase()
    return sku.includes(search) || name.includes(search)
  },
  onSortingChange: (updaterOrValue) => sorting.value = typeof updaterOrValue === 'function' ? updaterOrValue(sorting.value) : updaterOrValue,
  onColumnFiltersChange: (updaterOrValue) => columnFilters.value = typeof updaterOrValue === 'function' ? updaterOrValue(columnFilters.value) : updaterOrValue,
  onColumnVisibilityChange: (updaterOrValue) => columnVisibility.value = typeof updaterOrValue === 'function' ? updaterOrValue(columnVisibility.value) : updaterOrValue,
  onPaginationChange: (updaterOrValue) => pagination.value = typeof updaterOrValue === 'function' ? updaterOrValue(pagination.value) : updaterOrValue,
  onGlobalFilterChange: (updaterOrValue) => globalFilter.value = typeof updaterOrValue === 'function' ? updaterOrValue(globalFilter.value) : updaterOrValue,
})

// --- Data Fetching ---
onMounted(async () => {
  try {
    const token = await getAccessTokenSilently()
    const [reportRes, whRes, catRes] = await Promise.all([
      fetch(`${import.meta.env.VITE_API_URL}/api/inventory/stock-report`, { headers: { 'Authorization': `Bearer ${token}` } }),
      fetch(`${import.meta.env.VITE_API_URL}/api/warehouses`, { headers: { 'Authorization': `Bearer ${token}` } }),
      fetch(`${import.meta.env.VITE_API_URL}/api/categories`, { headers: { 'Authorization': `Bearer ${token}` } })
    ])
    if (!reportRes.ok) throw new Error('No se pudo cargar el reporte.')
    if (!whRes.ok) throw new Error('No se pudieron cargar los almacenes.')
    if (!catRes.ok) throw new Error('No se pudieron cargar las categorías.')

    data.value = await reportRes.json()
    warehouses.value = await whRes.json()
    categories.value = await catRes.json()
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})

// --- Computed Properties ---
const totalValue = computed(() => {
  const total = table.getFilteredRowModel().rows.reduce((sum, row) => sum + row.original.total_value, 0)
  return new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(total)
})

function handleWarehouseFilterChange(value) {
  const filterValue = value === 'all' ? null : value
  table.getColumn('warehouse_name')?.setFilterValue(filterValue)
}

// =========================================================
//  LÓGICA DE CATEGORÍAS
// =========================================================

const nestedCategories = computed(() => {
  const list = JSON.parse(JSON.stringify(categories.value))
  const map = {}
  const tree = []
  list.forEach(item => { map[item.id] = { ...item, children: [] } })
  list.forEach(item => {
    if (item.parent_id && map[item.parent_id]) {
      map[item.parent_id].children.push(map[item.id])
    } else if (!item.parent_id) {
      tree.push(map[item.id])
    }
  })
  return tree
})

const getAllDescendantIds = (category) => {
    let ids = []
    if (category.children && category.children.length > 0) {
        category.children.forEach(child => {
            ids.push(child.id)
            ids = [...ids, ...getAllDescendantIds(child)]
        })
    }
    return ids
}

const findParentOf = (childId, nodes = nestedCategories.value) => {
    for (const node of nodes) {
        if (node.children && node.children.some(c => c.id === childId)) {
            return node;
        }
        if (node.children) {
            const found = findParentOf(childId, node.children);
            if (found) return found;
        }
    }
    return null;
}

const handleToggle = (category) => {
    const categoryId = category.id;
    const isSelected = selectedCategoryIds.value.includes(categoryId);

    const descendants = getAllDescendantIds(category);
    const idsToModify = [categoryId, ...descendants];

    if (isSelected) {
        selectedCategoryIds.value = selectedCategoryIds.value.filter(id => !idsToModify.includes(id));
        let currentId = categoryId;
        let parent = findParentOf(currentId);
        while (parent) {
            const parentIndex = selectedCategoryIds.value.indexOf(parent.id);
            if (parentIndex > -1) {
                selectedCategoryIds.value.splice(parentIndex, 1);
            }
            currentId = parent.id;
            parent = findParentOf(currentId);
        }

    } else {
        idsToModify.forEach(id => {
            if (!selectedCategoryIds.value.includes(id)) selectedCategoryIds.value.push(id);
        });
        let currentId = categoryId;
        let parent = findParentOf(currentId);
        while (parent) {
            const allSiblingsSelected = parent.children.every(c => selectedCategoryIds.value.includes(c.id));
            if (allSiblingsSelected && !selectedCategoryIds.value.includes(parent.id)) {
                selectedCategoryIds.value.push(parent.id);
            }
            currentId = parent.id;
            parent = findParentOf(currentId);
        }
    }
};

const isCategorySelected = (id) => selectedCategoryIds.value.includes(id);

watch(selectedCategoryIds, (newIds) => {
    const selectedNames = categories.value
        .filter(c => newIds.includes(c.id))
        .map(c => c.name);
    const column = table.getColumn('category_name');
    if (column) {
        column.setFilterValue(selectedNames.length > 0 ? selectedNames : undefined);
    }
}, { deep: true });

function downloadExcel() {
  const filteredRows = table.getFilteredRowModel().rows;
  if (filteredRows.length === 0) {
    alert('No hay datos en la tabla para exportar.');
    return;
  }

  const dataToExport = filteredRows.map(row => {
    return {
      'SKU': row.original.product_sku,
      'Producto': row.original.product_name,
      'Almacén': row.original.warehouse_name,
      'Categoría': row.original.category_name,
      'Cantidad': row.original.quantity,
      'Costo Unit.': row.original.unit_price,
      'Valor Total': row.original.total_value
    };
  });

  const worksheet = XLSX.utils.json_to_sheet(dataToExport);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'ReporteStock');
  const fileName = `Reporte_Stock_${new Date().toISOString().slice(0, 10)}.xlsx`;
  XLSX.writeFile(workbook, fileName);
}

</script>

<template>
  <div class="space-y-4">
    <h1 class="text-3xl font-bold print:hidden">Reportes y Maestro de Stock</h1>

    <div class="flex items-center justify-between print:hidden">
      <div class="flex items-center gap-2">
        <Input
          class="max-w-sm w-[300px]"
          placeholder="Buscar por SKU o Producto..."
          :model-value="globalFilter"
          @update:model-value="globalFilter = $event"
        />

        <Input
          class="max-w-sm"
          placeholder="Filtrar por ubicación..."
          :model-value="table.getColumn('product_location')?.getFilterValue()"
          @update:model-value="table.getColumn('product_location')?.setFilterValue($event)"
        />

        <Select @update:model-value="handleWarehouseFilterChange">
          <SelectTrigger class="w-[180px]">
            <SelectValue placeholder="Todos los Almacenes" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los Almacenes</SelectItem>
            <SelectItem v-for="wh in warehouses" :key="wh.id" :value="wh.name">
              {{ wh.name }}
            </SelectItem>
          </SelectContent>
        </Select>

        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button variant="outline" class="ml-auto">
              Categorías <ChevronDown class="ml-2 h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" class="max-h-[400px] overflow-y-auto">
            <template v-for="level1 in nestedCategories" :key="level1.id">
                <DropdownMenuItem class="flex items-center justify-between p-2 cursor-pointer hover:bg-gray-100">
                    <input type="checkbox" :checked="isCategorySelected(level1.id)" @click.stop="handleToggle(level1)" class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"/>
                    <span @click.prevent="handleToggle(level1)" class="capitalize font-bold flex-grow ml-2">{{ level1.name }}</span>
                </DropdownMenuItem>
                <template v-for="level2 in level1.children" :key="level2.id">
                    <DropdownMenuItem class="flex items-center justify-between p-2 ml-4 cursor-pointer hover:bg-gray-100">
                        <input type="checkbox" :checked="isCategorySelected(level2.id)" @click.stop="handleToggle(level2)" class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"/>
                        <span @click.prevent="handleToggle(level2)" class="capitalize flex-grow ml-2 font-medium">{{ level2.name }}</span>
                    </DropdownMenuItem>
                    <DropdownMenuItem v-for="level3 in level2.children" :key="level3.id" class="flex items-center justify-between p-2 ml-8 cursor-pointer hover:bg-gray-100">
                        <input type="checkbox" :checked="isCategorySelected(level3.id)" @click.stop="handleToggle(level3)" class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"/>
                        <span @click.prevent="handleToggle(level3)" class="capitalize flex-grow ml-2 text-gray-600">{{ level3.name }}</span>
                    </DropdownMenuItem>
                </template>
                <DropdownMenuSeparator />
            </template>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div class="flex items-center gap-2">
        <Button
          @click="router.push({ name: 'RegisterInventoryView' })"
          class="bg-blue-600 hover:bg-blue-700 text-white"
        >
          <Plus class="mr-2 h-4 w-4" />
          Registrar Inventario
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button variant="outline" class="ml-auto">
              Columnas <ChevronDown class="ml-2 h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              v-for="column in table.getAllColumns().filter((column) => column.getCanHide())"
              :key="column.id"
              class="flex items-center space-x-2"
            >
              <input
                type="checkbox"
                :id="`column-toggle-${column.id}`"
                :checked="column.getIsVisible()"
                @change="(e) => column.toggleVisibility(e.target.checked)"
                @click.stop
                class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
              />
              <label :for="`column-toggle-${column.id}`" class="text-sm cursor-pointer" @click.stop>
                {{ column.columnDef.label }}
              </label>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Button variant="outline" @click="downloadExcel">
          <FileDown class="mr-2 h-4 w-4" />
          Descargar Excel
        </Button>

        <Dialog v-model:open="showLabelGeneratorDialog">
          <DialogTrigger as-child>
            <Button variant="outline">
              <Tags class="mr-2 h-4 w-4" />
              Generar Etiquetas
            </Button>
          </DialogTrigger>
          <LabelGenerator />
        </Dialog>
      </div>
    </div>

    <div v-if="isLoading">Cargando reporte...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <Card v-else class="print:border-none print:shadow-none print:overflow-visible print:block overflow-hidden">
      <div class="relative w-full overflow-auto print:overflow-visible print:h-auto">
        <Table class="w-full text-sm">
          <TableHeader>
            <TableRow v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id" class="print:border-b-2 print:border-black">
              <TableHead
                v-for="header in headerGroup.headers"
                :key="header.id"
                class="text-center print:text-black print:font-bold print:whitespace-normal"
              >
                <FlexRender
                  v-if="!header.isPlaceholder"
                  :render="header.column.columnDef.header"
                  :props="header.getContext()"
                />
              </TableHead>
            </TableRow>
          </TableHeader>
         <TableBody>
            <template v-if="table.getRowModel().rows?.length">
              <TableRow
                v-for="row in table.getRowModel().rows"
                :key="row.id"
                :data-state="row.getIsSelected() && 'selected'"
                class="print:border-b print:border-gray-300 justify-center"
              >
                <TableCell
                    v-for="cell in row.getVisibleCells()"
                    :key="cell.id"
                    class="print:p-1 print:align-top print:whitespace-normal print:break-words print:text-xs"
                    :class="{
                        'whitespace-normal min-w-[250px]': cell.column.id === 'product_name',
                        'whitespace-normal min-w-[150px]': cell.column.id === 'product_location'
                    }"
                >
                  <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
                </TableCell>
              </TableRow>
            </template>
            <template v-else>
              <TableRow>
                <TableCell :colspan="table.getAllColumns().length" class="h-24 text-center print:p-1">
                  No hay resultados.
                </TableCell>
              </TableRow>
            </template>
          </TableBody>
        </Table>
      </div>
    </Card>

    <div class="flex items-center justify-between py-4 print:hidden">
      <div class="flex-1 text-sm text-muted-foreground">
        {{ table.getFilteredRowModel().rows.length }} de {{ data.length }} fila(s) totales.
      </div>
      <div class="font-bold text-lg hidden sm:block">
        Valor Total Filtrado: {{ totalValue }}
      </div>
      <div class="flex items-center space-x-2">
        <Button
          variant="outline"
          size="sm"
          :disabled="!table.getCanPreviousPage()"
          @click="table.previousPage()"
        >
          Anterior
        </Button>
        <span class="text-sm">
          Página {{ table.getState().pagination.pageIndex + 1 }} de {{ table.getPageCount() }}
        </span>
        <Button
          variant="outline"
          size="sm"
          :disabled="!table.getCanNextPage()"
          @click="table.nextPage()"
        >
          Siguiente
        </Button>
      </div>
    </div>
  </div>
</template>

<style>
@media print {
  @page {
    size: landscape;
    margin: 10mm;
  }

  body {
    background-color: white !important;
    color: black !important;
  }

  * {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
}
</style>