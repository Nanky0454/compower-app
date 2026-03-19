import { createRouter, createWebHistory } from 'vue-router'

// --- ¡RUTAS DE IMPORTACIÓN ACTUALIZADAS! ---
import HomeView from '@/views/HomeView.vue'

import AdminPanel from '@/views/admin/AdminPanel.vue'

import CostCentersView from '../views/cost_centers/CostCentersView.vue'
import SitesView from '../views/projects/SitesView.vue' // <-- Importar vista de Sites
import UbigeoConfigView from '../views/admin/UbigeoConfigView.vue' // <-- Importar vista de Ubigeo
import UnitsConfigView  from "@/views/admin/UnitsConfigView.vue";

import PurchasesView from '@/views/purchasing/PurchasesView.vue'
import PurchaseDetailView from '@/views/purchasing/PurchaseDetailView.vue'
import EditPurchaseView from '@/views/purchasing/EditPurchaseView.vue'

import CatalogCategoriesView from '@/views/catalog/CatalogCategoriesView.vue'
import CatalogProductsView from '@/views/catalog/CatalogProductsView.vue'

import InventoryView from '@/views/inventory/InventoryView.vue'
import InventoryReceiveView from '@/views/inventory/InventoryReceiveView.vue'
import StockReportView from '@/views/inventory/StockReportView.vue'
import StockTransferView from '@/views/inventory/StockTransferView.vue'
import StockTransferReportView from '@/views/inventory/StockTransferReportView.vue'
import CreateTransferView from '@/views/inventory/CreateTransferView.vue'
import WarehouseView from '@/views/inventory/WarehouseView.vue'
import InventoryAdjustmentView from '@/views/inventory/InventoryAdjustmentView.vue'
import TreasuryConfigView from "@/views/admin/TreasuryConfigView.vue";
import RegisterInventoryView from "@/views/inventory/RegisterInventoryView.vue";
import ProviderListView from "@/views/purchasing/ProviderList.vue"
import CostCenterDetailView from "@/views/cost_centers/CostCenterDetailView.vue";

const routes = [
  {
    path: '/',
    name: 'Home',
    component: HomeView,
    meta: { title: 'Novedades' }
  },
  // Admin
  {
    path: '/admin',
    name: 'Admin',
    component: AdminPanel,
    meta: { title: 'Admin Panel' }
  },
  // Centros de Costos
  {
    path: '/cost-centers',
    name: 'cost-centers',
    component: CostCentersView,
    meta: { title: 'Centros de Costos' }
  },
    {
    path: '/cost-centers/:id',
    name: 'cost-centers-detail',
    component: CostCenterDetailView,
    meta: { title: 'Detalle de centro de costo' }
  },
  {
    path: '/projects/sites',
    name: 'sites',
    component: SitesView,
    meta: { title: 'Gestión de Sites' }
  },
  {
    path: '/admin/config/ubigeo',
    name: 'ubigeo-config',
    component: UbigeoConfigView,
    meta: { title: 'Configuración de Ubigeos' }
  },
  {
    path: '/admin/config/treasury',
    name: 'treasury-config',
    component: TreasuryConfigView,
    meta: { title: 'Configuración de Tesorería' }
  },{
    path: '/admin/config/unit_measure',
    name: 'units-config',
    component: UnitsConfigView,
    meta: { title: 'Configuración de Unidades' }
  },
  // Compras
  {
    path: '/purchases',
    name: 'Purchases',
    component: PurchasesView,
    meta: { title: 'Módulo de Compras' }
  },
  {
    path: '/purchases/:id',
    name: 'PurchaseDetail',
    component: PurchaseDetailView,
    meta: { title: 'Detalle de Compra' }
  },
    {
    path: '/purchases/:id/edit',
    name: 'EditPurchase',
    component: EditPurchaseView,
    meta: { title: 'Editar Orden' }
  },
  // Catálogo
  {
    path: '/catalog/categories',
    name: 'Categories',
    component: CatalogCategoriesView,
    meta: { title: 'Gestión de Categorías' }
  },
  {
    path: '/catalog/products',
    name: 'Products',
    component: CatalogProductsView,
    meta: { title: 'Gestión de Productos' }
  },
  // Inventario
  {
    path: '/inventory/warehouses',
    name: 'Warehouses',
    component: WarehouseView,
    meta: { title: 'Gestión de Almacenes' }
  },
  {
    path: '/inventory',
    name: 'Inventory',
    component: InventoryView,
    meta: { title: 'Recepcion' }
  },
  {
    path: '/inventory/receive/:id',
    name: 'InventoryReceive',
    component: InventoryReceiveView,
    meta: { title: 'Recepcionar Orden' }
  },
  {
    path: '/purchases/providers',
    name: 'ProviderList',
    component: ProviderListView,
    meta: { title: 'Lista de Proveedores' }
  },
  {
    path: '/inventory/stock-report',
    name: 'StockReport',
    component: StockReportView,
    meta: { title: 'Reportes y Maestro' }
  },
    {
    path: '/inventory/stock-report/register',
    name: 'RegisterInventoryView',
    component: RegisterInventoryView,
    meta: { title: 'Registrar ingreso' }
  },
  {
    path: '/inventory/transfers',
    name: 'StockTransfers',
    component: StockTransferView,
    meta: { title: 'Transferencias' }
  },
  {
    path: '/inventory/stock-transfer-report',
    name: 'StockTransferReport',
    component: StockTransferReportView,
    meta: { title: 'Reporte de Transferencias' }
  },
  {
    path: '/inventory/transfers/create',
    name: 'CreateStockTransfer',
    component: CreateTransferView,
    meta: { title: 'Crear Transferencia' }
  },
  {
    path: '/inventory/transfers/:id',
    name: 'StockTransferDetail',
    component: () => import('@/views/inventory/StockTransferDetailView.vue'),
    meta: { title: 'Detalle de Transferencia' }
  },
  {
    path: '/inventory/transfers/:id/return',
    name: 'StockReturn',
    component: () => import('@/views/inventory/StockReturnView.vue'),
    meta: { title: 'Devolver Stock' }
  },
  {
    path: '/inventory/receipts/:id',
    name: 'InventoryReceiptDetail',
    component: () => import('@/views/inventory/InventoryDetailView.vue'),
    meta: { title: 'Detalle de Recepción' }
  },
  {
    path: '/inventory/adjust',
    name: 'InventoryAdjustment',
    component: InventoryAdjustmentView,
    meta: { title: 'Ajuste y Carga' }
  },
  {
    path: '/rrhh/employees',
    name: 'employees',
    component: () => import('../views/rrhh/EmployeesView.vue'),
    meta: { requiresAuth: true, permission: 'view:employees' }
  },
  {
    path: '/rrhh/attendance',
    name: 'attendance',
    component: () => import('../views/rrhh/AttendanceView.vue'),
    meta: { requiresAuth: true, permission: 'view:employees' }
  },
  {
    path: '/treasury',
    name: 'treasury',
    component: () => import('../views/treasury/TreasuryView.vue'),
    meta: { requiresAuth: true, permission: 'view:treasury', title: 'Modulo de Caja' }
  },
    {
        path: '/payment',
        name: 'payment',
        component: () => import ('../views/treasury/PaymentView.vue'),
       meta: { requiresAuth: true, permission: 'view:treasury', title: 'Modulo de Caja'}
       },
    {
        path: '/treasury/allocations/:id',
        name: 'treasury-allocation-detail',
        component: () => import('../views/treasury/AllocationDetailView.vue'),
        meta: { requiresAuth: true, permission: 'view:treasury', title: 'Detalle de Asignación' }
    }
    ]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
