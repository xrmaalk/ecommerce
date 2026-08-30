import { createRouter, createWebHistory } from "vue-router"

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: "/", name: "home", component: () => import("../views/HomeView.vue") },
    { path: "/bag", name: "bag", component: () => import("../views/BagView.vue"), meta: { title: "Shopping Bag" } },
    { path: "/account", name: "account", component: () => import("../views/AccountView.vue"), meta: { title: "Account" } },
    { path: "/privacy", name: "privacy", component: () => import("../views/PrivacyView.vue"), meta: { title: "Privacy" } },
    { path: "/returns", name: "returns", component: () => import("../views/ReturnsView.vue"), meta: { title: "Returns" } },
    { path: "/:pathMatch(.*)*", name: "not-found", component: () => import("../views/NotFoundView.vue"), meta: { title: "Page Not Found" } },
  ],
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: "smooth" }
    return { top: 0 }
  },
})

router.afterEach((to) => {
  const brand = "Organic Emperor"
  document.title = to.meta.title ? `${String(to.meta.title)} | ${brand}` : brand
})

export default router
