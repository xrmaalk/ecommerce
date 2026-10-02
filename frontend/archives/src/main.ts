import { createApp } from "vue"
import { createPinia } from "pinia"
import { createRouter, createWebHistory } from "vue-router"
import { useThemeStore } from "../../src/stores/theme"
import App from "../../src/archives/App.vue"
import FeedView from "../../src/archives/FeedView.vue"
import "../../src/archives/archives.css"
import { beginMetadata } from "../../src/seo"

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
      path: "/preview/:id",
      name: "preview",
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
router.afterEach((to, _from, failure) => {
  if (failure) return
  let robots = document.querySelector<HTMLMetaElement>('meta[name="robots"]')
  if (to.name === "preview") {
    if (!robots) {
      robots = document.createElement("meta")
      robots.name = "robots"
      document.head.append(robots)
    }
    robots.content = "noindex, nofollow"
  } else {
    robots?.remove()
  }
  beginMetadata("archives", to.name === "preview" ? "/" : to.path)
})
const pinia = createPinia()
const app = createApp(App).use(pinia)
useThemeStore(pinia).initialize()
app.use(router).mount("#app")
