import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import axios from 'axios'

// Настройка Axios
axios.defaults.baseURL = process.env.VUE_APP_API_URL || 'http://localhost:8000'
axios.defaults.headers.common['X-API-Key'] = process.env.VUE_APP_API_KEY

const app = createApp(App)
app.config.globalProperties.$http = axios
app.use(store)
app.use(router)
app.mount('#app')
