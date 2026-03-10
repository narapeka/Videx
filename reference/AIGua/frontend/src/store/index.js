import { defineStore } from 'pinia'
import axios from 'axios'
import { API_ENDPOINTS, API_CONFIG } from '../config/api'

const api = axios.create({
  baseURL: 'http://localhost:8088/api',
  timeout: API_CONFIG.timeout,
  headers: API_CONFIG.headers
})

// 添加扁平化函数
function flattenTree(tree) {
  const result = []
  
  function traverse(node) {
    if (node.isLeaf) {
      result.push({
        original_path: node.original_path,
        selected: node.selected
      })
    } else if (node.children) {
      node.children.forEach(traverse)
    }
  }
  
  tree.forEach(traverse)
  return result
}

// 添加更新文件信息的函数
function updateFilesWithIdentification(tree, identifiedFiles) {
  console.log('开始更新文件信息，当前树:', tree)
  console.log('识别结果:', identifiedFiles)
  
  const updatedTree = tree.map(node => {
    if (node.isLeaf) {
      const identifiedFile = identifiedFiles.find(f => f.original_path === node.original_path)
      console.log('处理文件:', node.original_path)
      console.log('找到的识别结果:', identifiedFile)
      
      if (identifiedFile) {
        const updatedNode = {
          ...node,
          new_name: identifiedFile.new_name,
          chinese_title: identifiedFile.chinese_title,
          english_title: identifiedFile.english_title,
          year: identifiedFile.year,
          tmdb: identifiedFile.tmdb || null,
          error: identifiedFile.error
        }
        console.log('更新后的节点:', updatedNode)
        return updatedNode
      }
    } else if (node.children) {
      return {
        ...node,
        children: updateFilesWithIdentification(node.children, identifiedFiles)
      }
    }
    return node
  })
  
  console.log('更新后的树:', updatedTree)
  return updatedTree
}

export const useStore = defineStore('main', {
  state: () => ({
    files: [],
    selectedFiles: [],
    settings: {
      media_libraries: [],
      grok_api_key: '',
      tmdb_api_key: '',
      grok_batch_size: 20,
      grok_rate_limit: 1,
      tmdb_rate_limit: 50,
      proxy_url: ''
    },
    loading: false,
    error: null,
    initialized: false,  // 添加初始化状态标记
    filesToIdentify: [], // 存储要识别的文件路径列表
    renameResults: null,
    needsSorting: false
  }),

  actions: {
    // 添加初始化方法
    async initialize() {
      if (this.initialized) return
      
      try {
        console.log('正在初始化 store...')
        await this.loadConfig()
        this.initialized = true
        console.log('Store 初始化完成，当前配置:', this.settings)
      } catch (error) {
        console.error('Store 初始化失败:', error)
        throw error
      }
    },

    async scanFiles(fullScan = false) {
      try {
        // 确保 store 已初始化
        if (!this.initialized) {
          await this.initialize()
        }
        
        // 强制刷新配置以确保使用最新的设置
        await this.loadConfig()
        
        this.loading = true
        this.files = []
        this.selectedFiles = []
        
        console.log('当前配置:', this.settings)
        
        // 检查媒体库配置
        if (!this.settings || !this.settings.media_libraries || this.settings.media_libraries.length === 0) {
          console.error('媒体库配置为空')
          throw new Error('请先在设置页面配置媒体库')
        }
        
        // 检查每个媒体库的配置是否完整
        const invalidLibraries = this.settings.media_libraries.filter(lib => !lib.path || !lib.type)
        if (invalidLibraries.length > 0) {
          console.error('无效的媒体库配置:', invalidLibraries)
          throw new Error('媒体库配置不完整，请检查设置')
        }
        
        console.log('开始扫描文件...')
        console.log(`扫描模式: ${fullScan ? '全量扫描' : '增量扫描'}`)
        const response = await api.get('/files/scan', { params: { full_scan: fullScan } })
        console.log('扫描响应:', response.data)
        
        if (!response.data) {
          console.error('扫描响应为空')
          throw new Error('扫描响应为空')
        }
        
        if (!response.data.files) {
          console.warn('扫描响应中没有文件列表:', response.data)
          this.files = []
          return response.data
        }
        
        console.log(`找到 ${response.data.files.length} 个文件`)
        this.files = response.data.files.map(file => ({
          original_path: file,
          selected: true,  // 默认选中所有文件
          new_name: '',
          tmdb: null
        }))
        
        // 标记需要重新排序
        this.needsSorting = true
        
        return response.data
      } catch (error) {
        console.error('扫描文件失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async identifyFiles() {
      if (this.selectedFiles.length === 0) {
        throw new Error('没有选中文件')
      }
      
      try {
        this.loading = true
        
        // 准备要识别的文件路径列表
        const paths = this.filesToIdentify.length > 0 
          ? this.filesToIdentify 
          : this.selectedFiles.map(file => file.original_path)
        
        // 将路径列表转换为后端期望的格式（与原来的格式保持一致）
        const filesToSend = paths.map(path => ({
          original_path: path,
          selected: true
        }))
        
        console.log('准备识别的文件:', filesToSend)
        
        const response = await api.post('/files/identify', filesToSend)
        
        if (response.data && response.data.files) {
          console.log('收到服务器返回的识别结果:', response.data.files)
          
          // 创建一个映射，用于跟踪已使用的电影ID和子文件夹，避免重复分配
          const usedFolderNames = {}
          
          // 更新文件信息，确保一一对应
          response.data.files.forEach(updatedFile => {
            // 使用原始路径查找对应的文件
            const index = this.files.findIndex(file => 
              file.original_path === updatedFile.original_path
            )
            
            if (index !== -1) {
              // 如果找到对应文件，更新信息
              console.log(`更新文件 [${index}]: ${updatedFile.original_path}`)
              console.log(`新文件名: ${updatedFile.new_name}`)
              console.log(`新子文件夹: ${updatedFile.new_sub_folder}`)
              
              // 保留旧文件的其他属性，更新识别相关的信息
              this.files[index] = {
                ...this.files[index],
                new_name: updatedFile.new_name,
                new_sub_folder: updatedFile.new_sub_folder || '',
                tmdb: updatedFile.tmdb || null
              }
              
              // 如果文件有TMDB信息，记录使用情况
              if (updatedFile.new_sub_folder) {
                if (!usedFolderNames[updatedFile.new_sub_folder]) {
                  usedFolderNames[updatedFile.new_sub_folder] = 1
                } else {
                  usedFolderNames[updatedFile.new_sub_folder]++
                }
                console.log(`文件夹 ${updatedFile.new_sub_folder} 已使用 ${usedFolderNames[updatedFile.new_sub_folder]} 次`)
              }
            } else {
              console.warn(`未找到对应的原始文件: ${updatedFile.original_path}`)
            }
          })
          
          // 检查是否有重名问题，并记录日志
          const folderCounts = Object.entries(usedFolderNames)
            .filter(([_, count]) => count > 1)
            .map(([folder, count]) => `${folder}: ${count}个文件`)
          
          if (folderCounts.length > 0) {
            console.log('检测到多个文件映射到相同电影:')
            folderCounts.forEach(info => console.log(info))
          }
        }
        
        // 完成后清空filesToIdentify列表
        this.filesToIdentify = []
        
        return response.data
      } catch (error) {
        console.error('识别文件失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async renameFiles() {
      if (!this.initialized) {
        throw new Error('Store未初始化')
      }
      
      // 检查是否有媒体库配置
      if (!this.settings || !this.settings.media_libraries || this.settings.media_libraries.length === 0) {
        throw new Error('未配置媒体库')
      }
      
      // 获取选中的文件
      const filesToRename = this.selectedFiles.filter(file => 
        file.tmdb && file.tmdb.id && file.new_name && file.new_sub_folder
      )
      
      // 检查是否有可重命名的文件
      if (filesToRename.length === 0) {
        return {
          success: 0,
          warnings: 0,
          errors: 0,
          message: '没有可重命名的文件',
          results: []
        }
      }
      
      try {
        // 发送请求 - 直接发送文件数组，不要包装在files字段中
        console.log('准备重命名的文件:', filesToRename)
        
        // 后端API接口期望直接接收FileInfo对象的数组
        const response = await api.post(API_ENDPOINTS.files.rename, filesToRename)
        
        // 处理响应
        if (response.data && response.data.success) {
          const { success, warnings, errors, results } = response.data
          
          // 更新已重命名文件的状态而不是重新加载所有文件
          // 对每个成功重命名的文件，更新其路径和状态
          if (results && Array.isArray(results)) {
            results.forEach(result => {
              if (result.status === 'success') {
                if (result.operation === 'delete') {
                  // 自动删除的文件逻辑 - 不做额外处理，UI会处理
                  console.log(`后台自动删除了文件: ${result.file}`)
                } 
                else if (result.file && result.new_path) {
                  // 常规重命名逻辑
                  const index = this.files.findIndex(f => f.original_path === result.file)
                  if (index !== -1) {
                    // 设置已重命名标志，务必在更新路径前设置
                    this.files[index].renamed = true
                    
                    // 更新文件路径为新路径
                    this.files[index].original_path = result.new_path
                    
                    // 清空新文件名和新子文件夹
                    this.files[index].new_name = ""
                    this.files[index].new_sub_folder = ""
                    
                    console.log(`文件已标记为重命名: ${result.file} -> ${result.new_path}`)
                  }
                }
              }
            })
          }
          
          // 设置重命名结果 - 确保保留完整结果数据，不做过滤
          this.renameResults = {
            success,
            warnings,
            errors,
            message: `重命名完成。${success} 个成功，${warnings} 个未变更，${errors} 个失败。`,
            results: results || []
          }
          
          return this.renameResults
        } else {
          console.error('重命名失败:', response.data)
          throw new Error(response.data?.message || '重命名失败，请检查文件权限')
        }
      } catch (error) {
        console.error('重命名文件时出错:', error)
        throw error
      }
    },
    
    async loadConfig() {
      this.loading = true
      try {
        const response = await api.get(API_ENDPOINTS.config.get)
        this.settings = response.data
        return response.data
      } catch (error) {
        console.error('加载配置失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async updateConfig(config) {
      this.loading = true
      try {
        console.log('Updating config in store:', config)
        // 确保 media_libraries 是一个数组
        if (!config.media_libraries) {
          config.media_libraries = []
        }
        const response = await api.post(API_ENDPOINTS.config.update, config)
        console.log('Backend response:', response.data)
        if (!response.data) {
          throw new Error('No data returned from backend')
        }
        this.settings = response.data
        return response.data
      } catch (error) {
        console.error('更新配置失败:', error)
        if (error.response) {
          console.error('Error response:', error.response.data)
          throw new Error(error.response.data.detail || '更新配置失败')
        }
        throw error
      } finally {
        this.loading = false
      }
    },
    
    async testConnection() {
      this.loading = true
      try {
        await api.post(API_ENDPOINTS.config.test, this.settings)
      } catch (error) {
        console.error('Connection test failed:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async getDirectories(path) {
      try {
        console.log('Getting directories for path:', path)
        const response = await api.get('/files/directories', { params: { path } })
        console.log('Directories response:', response)
        
        if (!response.data || !response.data.directories || !Array.isArray(response.data.directories)) {
          console.error('Invalid response format:', response)
          throw new Error('目录列表格式错误')
        }
        
        return response.data.directories
      } catch (error) {
        console.error('获取目录列表失败:', error)
        throw error
      }
    },

    // 保存设置
    async saveSettings({ commit }, settings) {
      try {
        console.log('保存设置:', settings)
        // 验证媒体库配置
        if (!settings.media_libraries || settings.media_libraries.length === 0) {
          throw new Error('请至少配置一个媒体库')
        }
        
        // 验证每个媒体库的配置
        for (const library of settings.media_libraries) {
          if (!library.path || !library.type) {
            throw new Error('媒体库配置不完整，请确保每个媒体库都包含路径和类型')
          }
        }
        
        const response = await api.post('/settings', settings)
        console.log('保存设置响应:', response.data)
        commit('SET_SETTINGS', response.data)
        return response.data
      } catch (error) {
        console.error('保存设置失败:', error)
        throw error
      }
    },

    // 设置要识别的文件列表
    setFilesToIdentify(filePaths) {
      this.filesToIdentify = filePaths || []
    },

    async updateIdentifiedFiles(updatedFiles) {
      console.log('更新文件识别信息:', updatedFiles)
      
      for (const updatedFile of updatedFiles) {
        // 找到文件索引
        const index = this.files.findIndex(f => f.original_path === updatedFile.original_path)
        
        if (index !== -1) {
          // 更新文件信息
          console.log(`更新文件: ${this.files[index].original_path}`)
          this.files[index] = {
            ...this.files[index],
            new_name: updatedFile.new_name,
            new_sub_folder: updatedFile.new_sub_folder || '',
            tmdb: updatedFile.tmdb || null
          }
        }
      }
    }
  }
}) 