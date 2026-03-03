import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import { createAuth0 } from '@auth0/auth0-vue' // <-- Importa Auth0
import router from './router'
const app = createApp(App)

// Configura el plugin de Auth0
app.use(
  createAuth0({
    domain: 'compower-app.us.auth0.com', // <-- Pega tu Domain
    clientId: 'j4IOBtmgRSkjFfyTGZ0ypuQrjv1NKskw', // <-- Pega tu Client ID
    authorizationParams: {
      redirect_uri: window.location.origin,
      audience: 'https://compower-app.us.auth0.com/api/v2/' // <-- Pega tu Audience/Identifier
    }
  })
)
app.use(router)
app.mount('#app')
