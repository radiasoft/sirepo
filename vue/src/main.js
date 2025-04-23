import App from '@/App.vue'
import router from '@/services/router'
import { createApp } from 'vue'
import "bootstrap"
import '@/main.scss'
import "bootstrap-icons/font/bootstrap-icons.css";
import '@/assets/main.css'

createApp(App).use(router).mount('#app')
