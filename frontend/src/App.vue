<script setup>
import { useAuth0 } from '@auth0/auth0-vue'
import { Button } from '@/components/ui/button'
import { computed, watch, ref } from 'vue' // <-- Añadido 'ref'
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
  LayoutDashboard, BarChart2, FileText,
  MoreHorizontal, LogOut, User, Settings, Briefcase, ShoppingBagIcon,Archive,Package, FolderTree, Building2, Users, DollarSign
} from 'lucide-vue-next'

import { Toaster } from '@/components/ui/toast'

// Lógica de Auth0
const { loginWithRedirect, logout, user, isAuthenticated, isLoading, getAccessTokenSilently } = useAuth0()

// Lógica 'isAdmin' (igual que antes)
const AUTH0_NAMESPACE = 'https://appcompower.com'
const isAdmin = computed(() => {
  const rolesKey = AUTH0_NAMESPACE + '/roles';
  if (user.value && user.value[rolesKey] && Array.isArray(user.value[rolesKey])) {
    const userRoles = user.value[rolesKey].map(role => role.toLowerCase());
    return userRoles.includes('admin');
  }
  return false;
})

// Lógica de login/logout (igual que antes)
function handleLogin() { loginWithRedirect() }
function handleLogout() { logout({ logoutParams: { returnTo: window.location.origin } }) }

// Título de la página (igual que antes)
const route = useRoute()
const currentPageTitle = computed(() => route.meta.title || 'Dashboard')

// --- ¡NUEVA LÓGICA DE SIDEBAR DINÁMICO! ---

// 2. Definir TODOS los módulos posibles de la app
const navModules = [
  {
    title: 'Modulo de Proyectos', // <-- Renombrado
    icon: Briefcase,
    permission: 'view:cost_centers', // <-- Permiso actualizado
    links: [
      { name: 'Centro de costo', path: '/cost-centers' }, // <-- Renombrado
      { name: 'Site', path: '/projects/sites' } // <-- Nuevo link
    ]
  },
  {
    title: 'Modulo de Compras', // <-- Renombrado
    icon: ShoppingBagIcon,
    permission: 'view:purchases', // <-- Permiso actualizado
    links: [
      { name: 'Ver Compras', path: '/purchases' } // <-- Path actualizado
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
      { name: 'Movimientos', path: '/treasury' }
    ]
  }
]

// 3. Un 'ref' para guardar los permisos del usuario
const userPermissions = ref([])

// 4. Función para llamar a la API /api/my-permissions
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

// 5. Lógica de redirección y carga de permisos
watch(
  [isAuthenticated, isLoading],
  ([isAuth, loading]) => {
    if (!loading && !isAuth) {
      loginWithRedirect({ appState: { targetUrl: route.path } })
    }
    // Si está autenticado, cargar sus permisos
    if (isAuth) {
      fetchUserPermissions()
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
                        <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                          {{ link.name }}
                        </Button>
                      </RouterLink>
                    </li>
                  </ul>
                </AccordionContent>
              </AccordionItem>
            </template>
            <AccordionItem v-if="userPermissions.includes('view:inventory') || userPermissions.includes('manage:inventory')" value="inventory">
                <AccordionTrigger class="hover:no-underline">
                  <div class="flex items-center">
                    <Archive class="h-4 w-4 mr-2" />
                    <span>Modulo de Inventario</span>
                  </div>
                </AccordionTrigger>
                <AccordionContent class="pl-4">
                  <ul class="space-y-1">
                    <li v-if="userPermissions.includes('manage:inventory')">
                      <RouterLink to="/inventory" v-slot="{ href, navigate, isActive }">
                        <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                          Recepcion
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
                    <!-- <li v-if="userPermissions.includes('manage:inventory')">
                      <RouterLink to="/inventory/warehouses" v-slot="{ href, navigate, isActive }">
                        <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                          Gestionar Almacenes
                        </Button>
                      </RouterLink>
                    </li> -->
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

              <!-- <AccordionItem v-if="userPermissions.includes('view:catalog')" value="catalog">
                <AccordionTrigger class="hover:no-underline">
                  <div class="flex items-center">
                    <FolderTree class="h-4 w-4 mr-2" />
                    <span>Catálogo</span>
                  </div>
                </AccordionTrigger>
                <AccordionContent class="pl-4">
                  <ul class="space-y-1">
                    <li>
                      <RouterLink to="/catalog/products" v-slot="{ href, navigate, isActive }">
                        <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                          Productos
                        </Button>
                      </RouterLink>
                    </li>
                    <li>
                      <RouterLink to="/catalog/categories" v-slot="{ href, navigate, isActive }">
                        <Button :variant="isActive ? 'secondary' : 'ghost'" class="w-full justify-start h-8" @click="navigate">
                          Categorías
                        </Button>
                      </RouterLink>
                    </li>
                  </ul>
                </AccordionContent>
              </AccordionItem> -->
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
/* Estilos globales (Sin cambios) */
html, body, #app {
  height: 100%;
  overflow: hidden;
}
</style>
