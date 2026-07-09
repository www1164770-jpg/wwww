import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", name: "Home", component: () => import("../views/Home.vue") },
  {
    path: "/login",
    name: "Login",
    component: () => import("../views/Login.vue"),
    meta: { public: true },
  },
  {
    path: "/authing/callback",
    name: "AuthingCallback",
    component: () => import("../views/AuthingCallback.vue"),
    meta: { public: true },
  },
  {
    path: "/register",
    name: "Register",
    component: () => import("../views/Register.vue"),
    meta: { public: true },
  },
  {
    path: "/questionnaire",
    name: "Questionnaire",
    component: () => import("../views/Questionnaire.vue"),
    meta: { requiresAuth: true, allowIncompleteQuestionnaire: true },
  },
  {
    path: "/categories",
    name: "Categories",
    component: () => import("../views/Categories.vue"),
  },
  {
    path: "/category/:id",
    name: "CategoryDetail",
    component: () => import("../views/CategoryDetail.vue"),
  },
  {
    path: "/site/:id",
    name: "SiteDetail",
    component: () => import("../views/SiteDetail.vue"),
  },
  {
    path: "/search",
    name: "SearchResults",
    component: () => import("../views/SearchResults.vue"),
  },
  {
    path: "/favorites",
    name: "Favorites",
    component: () => import("../views/Favorites.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/profile",
    name: "Profile",
    component: () => import("../views/ProfileView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/admin",
    name: "Admin",
    component: () => import("../views/Admin.vue"),
    redirect: "/admin/dashboard",
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      {
        path: "dashboard",
        name: "AdminDashboard",
        component: () => import("../views/admin/AdminDashboard.vue"),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: "sites",
        name: "AdminSites",
        component: () => import("../views/admin/AdminSites.vue"),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: "categories",
        name: "AdminCategories",
        component: () => import("../views/admin/AdminCategories.vue"),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: "tags",
        name: "AdminTags",
        component: () => import("../views/admin/AdminTags.vue"),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: "users",
        name: "AdminUsers",
        component: () => import("../views/admin/AdminUsers.vue"),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: "comments",
        name: "AdminComments",
        component: () => import("../views/admin/AdminComments.vue"),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: "/admin/questionnaires",
        name: "AdminQuestionnaires",
        component: () => import("../views/admin/AdminQuestionnaires.vue"),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: "/admin/recommend-rules",
        name: "AdminRecommendRules",
        component: () => import("../views/admin/AdminRecommendRules.vue"),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: "/admin/settings",
        name: "AdminSettings",
        component: () => import("../views/admin/AdminSettings.vue"),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
    ],
  },
  {
    path: "/publish",
    name: "Publish",
    component: () => import("../views/Editor.vue"),
  },
  {
    path: "/audit",
    name: "Audit",
    component: () => import("../views/AuditBoard.vue"),
  },
  { path: "/dmca", name: "DMCA", component: () => import("../views/DMCA.vue") },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }

    if (to.hash) {
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            el: to.hash,
            top: 88,
            behavior: "smooth",
          });
        }, 80);
      });
    }

    return { top: 0, behavior: "smooth" };
  },
});

function isLoggedIn() {
  const token =
    localStorage.getItem("token") || localStorage.getItem("access_token");
  const value = String(token || "");
  return Boolean(
    value.length > 20 &&
    (!value.includes(".") || value.split(".").length === 3),
  );
}

function isAdmin() {
  return ["admin", "super_admin"].includes(localStorage.getItem("user_role"));
}

router.beforeEach((to) => {
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin);
  const isPublic = to.matched.some((record) => record.meta.public);

  if (isPublic && to.path !== "/login") {
    return true;
  }

  if (to.path === "/login" && isLoggedIn()) {
    return { path: "/" };
  }

  if (requiresAuth && !isLoggedIn()) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }

  if (requiresAdmin && !isAdmin()) {
    return isLoggedIn()
      ? { path: "/" }
      : { path: "/login", query: { redirect: to.fullPath } };
  }

  return true;
});

export default router;
