<script setup>
import { ref, onMounted, computed } from 'vue' // <-- Añadido computed
import { useAuth0 } from '@auth0/auth0-vue'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card/index.js'
// import { Checkbox } from '@/components/ui/checkbox' // <-- Ya no se usa
import { Button } from '@/components/ui/button/index.js'
// import { useToast } from '@/components/ui/toast/use-toast' // (Seguimos sin toast)

// --- ¡NUEVAS IMPORTACIONES! ---
import { Badge } from '@/components/ui/badge/index.js'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu/index.js'
import { Plus, X } from 'lucide-vue-next'
// ----------------------------

// Hooks
const { getAccessTokenSilently } = useAuth0()
// const { toast } = useToast()

// Refs (sin cambios)
const roles = ref([])
const permissions = ref([])
const isLoading = ref(true)
const error = ref(null)

// Función loadData (sin cambios)
onMounted(async () => {
  isLoading.value = true
  error.value = null
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/admin/roles`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) {
      throw new Error(`Error ${response.status}: No se pudieron cargar los datos.`)
    }
    const data = await response.json()
    roles.value = data.roles
    permissions.value = data.permissions
  } catch (e) {
    error.value = e.message
  } finally {
    isLoading.value = false
  }
})

// Función handlePermissionChange (¡SIN CAMBIOS! Sigue funcionando)
async function handlePermissionChange(role, permissionId) {
  console.log('--- ¡CLIC DETECTADO!', role, permissionId)
  const roleToUpdate = roles.value.find(r => r.id === role.id)
  if (!roleToUpdate) return

  const hasPermission = roleToUpdate.permission_ids.includes(permissionId)
  let newPermissionIds = []

  if (hasPermission) {
    newPermissionIds = roleToUpdate.permission_ids.filter(id => id !== permissionId)
  } else {
    newPermissionIds = [...roleToUpdate.permission_ids, permissionId]
  }

  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/admin/roles/${role.id}/permissions`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ permission_ids: newPermissionIds })
    })
    if (!response.ok) {
      throw new Error('Error al guardar')
    }
    roleToUpdate.permission_ids = newPermissionIds
    console.log("¡Permisos guardados!")
  } catch (e) {
    console.error("Error al guardar:", e.message)
  }
}

// Función Helper (sin cambios)
function roleHasPermission(role, permissionId) {
  return role.permission_ids.includes(permissionId)
}

// --- ¡NUEVO HELPER! ---
// Devuelve una lista de roles que NO tienen un permiso
function rolesWithoutPermission(permissionId) {
  return roles.value.filter(role => !role.permission_ids.includes(permissionId))
}
</script>

<template>
  <div>
    <h1 class="text-3xl font-bold mb-4">
      Roles y Permisos
    </h1>

    <div v-if="isLoading">Cargando roles y permisos...</div>

    <div v-else-if="error" class="text-red-500">{{ error }}</div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

      <Card v-for="permission in permissions" :key="permission.id">
        <CardHeader>
          <CardTitle class="text-lg">{{ permission.display_name }}</CardTitle>
        </CardHeader>
        <CardContent>
          <h4 class="font-semibold mb-2">Roles con acceso:</h4>
          <div class="flex flex-wrap gap-2 min-h-[40px]">

            <template v-for="role in roles" :key="role.id">
              <Badge
                v-if="roleHasPermission(role, permission.id)"
                variant="default"
                class="text-sm cursor-pointer"
                @click="() => handlePermissionChange(role, permission.id)"
              >
                {{ role.name }}
                <X class="h-3 w-3 ml-1" />
              </Badge>
            </template>

            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="outline" size="icon" class="h-8 w-8">
                  <Plus class="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <template v-for="role in rolesWithoutPermission(permission.id)" :key="role.id">
                  <DropdownMenuItem @click="() => handlePermissionChange(role, permission.id)">
                    Añadir rol: {{ role.name }}
                  </DropdownMenuItem>
                </template>
                <DropdownMenuItem v-if="rolesWithoutPermission(permission.id).length === 0" :disabled="true">
                  Todos los roles tienen acceso
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

          </div>
        </CardContent>
      </Card>

    </div>
  </div>
</template>
