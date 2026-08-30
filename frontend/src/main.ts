import { createPinia } from "pinia"
import { createApp } from "vue"
import App from "./App.vue"
import router from "./router"
import { useThemeStore } from "./stores/theme"
import "./styles/index.css"

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
useThemeStore(pinia).initialize()
app.use(router).mount("#app")
