<template>
  <!-- 🎯 双维度兴趣问卷弹窗 -->
  <Teleport to="body">
    <transition name="survey-fade">
      <div v-if="visible" class="survey-overlay" @click.self="handleSkip">
        <div class="survey-modal" @click.stop>
          <!-- 装饰光晕 -->
          <div class="survey-glow survey-glow-1"></div>
          <div class="survey-glow survey-glow-2"></div>

          <!-- 头部 -->
          <div class="survey-header">
            <div class="survey-icon">🧭</div>
            <h2 class="survey-title">定制你的专属导航</h2>
            <p class="survey-subtitle">
              选择你的职业角色与核心需求，我们将为你精准推荐最对胃口的工具与资源。
            </p>
          </div>

          <!-- ========== 维度一：我的职业角色 ========== -->
          <div class="survey-section">
            <h3 class="section-title">
              <span class="section-badge">维度一</span>
              我的职业角色
              <span class="section-hint">（多选）</span>
            </h3>
            <div class="survey-tags-grid">
              <div
                v-for="tag in roleTags"
                :key="tag.key"
                class="survey-tag-card"
                :class="{ 'survey-tag-selected': selectedTags.includes(tag.key) }"
                @click="toggleTag(tag.key)"
              >
                <span class="tag-emoji">{{ tag.emoji }}</span>
                <span class="tag-label">{{ tag.label }}</span>
                <span v-if="selectedTags.includes(tag.key)" class="tag-check">✓</span>
              </div>
            </div>
          </div>

          <!-- ========== 维度二：我的核心需求 ========== -->
          <div class="survey-section">
            <h3 class="section-title">
              <span class="section-badge">维度二</span>
              我的核心需求
              <span class="section-hint">（多选）</span>
            </h3>
            <div class="survey-tags-grid demand-grid">
              <div
                v-for="tag in demandTags"
                :key="tag.key"
                class="survey-tag-card demand-card"
                :class="{ 'survey-tag-selected': selectedTags.includes(tag.key) }"
                @click="toggleTag(tag.key)"
              >
                <span class="tag-emoji">{{ tag.emoji }}</span>
                <span class="tag-label">{{ tag.label }}</span>
                <span v-if="selectedTags.includes(tag.key)" class="tag-check">✓</span>
              </div>
            </div>
          </div>

          <!-- 选中提示 -->
          <div class="survey-selected-hint" v-if="selectedTags.length > 0">
            已选 <strong>{{ selectedTags.length }}</strong> 个标签
            <span v-if="selectedTags.length >= 3" class="hint-extra">— 维度覆盖越广，推荐越精准 🎯</span>
            <span v-else class="hint-extra">— 建议在至少一个维度中做出选择</span>
          </div>
          <div class="survey-selected-hint empty-hint" v-else>
            <span class="hint-dim">请至少在一个维度中选择你感兴趣的方向</span>
          </div>

          <!-- 底部按钮 -->
          <div class="survey-actions">
            <button
              class="survey-btn-submit"
              :disabled="selectedTags.length === 0 || isSubmitting"
              @click="handleSubmit"
            >
              <span v-if="isSubmitting" class="btn-loading"></span>
              <span v-else>✨ 生成我的专属百宝箱</span>
            </button>
            <button
              class="survey-btn-skip"
              :disabled="isSubmitting"
              @click="handleSkip"
            >
              {{ selectedTags.length > 0 ? '先跳过，以后再说' : '暂时跳过，使用默认导航' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

// ==================== Props ====================
const props = defineProps({
  visible: { type: Boolean, default: false },
  username: { type: String, default: '' }
})

// ==================== Emits ====================
const emit = defineEmits(['close', 'submit', 'skip'])

// ==================== 维度一：我的职业角色 ====================
const roleTags = [
  { key: 'frontend',    emoji: '🚀', label: '前端开发' },
  { key: 'backend',     emoji: '🐍', label: '后端开发' },
  { key: 'ai-data',     emoji: '🤖', label: '人工智能 / 数据科学' },
  { key: 'ui-design',   emoji: '🎨', label: 'UI / UX 设计' },
  { key: 'iot-hardware',emoji: '⚙️', label: '智能硬件与物联网' },
  { key: 'product-pm',  emoji: '📈', label: '产品与运营' },
]

// ==================== 维度二：我的核心需求 ====================
const demandTags = [
  { key: 'self-learning',  emoji: '📚', label: '自学进阶' },
  { key: 'job-hunting',    emoji: '💼', label: '求职面试 / 搞钱' },
  { key: 'efficiency',     emoji: '🛠️', label: '高效率日常工具' },
  { key: 'open-source',    emoji: '🌐', label: '开源找源码' },
]

// ==================== 状态 ====================
const selectedTags = ref([])   // 两个维度合并后的选中 key 列表
const isSubmitting = ref(false)

// ==================== 方法 ====================

/** 切换标签选中状态 */
function toggleTag(key) {
  if (isSubmitting.value) return
  const idx = selectedTags.value.indexOf(key)
  if (idx > -1) {
    selectedTags.value.splice(idx, 1)
  } else {
    selectedTags.value.push(key)
  }
}

/** 提交问卷 —— 将两个维度的标签合并后打包发出 */
async function handleSubmit() {
  if (selectedTags.value.length === 0 || isSubmitting.value) return
  isSubmitting.value = true
  // 合并所有选中的英文 key（已包含角色 + 需求两个维度）
  emit('submit', [...selectedTags.value])
}

/** 父组件通知提交完成（成功或失败都会调用） */
function done() {
  isSubmitting.value = false
}

/** 跳过问卷 */
function handleSkip() {
  if (isSubmitting.value) return
  emit('skip')
}

/** 重置状态（供父组件调用） */
function reset() {
  selectedTags.value = []
  isSubmitting.value = false
}

defineExpose({ reset, done, selectedTags })
</script>

<style scoped>
/* ==================== 遮罩层 ==================== */
.survey-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 20px;
}

/* ==================== 弹窗主体 ==================== */
.survey-modal {
  position: relative;
  width: 100%;
  max-width: 660px;
  max-height: 90vh;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(30px);
  -webkit-backdrop-filter: blur(30px);
  border-radius: 24px;
  padding: 36px 32px 28px;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.12),
    0 2px 8px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.5);
}

/* 暗黑模式 */
:global(.layout.dark-theme) .survey-modal {
  background: rgba(15, 23, 42, 0.92);
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}
:global(.layout.dark-theme) .survey-title,
:global(.layout.dark-theme) .survey-subtitle,
:global(.layout.dark-theme) .section-title,
:global(.layout.dark-theme) .survey-selected-hint,
:global(.layout.dark-theme) .tag-label {
  color: #e2e8f0;
}
:global(.layout.dark-theme) .survey-subtitle,
:global(.layout.dark-theme) .section-hint,
:global(.layout.dark-theme) .hint-dim { color: #94a3b8; }
:global(.layout.dark-theme) .survey-tag-card {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
}
:global(.layout.dark-theme) .survey-tag-selected {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.4);
}
:global(.layout.dark-theme) .section-badge {
  background: rgba(99, 102, 241, 0.2);
  color: #a5b4fc;
}

/* ==================== 装饰光晕 ==================== */
.survey-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.12;
  pointer-events: none;
  z-index: 0;
}
.survey-glow-1 {
  width: 260px; height: 260px;
  top: -60px; right: -60px;
  background: #3b82f6;
}
.survey-glow-2 {
  width: 200px; height: 200px;
  bottom: -40px; left: -40px;
  background: #8b5cf6;
}

/* ==================== 头部 ==================== */
.survey-header {
  position: relative;
  z-index: 1;
  text-align: center;
  margin-bottom: 24px;
}
.survey-icon {
  font-size: 48px;
  margin-bottom: 10px;
  animation: surveyFloat 3s ease-in-out infinite;
}
@keyframes surveyFloat {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-6px); }
}
.survey-title {
  font-size: 1.4rem;
  font-weight: 800;
  margin: 0 0 6px;
  color: #0f172a;
  letter-spacing: 0.5px;
}
.survey-subtitle {
  font-size: 0.85rem;
  color: #64748b;
  margin: 0;
  line-height: 1.6;
}

/* ==================== 维度区块 ==================== */
.survey-section {
  position: relative;
  z-index: 1;
  margin-bottom: 20px;
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 12px;
}
.section-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 0.72rem;
  font-weight: 700;
  background: rgba(99, 102, 241, 0.12);
  color: #6366f1;
  letter-spacing: 0.3px;
}
.section-hint {
  font-size: 0.75rem;
  font-weight: 400;
  color: #94a3b8;
  margin-left: auto;
}

/* ==================== 标签网格 ==================== */
.survey-tags-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.demand-grid {
  grid-template-columns: repeat(2, 1fr);
}
@media (max-width: 500px) {
  .survey-tags-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .demand-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 单个标签卡片 */
.survey-tag-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  background: rgba(0, 0, 0, 0.03);
  border: 1.5px solid rgba(0, 0, 0, 0.08);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
  position: relative;
  overflow: hidden;
}
.survey-tag-card:hover {
  background: rgba(59, 130, 246, 0.06);
  border-color: rgba(59, 130, 246, 0.25);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}
.survey-tag-card:active {
  transform: scale(0.97);
}

/* 需求维度的卡片稍大一点（2列布局） */
.demand-card {
  padding: 14px 16px;
}

/* 选中态 */
.survey-tag-selected {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}
.survey-tag-selected:hover {
  background: rgba(59, 130, 246, 0.14);
}

.tag-emoji {
  font-size: 1.3rem;
  line-height: 1;
  flex-shrink: 0;
}
.tag-label {
  font-size: 0.82rem;
  font-weight: 600;
  color: #334155;
  flex: 1;
  line-height: 1.2;
}
.tag-check {
  width: 20px; height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* ==================== 选中提示 ==================== */
.survey-selected-hint {
  position: relative;
  z-index: 1;
  text-align: center;
  font-size: 0.82rem;
  color: #64748b;
  margin-bottom: 20px;
}
.empty-hint { color: #94a3b8; }
.hint-extra { color: #3b82f6; font-weight: 500; }

/* ==================== 底部按钮 ==================== */
.survey-actions {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
}

.survey-btn-submit {
  width: 100%;
  max-width: 380px;
  padding: 14px 28px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  color: #fff;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.35);
  letter-spacing: 0.5px;
}
.survey-btn-submit:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.45);
}
.survey-btn-submit:active {
  transform: scale(0.97);
}
.survey-btn-submit:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.survey-btn-skip {
  padding: 8px 20px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 0.82rem;
  cursor: pointer;
  transition: color 0.2s;
}
.survey-btn-skip:hover {
  color: #64748b;
}

/* 按钮 loading 动画 */
.btn-loading {
  display: inline-block;
  width: 20px; height: 20px;
  border: 2.5px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: btnSpin 0.7s linear infinite;
}
@keyframes btnSpin { to { transform: rotate(360deg); } }

/* ==================== 入场/退场动画 ==================== */
.survey-fade-enter-active {
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.survey-fade-leave-active {
  transition: all 0.25s ease-in;
}
.survey-fade-enter-from { opacity: 0; }
.survey-fade-enter-from .survey-modal {
  opacity: 0;
  transform: scale(0.9) translateY(20px);
}
.survey-fade-leave-to { opacity: 0; }
.survey-fade-leave-to .survey-modal {
  opacity: 0;
  transform: scale(0.95) translateY(10px);
}
</style>
