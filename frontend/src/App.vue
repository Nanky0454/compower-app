<script setup>
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button'
import { computed, watch, ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

// 1. Importar Accordion
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'

// Importar componentes de shadcn (Dropdown, Avatar)
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from '@/components/ui/avatar'

// Importar iconos
import {
  MoreHorizontal, LogOut, Settings, Briefcase, ShoppingBagIcon,
  Archive, Users, DollarSign
} from 'lucide-vue-next'

import { Toaster } from '@/components/ui/toast'

// Lógica de Auth0
const { loginWithRedirect, logout, user, isAuthenticated, isLoading, getAccessTokenSilently } = useAuth0()

// Lógica 'isAdmin'
const AUTH0_NAMESPACE = 'https://appcompower.com'
const isAdmin = computed(() => {
  const rolesKey = AUTH0_NAMESPACE + '/roles';
  if (user.value && user.value[rolesKey] && Array.isArray(user.value[rolesKey])) {
    const userRoles = user.value[rolesKey].map(role => role.toLowerCase());
    return userRoles.includes('admin');
  }
  return false;
})

function handleLogout() { logout({ logoutParams: { returnTo: window.location.origin } }) }

const route = useRoute()
const currentPageTitle = computed(() => route.meta.title || 'Dashboard')

// --- LÓGICA DE NOTIFICACIONES Y PERMISOS ---

const userPermissions = ref([])
const pendingPurchasesCount = ref(0) // Estado para el numerito rojo

// Función para contar: Aprobadas + Tipo OC
async function fetchDashboardCounts() {
  if (!isAuthenticated.value) return
  try {
    const token = await getAccessTokenSilently()
    console.log(token)
    const res = await fetch(`${import.meta.env.VITE_API_URL}/api/purchases/`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (res.ok) {
      const data = await res.json()

      // --- FILTRO: Aprobadas Y de tipo OC ---
      const pendientes = data.filter(order =>
          order.status === 'Aprobada' &&
          order.order_type === 'OC'
      )
      pendingPurchasesCount.value = pendientes.length
    }
  } catch (error) {
    console.error("Error cargando contadores:", error)
  }
}

// Función para permisos
async function fetchUserPermissions() {
  if (!isAuthenticated.value) return
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/my-permissions`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) throw new Error('No se pudieron cargar los permisos')
    const data = await response.json()
    userPermissions.value = data.permissions || []
  } catch (error) {
    console.error("Error cargando permisos:", error)
    userPermissions.value = []
  }
}

// Módulos de navegación (COMPUTED para que reaccione al contador)
const navModules = computed(() => [
  {
    title: 'Modulo de Proyectos',
    icon: Briefcase,
    permission: 'view:cost_centers',
    links: [
      { name: 'Centro de costo', path: '/cost-centers' },
      { name: 'Site', path: '/projects/sites' }
    ]
  },
  {
    title: 'Modulo de Compras',
    icon: ShoppingBagIcon,
    permission: 'view:purchases',
    links: [
      {
        name: 'Ver Compras',
        path: '/purchases',
        // Inyectamos el contador aquí
      },
      {
        name: 'Ver Proveedores',
        path: '/purchases/providers'
      }
    ]
  },
  {
    title: 'Modulo RR.HH',
    icon: Users,
    permission: 'view:employees',
    links: [
      { name: 'Empleados', path: '/rrhh/employees' },
      { name: 'Asistencia', path: '/rrhh/attendance' }
    ]
  },
  {
    title: 'Modulo de Caja',
    icon: DollarSign,
    permission: 'view:treasury',
    links: [
      { name: 'Movimientos', path: '/treasury' },
      { name: 'Pagos', path: '/payment'}
    ]
  }
])

// Watcher para cargar datos al entrar
watch(
  [isAuthenticated, isLoading],
  ([isAuth, loading]) => {
    if (!loading && !isAuth) {
      loginWithRedirect({ appState: { targetUrl: route.path } })
    }
    if (isAuth) {
      fetchUserPermissions()
      fetchDashboardCounts() // <-- Carga el contador
    }
  },
  { immediate: true }
)
</script>

<template>
  <div v-if="isAuthenticated" class="flex" style="height: 100vh;">

    <div class="w-64 border-r bg-white flex flex-col print:hidden">
      <div class="p-4 border-b">
        <RouterLink to="/">
          <h1 class="text-xl font-bold text-gray-800 hover:text-gray-600">
            CompowerAPP
          </h1>
        </RouterLink>
      </div>

      <nav class="flex-1 p-3 flex flex-col justify-between overflow-auto">
        <div>
          <Accordion type="multiple" class="w-full">

            <template v-for="module in navModules" :key="module.title">
              <AccordionItem v-if="userPermissions.includes(module.permission)" :value="module.title">
                <AccordionTrigger class="hover:no-underline">
                  <div class="flex items-center">
                    <component :is="module.icon" class="h-4 w-4 mr-2" />
                    <span>{{ module.title }}</span>
                  </div>
                </AccordionTrigger>
                <AccordionContent class="pl-4">
                  <ul class="space-y-1">
                    <li v-for="link in module.links" :key="link.name">
                      <RouterLink :to="link.path" v-slot="{ href, navigate, isActive }">

                        <Button
                          :variant="isActive ? 'secondary' : 'ghost'"
                          class="w-full h-8 flex items-center justify-between px-2"
                          @click="navigate"
                        >
                          <span>{{ link.name }}</span>

                          <span
                            v-if="link.badge && link.badge > 0"
                            class="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full ml-2 h-5 min-w-[20px] flex items-center justify-center shadow-sm"
                          >
                            {{ link.badge }}
                          </span>
                        </Button>

                      </RouterLink>
                    </li>
                  </ul>
                </AccordionContent>
              </AccordionItem>
            </template>

            <AccordionItem v-if="userPermissions.includes('view:inventory') || userPermissions.includes('manage:inventory')" value="inventory">

              <AccordionTrigger class="hover:no-underline pr-4">
                <div class="flex items-center w-full justify-between">
                  <div class="flex items-center">
                    <Archive class="h-4 w-4 mr-2" />
                    <span>Modulo de Inventario</span>
                  </div>
                  <span
                    v-if="pendingPurchasesCount > 0"
                    class="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full h-5 min-w-[20px] flex items-center justify-center shadow-sm mr-2"
                  >
                    {{ pendingPurchasesCount }}
                  </span>
                </div>
              </AccordionTrigger>

              <AccordionContent class="pl-4">
                <ul class="space-y-1">

                  <li v-if="userPermissions.includes('manage:inventory')">
                    <RouterLink to="/inventory" v-slot="{ href, navigate, isActive }">
                      <Button
                          :variant="isActive ? 'secondary' : 'ghost'"
                          class="w-full h-8 flex items-center justify-between px-2"
                          @click="navigate"
                      >
                        <span>Recepcion</span>
                        <span
                          v-if="pendingPurchasesCount > 0"
                          class="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full ml-2 h-5 min-w-[20px] flex items-center justify-center shadow-sm"
                        >
                          {{ pendingPurchasesCount }}
                        </span>
                      </Button>
                    </RouterLink>
                  </li>

                  <li v-if="userPermissions.includes('manage:inventory')">
                    <RouterLink to="/inventory/stock-transfer-report" v-slot="{ href, navigate, isActive }">
                      <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                        Reportes
                      </Button>
                    </RouterLink>
                  </li>
                  <li v-if="userPermissions.includes('manage:transfers')">
                    <RouterLink to="/inventory/transfers" v-slot="{ href, navigate, isActive }">
                      <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                        Transferencias
                      </Button>
                    </RouterLink>
                  </li>
                  <li v-if="userPermissions.includes('view:inventory')">
                    <RouterLink to="/inventory/stock-report" v-slot="{ href, navigate, isActive }">
                      <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                        Inventario
                      </Button>
                    </RouterLink>
                  </li>
                  <li v-if="userPermissions.includes('manage:inventory')">
                    <RouterLink to="/inventory/adjust" v-slot="{ href, navigate, isActive }">
                      <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                        Ajuste y Carga
                      </Button>
                    </RouterLink>
                  </li>
                </ul>
              </AccordionContent>
          </AccordionItem>

            <AccordionItem v-if="isAdmin" value="admin-panel">
              <AccordionTrigger class="hover:no-underline">
                <div class="flex items-center">
                  <Settings class="h-4 w-4 mr-2" />
                  <span>Admin Panel</span>
                </div>
              </AccordionTrigger>
              <AccordionContent class="pl-4">
                <ul class="space-y-1">
                  <li>
                    <RouterLink to="/admin" v-slot="{ href, navigate, isActive }">
                      <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                        Roles y Permisos
                      </Button>
                    </RouterLink>
                  </li>
                  <li>
                    <RouterLink to="/admin/config/ubigeo" v-slot="{ href, navigate, isActive }">
                      <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                        Configuración Ubigeo
                      </Button>
                    </RouterLink>
                  </li>
                  <li>
                    <RouterLink to="/admin/config/treasury" v-slot="{ href, navigate, isActive }">
                      <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                        Configuración Caja
                      </Button>
                    </RouterLink>
                  </li>
                  <li>
                    <RouterLink to="/admin/config/unit_measure" v-slot="{ href, navigate, isActive }">
                      <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                        Configuración Unidad de Medida
                      </Button>
                    </RouterLink>
                  </li>

                </ul>
              </AccordionContent>
            </AccordionItem>

          </Accordion>
        </div>

        <div v-if="isAuthenticated">
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="ghost" class="w-full justify-between h-16 text-left">
                <div class="flex items-center space-x-3">
                  <Avatar>
                    <AvatarImage :src="user?.picture || ''" :alt="user?.name || 'U'" />
                    <AvatarFallback>{{ user.name ? user.name.substring(0, 2) : 'U' }}</AvatarFallback>
                  </Avatar>
                  <div class="flex flex-col -space-y-1">
                    <span class="text-sm font-medium">{{ user.name }}</span>
                    <span class="text-xs text-gray-500">{{ user.email }}</span>
                  </div>
                </div>
                <MoreHorizontal class="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent class="w-56" align="end">
              <DropdownMenuItem @click="handleLogout" class="text-red-600">
                <LogOut class="h-4 w-4 mr-2" />
                <span>Cerrar Sesión</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </nav>
    </div>

    <div class="flex-1 flex flex-col">
      <header class="p-4.5 flex justify-between items-center border-b bg-white">
        <div class="flex items-center h-6">
          <span class="text-lg font-medium text-gray-600">
            {{ currentPageTitle }}
          </span>
        </div>
      </header>
      <main class="flex-1 p-8 overflow-auto bg-gray-50/50">
        <RouterView />
      </main>
    </div>
  </div>

  <div v-else class="flex h-screen w-screen items-center justify-center">
    <span class="text-xl font-medium">Cargando...</span>
  </div>
  <Toaster />
</template>

<style>
/* Estilos globales */
html, body, #app {
  height: 100%;
  overflow: hidden;
}
</style>