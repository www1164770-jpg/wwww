/**
 * 应用全局 UI 状态管理 (Pinia Store)
 * =====================================
 * 管理主题、专注模式、搜索引擎、壁纸、职业选择等全局 UI 状态。
 */

import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useAppStore = defineStore('app', () => {
  // ==================== 主题 ====================
  const isDarkMode = ref(false)

  function toggleTheme() {
    isDarkMode.value = !isDarkMode.value
  }

  // ==================== 专注模式 ====================
  const isFocusMode = ref(false)

  function toggleFocusMode() {
    isFocusMode.value = !isFocusMode.value
  }

  // ==================== 搜索引擎 ====================
  const currentEngine = ref('google')
  const selectedEngines = ref(['google', 'baidu', 'github', 'bilibili'])

  function setEngine(engine) {
    currentEngine.value = engine
  }

  function updateSelectedEngines(engines) {
    selectedEngines.value = [...engines]
  }

  // ==================== 壁纸 ====================
  const customWallpaper = ref('')
  const focusWallpaper = ref('')

  function setWallpaper(url) {
    customWallpaper.value = url
  }

  function removeWallpaper() {
    customWallpaper.value = ''
  }

  function setFocusWallpaper(url) {
    focusWallpaper.value = url
  }

  function removeFocusWallpaper() {
    focusWallpaper.value = ''
  }

  // ==================== Toast 消息 ====================
  const toastMessage = ref('')
  const toastType = ref('info') // 'info' | 'success' | 'error' | 'warning'

  function showToast(msg, type = 'info') {
    toastMessage.value = msg
    toastType.value = type
    setTimeout(() => {
      toastMessage.value = ''
    }, 3000)
  }

  // ==================== 初始化（从 localStorage 恢复） ====================
  function initFromStorage() {
    // 主题
    const savedDark = localStorage.getItem('dark_mode')
    if (savedDark === 'true') isDarkMode.value = true

    // 壁纸
    const savedBg = localStorage.getItem('custom_wallpaper')
    if (savedBg) customWallpaper.value = savedBg
    const savedFocusBg = localStorage.getItem('focus_wallpaper')
    if (savedFocusBg) focusWallpaper.value = savedFocusBg

    // 搜索引擎
    const savedEngine = localStorage.getItem('current_engine')
    if (savedEngine) currentEngine.value = savedEngine
    const savedEngines = localStorage.getItem('selected_engines')
    if (savedEngines) {
      try {
        selectedEngines.value = JSON.parse(savedEngines)
      } catch (e) { /* ignore */ }
    }
  }

  // ==================== 持久化监听 ====================
  function persistToStorage() {
    localStorage.setItem('dark_mode', isDarkMode.value)
    localStorage.setItem('current_engine', currentEngine.value)
    localStorage.setItem('selected_engines', JSON.stringify(selectedEngines.value))
    if (customWallpaper.value) {
      localStorage.setItem('custom_wallpaper', customWallpaper.value)
    } else {
      localStorage.removeItem('custom_wallpaper')
    }
    if (focusWallpaper.value) {
      localStorage.setItem('focus_wallpaper', focusWallpaper.value)
    } else {
      localStorage.removeItem('focus_wallpaper')
    }
  }

  // 自动持久化关键字段
  watch([isDarkMode, currentEngine, selectedEngines, customWallpaper, focusWallpaper], () => {
    persistToStorage()
  }, { deep: true })

  return {
    isDarkMode,
    isFocusMode,
    currentEngine,
    selectedEngines,
    customWallpaper,
    focusWallpaper,
    toastMessage,
    toastType,
    toggleTheme,
    toggleFocusMode,
    setEngine,
    updateSelectedEngines,
    setWallpaper,
    removeWallpaper,
    setFocusWallpaper,
    removeFocusWallpaper,
    showToast,
    initFromStorage,
    persistToStorage
  }
})
