/**
 * 导航数据状态管理 (Pinia Store)
 * =====================================
 * 管理网站导航核心数据：分类、网站列表、收藏、搜索历史等。
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { navAPI } from "@/utils/api";

export const useNavStore = defineStore("nav", () => {
  // ==================== 职业 ====================
  const currentProfession = ref("programmer");
  const professionData = ref({
    programmer: { name: "程序员", icon: "💻" },
    designer: { name: "设计师", icon: "🎨" },
    pm: { name: "产品经理", icon: "📋" },
    gamer: { name: "极客人", icon: "🕹️" },
  });

  // ==================== 分类与网站 ====================
  const categories = ref([]);
  const allSites = ref([]); // 所有网站映射
  const activeCategoryId = ref(null);

  // ==================== 收藏 ====================
  const favoriteSiteIds = ref([]);

  // ==================== 搜索历史 ====================
  const searchHistory = ref([]);
  const maxHistory = 10;

  // ==================== 计算属性 ====================
  /** 当前分类下的网站列表 */
  const currentSites = computed(() => {
    if (!activeCategoryId.value) return [];
    const cat = categories.value.find((c) => c.id === activeCategoryId.value);
    return cat?.sites || [];
  });

  // ==================== 加载导航数据 ====================
  async function loadNavData() {
    try {
      const res = await navAPI.getNavData();
      if (res.data?.code === 0 && res.data?.data) {
        const data = res.data.data;
        categories.value = data.categories || [];
        allSites.value = data.sites || [];

        // 自动选中第一个分类
        if (categories.value.length && !activeCategoryId.value) {
          activeCategoryId.value = categories.value[0].id;
        }
      }
    } catch (error) {
      console.error("加载导航数据失败:", error);
    }
  }

  // ==================== 切换职业 ====================
  function selectProfession(profKey) {
    if (professionData.value[profKey]) {
      currentProfession.value = profKey;
      loadNavData();
    }
  }

  // ==================== 收藏管理 ====================
  async function loadFavorites() {
    try {
      const res = await navAPI.getFavorites();
      if (res.data?.code === 0) {
        favoriteSiteIds.value = (res.data.data || []).map((f) => f.website_id);
      }
    } catch (error) {
      console.error("加载收藏失败:", error);
    }
  }

  async function toggleFavorite(websiteId) {
    const idx = favoriteSiteIds.value.indexOf(websiteId);
    if (idx > -1) {
      try {
        await navAPI.removeFavorite(websiteId);
        favoriteSiteIds.value.splice(idx, 1);
      } catch (e) {
        console.error("取消收藏失败:", e);
      }
    } else {
      try {
        await navAPI.addFavorite(websiteId);
        favoriteSiteIds.value.push(websiteId);
      } catch (e) {
        console.error("添加收藏失败:", e);
      }
    }
  }

  function isFavorite(websiteId) {
    return favoriteSiteIds.value.includes(websiteId);
  }

  // ==================== 搜索历史 ====================
  function addSearchHistory(query) {
    if (!query.trim()) return;
    // 去重
    searchHistory.value = searchHistory.value.filter((h) => h !== query);
    searchHistory.value.unshift(query);
    // 限制条数
    if (searchHistory.value.length > maxHistory) {
      searchHistory.value = searchHistory.value.slice(0, maxHistory);
    }
  }

  function clearSearchHistory() {
    searchHistory.value = [];
  }

  // ==================== 初始化 ====================
  function initFromStorage() {
    // 恢复专注模式收藏
    const savedFocus = localStorage.getItem("focus_sites");
    if (savedFocus) {
      try {
        // focus_sites 是专注模式的本地快捷收藏，独立于云端收藏
      } catch (e) {
        /* ignore */
      }
    }

    // 恢复搜索历史
    const savedHistory = localStorage.getItem("search_history");
    if (savedHistory) {
      try {
        searchHistory.value = JSON.parse(savedHistory);
      } catch (e) {
        /* ignore */
      }
    }
  }

  // 搜索历史自动持久化（通过 watch 在组件中绑定）

  return {
    currentProfession,
    professionData,
    categories,
    allSites,
    activeCategoryId,
    favoriteSiteIds,
    searchHistory,
    currentSites,
    loadNavData,
    selectProfession,
    loadFavorites,
    toggleFavorite,
    isFavorite,
    addSearchHistory,
    clearSearchHistory,
    initFromStorage,
  };
});
