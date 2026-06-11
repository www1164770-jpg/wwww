<template>
  <!-- 🔒 安全设置弹窗：修改密码 / 换绑邮箱 / 绑定手机 -->
  <div v-if="currentModalType" class="auth-overlay glass-overlay" @click.self="closeModal">
    <div class="auth-modal edit-modal" @click.stop>
      <button class="close-btn" @click="closeModal">×</button>

      <!-- 修改密码 -->
      <template v-if="currentModalType === 'password'">
        <h2 class="modal-title">修改登录密码</h2>
        <div class="vertical-layout">
          <input
            type="password"
            v-model="modalForm.oldPwd"
            placeholder="请输入当前旧密码"
            class="auth-input"
          />
          <input
            type="password"
            v-model="modalForm.newPwd"
            placeholder="请输入新密码 (至少6位)"
            class="auth-input"
          />
          <input
            type="password"
            v-model="modalForm.confirmPwd"
            placeholder="请再次确认新密码"
            class="auth-input"
          />
          <button class="btn-submit" @click="submitPasswordChange">
            确认修改，并重新登录
          </button>
        </div>
      </template>

      <!-- 换绑邮箱 -->
      <template v-else-if="currentModalType === 'email'">
        <h2 class="modal-title">换绑邮箱</h2>
        <div class="vertical-layout">
          <input
            type="email"
            v-model="modalForm.email"
            placeholder="请输入新邮箱地址"
            class="auth-input"
          />
          <div class="verify-code-row">
            <input
              type="text"
              v-model="modalForm.emailCode"
              placeholder="6位验证码"
              class="auth-input small"
            />
            <button
              class="get-code-btn"
              :disabled="emailCountdown > 0"
              @click="sendEmailCode"
            >
              {{ emailCountdown > 0 ? `${emailCountdown}s 后重发` : '获取验证码' }}
            </button>
          </div>
          <button class="btn-submit" @click="submitEmailBind">确认换绑</button>
        </div>
      </template>

      <!-- 绑定手机 -->
      <template v-else-if="currentModalType === 'phone'">
        <h2 class="modal-title">绑定手机号</h2>
        <div class="vertical-layout">
          <input
            type="tel"
            v-model="modalForm.phone"
            placeholder="请输入手机号码"
            class="auth-input"
          />
          <div class="verify-code-row">
            <input
              type="text"
              v-model="modalForm.phoneCode"
              placeholder="6位短信验证码"
              class="auth-input small"
            />
            <button
              class="get-code-btn"
              :disabled="phoneCountdown > 0"
              @click="sendPhoneCode"
            >
              {{ phoneCountdown > 0 ? `${phoneCountdown}s 后重发` : '获取验证码' }}
            </button>
          </div>
          <button class="btn-submit" @click="submitPhoneBind">立即绑定</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { securityAPI, userAPI } from '@/utils/api'

const emit = defineEmits(['toast', 'logout'])

// --- Props & Emits ---
// 父组件通过 v-model:show 控制弹窗显示
const props = defineProps({
  modelValue: { type: String, default: null },  // 'password' | 'email' | 'phone' | null
  userInfo: { type: Object, default: () => ({ email: '未绑定邮箱', phone: '' }) }
})

const currentModalType = ref(null)

// Watch for changes from parent
import { watch } from 'vue'
watch(() => props.modelValue, (val) => {
  currentModalType.value = val
})

// --- 表单数据 ---
const modalForm = ref({
  oldPwd: '',
  newPwd: '',
  confirmPwd: '',
  email: '',
  emailCode: '',
  phone: '',
  phoneCode: ''
})

// --- 倒计时 ---
const emailCountdown = ref(0)
const phoneCountdown = ref(0)
let emailTimer = null
let phoneTimer = null

// --- 清理 Timer ---
function clearAllTimers() {
  if (emailTimer) { clearInterval(emailTimer); emailTimer = null }
  if (phoneTimer) { clearInterval(phoneTimer); phoneTimer = null }
}

// --- 发送邮箱验证码 ---
const sendEmailCode = async () => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(modalForm.value.email)) {
    return emit('toast', '⚠️ 请输入正确的邮箱格式', 'error')
  }
  try {
    const res = await securityAPI.sendEmailCode(modalForm.value.email)
    if (res.data.code === 0) {
      emit('toast', '📧 验证码已发送至邮箱，请查收', 'success')
      emailCountdown.value = 60
      emailTimer = setInterval(() => {
        emailCountdown.value--
        if (emailCountdown.value <= 0) clearInterval(emailTimer)
      }, 1000)
    } else {
      emit('toast', '❌ ' + res.data.msg, 'error')
    }
  } catch (error) {
    emit('toast', '❌ 发送失败：' + (error.response?.data?.msg || '网络错误'), 'error')
  }
}

// --- 发送手机验证码 ---
const sendPhoneCode = async () => {
  const phoneRegex = /^1[3-9]\d{9}$/
  if (!phoneRegex.test(modalForm.value.phone)) {
    return emit('toast', '⚠️ 请输入正确的11位手机号', 'error')
  }
  try {
    const res = await securityAPI.sendSmsCode(modalForm.value.phone)
    if (res.data.code === 0) {
      emit('toast', '📱 验证码短信已发送', 'success')
      phoneCountdown.value = 60
      phoneTimer = setInterval(() => {
        phoneCountdown.value--
        if (phoneCountdown.value <= 0) clearInterval(phoneTimer)
      }, 1000)
    } else {
      emit('toast', '❌ ' + res.data.msg, 'error')
    }
  } catch (error) {
    emit('toast', '❌ 发送失败：' + (error.response?.data?.msg || '网络错误'), 'error')
  }
}

// --- 提交邮箱绑定 ---
const submitEmailBind = async () => {
  if (!modalForm.value.emailCode) {
    return emit('toast', '⚠️ 请输入验证码', 'error')
  }
  try {
    const res = await securityAPI.bindEmail(modalForm.value.email, modalForm.value.emailCode)
    if (res.data.code === 0) {
      emit('toast', '🎉 邮箱绑定成功！', 'success')
      closeModal()
    } else {
      emit('toast', '❌ ' + res.data.msg, 'error')
    }
  } catch (error) {
    emit('toast', '❌ 绑定失败：' + (error.response?.data?.msg || '验证码错误'), 'error')
  }
}

// --- 提交手机绑定 ---
const submitPhoneBind = async () => {
  if (!modalForm.value.phoneCode) {
    return emit('toast', '⚠️ 请输入验证码', 'error')
  }
  try {
    const res = await securityAPI.bindPhone(modalForm.value.phone, modalForm.value.phoneCode)
    if (res.data.code === 0) {
      emit('toast', '🎉 手机绑定成功！', 'success')
      closeModal()
    } else {
      emit('toast', '❌ ' + res.data.msg, 'error')
    }
  } catch (error) {
    emit('toast', '❌ 绑定失败：' + (error.response?.data?.msg || '验证码错误'), 'error')
  }
}

// --- 提交修改密码 ---
const submitPasswordChange = async () => {
  if (!modalForm.value.oldPwd || !modalForm.value.newPwd || !modalForm.value.confirmPwd) {
    return emit('toast', '⚠️ 请完整填写所有密码项', 'error')
  }
  if (modalForm.value.newPwd !== modalForm.value.confirmPwd) {
    return emit('toast', '⚠️ 两次输入的新密码不一致！', 'error')
  }
  if (modalForm.value.newPwd.length < 6) {
    return emit('toast', '⚠️ 新密码不能少于 6 位', 'error')
  }
  try {
    const res = await userAPI.changePassword(modalForm.value.oldPwd, modalForm.value.newPwd)
    if (res.data.code === 0) {
      emit('toast', '🎉 密码修改成功！请重新登录', 'success')
      closeModal()
      setTimeout(() => { emit('logout') }, 1500)
    } else {
      emit('toast', '❌ ' + res.data.msg, 'error')
    }
  } catch (error) {
    emit('toast', '❌ 修改失败：' + (error.response?.data?.msg || '网络错误'), 'error')
  }
}

// --- 打开弹窗 ---
const openModal = (type) => {
  currentModalType.value = type
}

// --- 关闭弹窗并重置表单 ---
const closeModal = () => {
  currentModalType.value = null
  modalForm.value = {
    oldPwd: '', newPwd: '', confirmPwd: '',
    email: '', emailCode: '',
    phone: '', phoneCode: ''
  }
  emailCountdown.value = 0
  phoneCountdown.value = 0
  clearAllTimers()
}

// 暴露 openModal 方法给父组件调用
defineExpose({ openModal, closeModal })
</script>

<style scoped>
/* 复用父组件的全局样式（auth-overlay, auth-modal, edit-modal 等定义在 style.css 中） */
</style>
