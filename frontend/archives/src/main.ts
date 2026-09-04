import { createApp } from "vue"
import { createRouter, createWebHistory } from "vue-router"
import App from "../../src/archives/App.vue"
import FeedView from "../../src/archives/FeedView.vue"
import "../../src/archives/archives.css"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "feed", component: FeedView },
    { path: "/posts/:slug", name: "post", component: () => import("../../src/archives/PostView.vue") },
    { path: "/:pathMatch(.*)*", name: "missing", component: () => import("../../src/archives/NotFoundView.vue") },
  ],
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
})
router.afterEach(() => {
  document.title = "Organic Archives | Organic Emperor"
  document.querySelector('meta[name="description"]')?.setAttribute("content", "Articles, news releases, and updates from Organic Emperor. Explore the Organic Archives.")
  document.querySelector('meta[property="og:title"]')?.setAttribute("content", document.title)
  document.querySelector('meta[property="og:description"]')?.setAttribute("content", "Articles, news releases, and updates from Organic Emperor.")
  document.querySelector('meta[property="og:type"]')?.setAttribute("content", "website")
})
createApp(App).use(router).mount("#app")
