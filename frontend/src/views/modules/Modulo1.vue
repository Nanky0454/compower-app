<script setup>
import { ref, onMounted } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'

// Recibimos el título como una "prop" desde el router
defineProps({
  title: {
    type: String,
    default: 'la página principal'
  }
})

const { getAccessTokenSilently } = useAuth0()

// --- Refs para AMBOS mensajes ---
const messageFromFlask = ref('Cargando mensaje de la API...')
const adminMessage = ref('Probando ruta de admin...') // <-- NUEVO REF

async function callApi() {
  // Obtenemos el token una sola vez
  let token
  try {
    token = await getAccessTokenSilently()
  } catch (error) {
    messageFromFlask.value = 'Error al obtener el token de Auth0'
    adminMessage.value = 'Error al obtener el token de Auth0'
    return
  }

  // --- 1. Llamada a la API normal (debe funcionar) ---
  try {
    const responseNormal = await fetch(`${import.meta.env.VITE_API_URL}/api/message`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const dataNormal = await responseNormal.json()
    messageFromFlask.value = dataNormal.message
  } catch (error) {
    messageFromFlask.value = 'Error al conectar con la API.'
  }

  // --- 2. Llamada a la API de ADMIN (debe fallar) ---
  try {
    const responseAdmin = await fetch(`${import.meta.env.VITE_API_URL}/api/admin/roles`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (!responseAdmin.ok) {
      // Si la respuesta no es 200, lanzamos un error con el status
      throw new Error(`Error ${responseAdmin.status}: ${responseAdmin.statusText}`)
    }

    // Si por alguna razón funciona, lo sabremos
    const dataAdmin = await responseAdmin.json()
    adminMessage.value = '¡ÉXITO! Pudiste ver los datos de admin. (Esto no debería pasar)'

  } catch (error) {
    // ¡Este es el resultado que queremos ver!
    console.error("Error al llamar a la API de admin:", error)
    adminMessage.value = `Prueba de admin falló como se esperaba. (Error: ${error.message})`
  }
}

onMounted(() => {
  callApi()
})
</script>

<template>
  <div>
    <h1 class="text-3xl font-bold mb-4">
      Hola bienvenido a {{ title }}
    </h1>

    <p class="text-lg p-4 border rounded-lg">
      Mensaje de la API: <strong>{{ messageFromFlask }}</strong>
    </p>

    <p class="text-lg p-4 border rounded-lg mt-4 bg-gray-100">
      Prueba de ruta de Admin: <strong>{{ adminMessage }}</strong>
    </p>
  </div>
</template>
