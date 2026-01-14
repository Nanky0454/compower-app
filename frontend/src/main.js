import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import { createAuth0 } from '@auth0/auth0-vue' // <-- Importa Auth0
import router from './router'
const app = createApp(App)

// Configura el plugin de Auth0
app.use(
  createAuth0({
    domain: 'dev-gforng2dfnavhcdz.us.auth0.com', // <-- Pega tu Domain
    clientId: 'UJPg0NM2Dxum2EMn5WATWJuapSKPI2cQ', // <-- Pega tu Client ID
    authorizationParams: {
      redirect_uri: window.location.origin,
      audience: 'https://api.appcompower.com' // <-- Pega tu Audience/Identifier
    }
  })
)
app.use(router)
app.mount('#app')
