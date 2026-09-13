import { createApp } from "vue"
import { createPinia } from "pinia"
import { createRouter, createWebHistory } from "vue-router"
import { useThemeStore } from "../../src/stores/theme"
import App from "../../src/archives/App.vue"
import FeedView from "../../src/archives/FeedView.vue"
import "../../src/archives/archives.css"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "feed", component: FeedView },
    {
      path: "/posts/:slug",
      name: "post",
      component: () => import("../../src/archives/PostView.vue"),
    },
    {
      path: "/reader",
      name: "reader",
      component: () => import("../../src/archives/ReaderView.vue"),
    },
    {
      path: "/:pathMatch(.*)*",
      name: "missing",
      component: () => import("../../src/archives/NotFoundView.vue"),
    },
  ],
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
})
router.afterEach(() => {
  document.title = "OrganicArchives | OrganicEmperor"
  document
    .querySelector('meta[name="description"]')
    ?.setAttribute(
      "content",
      "Articles, news releases, and updates from OrganicEmperor. Explore the OrganicArchives.",
    )
  document
    .querySelector('meta[property="og:title"]')
    ?.setAttribute("content", document.title)
  document
    .querySelector('meta[property="og:description"]')
    ?.setAttribute(
      "content",
      "Articles, news releases, and updates from OrganicEmperor.",
    )
  document
    .querySelector('meta[property="og:type"]')
    ?.setAttribute("content", "website")
})
const pinia = createPinia()
const app = createApp(App).use(pinia)
useThemeStore(pinia).initialize()
app.use(router).mount("#app")
