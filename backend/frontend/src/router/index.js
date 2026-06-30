import { createRouter, createWebHistory } from "vue-router";

const routes = [
  { path: "/", name: "Home", component: () => import("../views/Home.vue") },
  {
    path: "/login",
    name: "Login",
    component: () => import("../views/Login.vue"),
  },
  {
    path: "/register",
    name: "Register",
    component: () => import("../views/Register.vue"),
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
  scrollBehavior() {
    return { top: 0 };
  },
});

function isLoggedIn() {
  return Boolean(
    localStorage.getItem("access_token") ||
    localStorage.getItem("refresh_token"),
  );
}

function isAdmin() {
  return ["admin", "super_admin"].includes(localStorage.getItem("user_role"));
}

function questionnaireCompleted() {
  return localStorage.getItem("questionnaire_completed") !== "false";
}

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isLoggedIn()) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }

  if (to.meta.requiresAdmin && !isAdmin()) {
    return isLoggedIn()
      ? { path: "/" }
      : { path: "/login", query: { redirect: to.fullPath } };
  }

  if (
    isLoggedIn() &&
    !questionnaireCompleted() &&
    !to.meta.allowIncompleteQuestionnaire &&
    to.path !== "/login" &&
    to.path !== "/register"
  ) {
    return { path: "/questionnaire", query: { redirect: to.fullPath } };
  }

  return true;
});

export default router;
