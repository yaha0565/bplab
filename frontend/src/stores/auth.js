import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import request from '../utils/request'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const menus = ref(JSON.parse(localStorage.getItem('menus') || '[]'))

  const isLoggedIn = computed(() => !!token.value)
  const role = computed(() => user.value?.role || '')

  async function login(username, password) {
    const { data } = await request.post('/auth/login', { username, password })
    token.value = data.access_token
    user.value = { username: data.username, display_name: data.display_name, role: data.role }
    menus.value = data.menus || []
    localStorage.setItem('token', token.value)
    localStorage.setItem('user', JSON.stringify(user.value))
    localStorage.setItem('menus', JSON.stringify(menus.value))
    return data
  }

  function logout() {
    token.value = ''
    user.value = null
    menus.value = []
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('menus')
  }

  return { token, user, menus, isLoggedIn, role, login, logout }
})
