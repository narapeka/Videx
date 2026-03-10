// API 基础配置
export const API_BASE_URL = 'http://localhost:8088/api'

// API 端点配置
export const API_ENDPOINTS = {
  // 文件相关接口
  files: {
    scan: `${API_BASE_URL}/files/scan`,
    identify: `${API_BASE_URL}/files/identify`,
    rename: `${API_BASE_URL}/files/rename`,
    directories: `${API_BASE_URL}/files/directories`
  },
  
  // 配置相关接口
  config: {
    get: `${API_BASE_URL}/config`,
    update: `${API_BASE_URL}/config`,
    test: `${API_BASE_URL}/config/test`
  },

  directories: {
    list: `${API_BASE_URL}/directories`
  }
}

// API 请求配置
export const API_CONFIG = {
  timeout: 0, // 设置为0表示永不超时
  headers: {
    'Content-Type': 'application/json'
  }
} 