import axios from 'axios'
import { API_BASE_URL, API_CONFIG } from '../config/api'

// 创建API客户端
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_CONFIG.timeout,
  headers: API_CONFIG.headers
})

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 处理错误
    console.error('API请求失败:', error)
    return Promise.reject(error)
  }
)

export default api 