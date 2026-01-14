<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import PermissionDenied from '@/components/PermissionDenied.vue'

defineProps({ title: { type: String, default: 'Entrada 2' } })

const { getAccessTokenSilently } = useAuth0()

const isLoading = ref(true)
const error = ref(null)
const data = ref(null)

onMounted(async () => {
  try {
    const token = await getAccessTokenSilently()
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/entrada2_data`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (!response.ok) {
      // Si es 403 (Prohibido) o 401 (No autorizado)
      if (response.status === 403 || response.status === 401) {
        throw new Error('Access Denied')
      }
      throw new Error('Error de red')
    }

    data.value = await response.json()
  } catch (e) {
    error.value = e
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div>
    <h1 class="text-3xl font-bold mb-4">
      Hola bienvenido a {{ title }}
    </h1>

    <div v-if="isLoading" class="p-4 border rounded-lg">
      Cargando datos...
    </div>

    <PermissionDenied v-else-if="error" />

    <div v-else class="p-4 border rounded-lg bg-white">
      <p>Mensaje de la API:</p>
      <strong class="text-green-600">{{ data.message }}</strong>
    </div>
  </div>
</template>
