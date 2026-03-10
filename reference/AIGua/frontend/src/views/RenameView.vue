<template>
  <div class="rename-view">
    <div class="header">
      <h2>文件重命名</h2>
      <div class="actions">
        <el-dropdown @command="handleScanCommand" split-button type="primary" @click="scanFiles(false)" :loading="scanning" class="action-btn">
          <template #default>
            <el-icon><Search /></el-icon>
            <span>扫描</span>
          </template>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="incremental">增量扫描</el-dropdown-item>
              <el-dropdown-item command="full">全量扫描</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button type="primary" @click="identifyFiles" :loading="identifying" :disabled="!hasFiles" class="action-btn">
          <el-icon><Film /></el-icon>
          <span>AI识别</span>
        </el-button>
        <el-button type="primary" @click="renameFiles" :loading="renaming" :disabled="!hasFiles" class="action-btn">
          <el-icon><Edit /></el-icon>
          <span>重命名</span>
        </el-button>
      </div>
    </div>

    <!-- 添加进度条 -->
    <div v-if="scanning || identifying || renaming" class="progress-container">
      <el-progress 
        :percentage="progress" 
        :status="progressStatus"
        :stroke-width="15"
        :show-text="true"
        :indeterminate="progress === 0"
        class="progress-bar"
      />
      <div class="progress-text">{{ progressText }}</div>
    </div>

    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="files"
      row-key="original_path"
      border
      style="width: 100%"
      @selection-change="handleSelectionChange"
      :row-class-name="tableRowClassName"
    >
      <el-table-column
        type="selection"
        width="55"
        :selectable="(row) => row.isLeaf && !isFileLocked(row)"
      />
      <el-table-column prop="label" label="文件名" min-width="70%">
        <template #default="scope">
          <div class="file-path" v-if="!scope.row.isLeaf" @click="toggleRow(scope.row)" style="cursor:pointer">
            <el-icon><Folder /></el-icon>
            <span class="library-name">{{ scope.row.label }} ({{ scope.row.type }})</span>
          </div>
          <div class="file-path" v-else>
            <el-icon @click="showFileDetails(scope.row)" style="cursor:pointer"><Document /></el-icon>
            <span class="file-name">
              <template v-if="isFileLocked(scope.row)">
                <span class="lock-tag">[锁定]</span>
              </template>
              <template v-if="scope.row.label.includes('/')">
                <span class="directory-path">{{ scope.row.label.substring(0, scope.row.label.lastIndexOf('/') + 1) }}</span>
                <span>{{ scope.row.label.substring(scope.row.label.lastIndexOf('/') + 1) }}</span>
              </template>
              <template v-else-if="scope.row.label.includes('\\')">
                <span class="directory-path">{{ scope.row.label.substring(0, scope.row.label.lastIndexOf('\\') + 1) }}</span>
                <span>{{ scope.row.label.substring(scope.row.label.lastIndexOf('\\') + 1) }}</span>
              </template>
              <template v-else>
                <span>{{ scope.row.label }}</span>
              </template>
            </span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="new_name" label="新文件名" min-width="30%" show-overflow-tooltip>
        <template #default="scope">
          <el-input
            v-if="scope.row.isLeaf"
            v-model="scope.row.new_name"
            placeholder="请输入新文件名"
            size="small"
            :disabled="scope.row.deleted || isPathDeleted(scope.row.original_path) || isFileLocked(scope.row)"
            :value="isFileLocked(scope.row) ? '' : scope.row.new_name"
          />
        </template>
      </el-table-column>
      <el-table-column prop="tmdb.id" label="TMDB ID" width="120" show-overflow-tooltip>
        <template #default="scope">
          <el-button 
            v-if="scope.row.isLeaf" 
            size="small"
            class="tmdb-id-btn"
            :type="getBtnType(scope.row)"
            @click="handleIdentify(scope.row)"
          >
            {{ getBtnText(scope.row) }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 只有在有日志时才显示日志容器 -->
    <div class="log-container" v-if="logs.length > 0">
      <h3>日志</h3>
      <el-scrollbar height="200px" class="log-scrollbar">
        <div v-for="(log, index) in logs" :key="index" 
             :class="['log-item', log.type ? `type-${log.type}` : '']">
          {{ log.message || log }}
        </div>
      </el-scrollbar>
    </div>
    
    <!-- 当文件已扫描但没有日志时显示提示 -->
    <div class="log-placeholder" v-if="logs.length === 0 && hasScanned">
      <el-icon><InfoFilled /></el-icon>
      <span>操作日志将显示在这里</span>
    </div>
    
    <!-- 添加手工识别对话框 -->
    <el-dialog
      v-model="identifyDialogVisible"
      title="手工识别"
      width="700px"
      :close-on-click-modal="false"
      draggable
      class="identify-dialog"
      append-to-body
    >
      <!-- 搜索表单 -->
      <el-form :model="identifyForm" label-position="top" v-if="!showResults" class="identify-form">
        <!-- 电影信息卡片，无论是否有数据都显示 -->
        <div class="current-movie-info">
          <div class="movie-item">
            <!-- 加载状态 -->
            <div v-if="searching && !currentMovieInfo" class="movie-loading">
              <el-icon class="loading-icon"><Loading /></el-icon>
              <span>正在加载电影信息...</span>
            </div>
            
            <!-- 有电影数据时显示电影信息 -->
            <template v-if="currentMovieInfo">
              <div class="movie-poster" v-if="currentMovieInfo.poster_path">
                <img :src="`https://image.tmdb.org/t/p/w92${currentMovieInfo.poster_path}`" alt="海报" />
              </div>
              <div class="movie-info">
                <div class="movie-title">{{ currentMovieInfo.title }}</div>
                <div class="movie-original-title">
                  {{ currentMovieInfo.original_title }} ({{ currentMovieInfo.year || '未知年份' }})
                </div>
                <div class="movie-overview">{{ currentMovieInfo.overview }}</div>
              </div>
              <!-- 添加评分和热度信息到右上角 -->
              <div class="movie-ratings-corner" v-if="currentMovieInfo.vote_average || currentMovieInfo.popularity">
                <span class="vote" v-if="currentMovieInfo.vote_average">
                  <el-icon><Star /></el-icon> {{ currentMovieInfo.vote_average.toFixed(1) }}
                </span>
                <span class="popularity" v-if="currentMovieInfo.popularity">
                  <el-icon><View /></el-icon> {{ Math.round(currentMovieInfo.popularity) }}
                </span>
              </div>
            </template>
            
            <!-- 无电影数据且不在加载状态时显示占位信息 -->
            <template v-if="!currentMovieInfo && !searching">
              <div class="movie-placeholder">
                <el-icon><Film /></el-icon>
                <span>暂无电影信息</span>
              </div>
            </template>
          </div>
        </div>
        
        <el-form-item label="识别信息">
          <el-input 
            ref="queryInput"
            type="textarea" 
            v-model="identifyForm.query" 
            :autosize="{ minRows: 2, maxRows: 6 }"
            placeholder="请输入影片中文名或英文名"
            resize="none"
            class="query-textarea"
          ></el-input>
        </el-form-item>
        <el-form-item label="年份">
          <el-input v-model="identifyForm.year" placeholder="年份 (可选)" @keyup.enter="searchTMDB"></el-input>
        </el-form-item>
        <el-form-item label="语言">
          <el-select
            v-model="identifyForm.language"
            placeholder="选择语言"
            size="default"
            style="width: 200px"
          >
            <el-option label="zh" value="zh" />
            <el-option label="zh-CN" value="zh-CN" />
            <el-option label="zh-HK" value="zh-HK" />
            <el-option label="zh-SG" value="zh-SG" />
            <el-option label="zh-TW" value="zh-TW" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <!-- 搜索结果 -->
      <div v-if="showResults" class="search-results">
        <el-scrollbar height="420px">
          <div 
            v-for="movie in searchResults" 
            :key="movie.id" 
            class="movie-item"
            :class="{'selected': selectedMovieId === movie.id}"
            @click="selectMovie(movie)"
          >
            <div class="movie-poster" v-if="movie.poster_path">
              <img :src="`https://image.tmdb.org/t/p/w92${movie.poster_path}`" alt="海报" />
              <div class="selected-overlay" v-if="selectedMovieId === movie.id">
                <el-icon class="selecting-icon"><Loading /></el-icon>
              </div>
            </div>
            <div class="movie-info">
              <div class="movie-title">{{ movie.title }}</div>
              <div class="movie-original-title" v-if="movie.original_title !== movie.title">
                {{ movie.original_title }} ({{ movie.year || '未知年份' }})
              </div>
              <div class="movie-overview">{{ movie.overview }}</div>
            </div>
            <!-- 添加评分和热度信息到右上角 -->
            <div class="movie-ratings-corner" v-if="movie.vote_average || movie.popularity">
              <span class="vote" v-if="movie.vote_average">
                <el-icon><Star /></el-icon> {{ movie.vote_average.toFixed(1) }}
              </span>
              <span class="popularity" v-if="movie.popularity">
                <el-icon><View /></el-icon> {{ Math.round(movie.popularity) }}
              </span>
            </div>
          </div>
          <div v-if="searchResults.length === 0" class="no-results">
            无搜索结果，请尝试修改搜索条件
          </div>
        </el-scrollbar>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="cancelSearch">
            {{ showResults ? '返回' : '取消' }}
          </el-button>
          <el-button type="primary" @click="searchTMDB" :loading="searching" v-if="!showResults">
            检索
          </el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 文件详情对话框 -->
    <el-dialog
      v-model="fileDetailsVisible"
      title="文件详情"
      width="500px"
      :close-on-click-modal="true"
      draggable
      class="file-details-dialog"
      append-to-body
    >
      <div v-if="fileDetails" class="file-details">
        <div class="detail-item">
          <span class="detail-label">完整路径:</span>
          <span class="detail-value">{{ fileDetails.fullPath }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">创建时间:</span>
          <span class="detail-value">{{ fileDetails.createdTime }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">修改时间:</span>
          <span class="detail-value">{{ fileDetails.modifiedTime }}</span>
        </div>
        <div class="detail-item">
          <span class="detail-label">文件大小:</span>
          <span class="detail-value">{{ formatFileSize(fileDetails.size) }} ({{ formatFileSizeInKB(fileDetails.size) }})</span>
        </div>
      </div>
      <div v-else class="file-details-loading">
        <el-icon class="loading-icon"><Loading /></el-icon>
        <span>正在加载文件信息...</span>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button type="danger" @click="deleteFile" :loading="deleting">
            <el-icon><Delete /></el-icon>
            <span>删除文件</span>
          </el-button>
          <el-button @click="fileDetailsVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useStore } from '@/store'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Folder, Document, InfoFilled, Search, Film, Edit, Loading, Star, View, Delete } from '@element-plus/icons-vue'
import axios from 'axios'
import api from '@/api'

export default {
  name: 'RenameView',
  components: {
    Folder,
    Document,
    InfoFilled,
    Search,
    Film,
    Edit,
    Loading,
    Star,
    View,
    Delete
  },
  setup() {
    const store = useStore()
    const localLoading = ref(false)
    const scanning = ref(false)
    const identifying = ref(false)
    const renaming = ref(false)
    const progress = ref(0)
    const progressStatus = ref('')
    const progressText = ref('')
    const progressTimer = ref(null)
    const logs = ref([])
    const expandedLibraries = ref({})  // 存储每个媒体库的展开状态
    const tableRef = ref(null)
    const identifyDialogVisible = ref(false)
    const identifyForm = ref({
      language: 'zh-CN'
    })
    const searching = ref(false)
    const showResults = ref(false)
    const searchResults = ref([])
    const hasScanned = ref(false) // 添加标记是否已扫描过文件
    const selectedMovieId = ref(null) // 追踪用户选择的电影ID
    const currentMovieInfo = ref(null)
    const fileDetailsVisible = ref(false)
    const fileDetails = ref(null)
    const deleting = ref(false)
    const deletedFiles = ref({}) // 使用普通对象记录已删除的文件
    
    // 在组件挂载时初始化 store
    onMounted(async () => {
      try {
        await store.initialize()
        console.log('Store 初始化完成')
      } catch (error) {
        console.error('Store 初始化失败:', error)
        ElMessage.error('初始化失败: ' + error.message)
      }
    })
    
    const files = computed(() => {
      const result = []
      
      // 添加媒体库节点
      if (store.settings && store.settings.media_libraries) {
        store.settings.media_libraries.forEach(library => {
          // 添加媒体库节点
          result.push({
            original_path: library.path,
            label: library.name || library.path,
            isLeaf: false,
            type: library.type || '未知类型'
          })
          
          // 如果媒体库已展开，添加该媒体库下的所有文件
          if (expandedLibraries.value[library.path]) {
            // 获取库下所有文件，添加null检查防止undefined错误
            const libraryFiles = (store.files || []).filter(file => 
              file && file.original_path && file.original_path.startsWith(library.path)
            )
            
            // 检查是否需要重新排序文件（只在扫描后或用户明确要求时）
            if (store.needsSorting) {
              // 分组：只区分锁定和未锁定的文件
              const lockedFiles = []
              const unlockedFiles = []
              
              // 将文件分到不同组，并保持原有顺序
              libraryFiles.forEach(file => {
                if (!file || !file.original_path) return // 跳过无效文件
                
                const fileObj = {
                  original_path: file.original_path,
                  label: file.original_path.slice(library.path.length + 1),
                  new_name: file.new_name || '',
                  new_sub_folder: file.new_sub_folder || '',
                  isLeaf: true,
                  selected: file.selected || false,
                  tmdb: file.tmdb || null,
                  deleted: file.deleted || false,
                  renamed: file.renamed || false  // 确保重命名标志被正确保留
                }
                
                // 检查文件是否被锁定
                const isLocked = isFileLocked({ original_path: file.original_path, renamed: file.renamed }) // 传递renamed属性
                
                if (isLocked) {
                  lockedFiles.push(fileObj)
                } else {
                  unlockedFiles.push(fileObj)
                }
              })
              
              // 始终按中文字母排序文件
              const sortByLabel = (a, b) => a.label.localeCompare(b.label, 'zh-CN')
              unlockedFiles.sort(sortByLabel)
              lockedFiles.sort(sortByLabel)
              
              // 添加到结果中：未锁定文件，锁定文件
              result.push(...unlockedFiles, ...lockedFiles)
              
              // 重置排序标志
              store.needsSorting = false
            } else {
              // 不需要重新排序，保持文件当前顺序
              result.push(...libraryFiles.map(file => {
                if (!file || !file.original_path) return null // 跳过无效文件
                
                return {
                  original_path: file.original_path,
                  label: file.original_path.slice(library.path.length + 1),
                  new_name: file.new_name || '',
                  new_sub_folder: file.new_sub_folder || '',
                  isLeaf: true,
                  selected: file.selected || false,
                  tmdb: file.tmdb || null,
                  deleted: file.deleted || false,
                  renamed: file.renamed || false  // 确保重命名标志被正确保留
                }
              }).filter(Boolean)) // 过滤掉null值
            }
          }
        })
      }
      
      return result
    })
    
    const hasFiles = computed(() => files.value.length > 0)
    const loading = computed(() => localLoading.value || store.loading)
    
    const toggleRow = (row) => {
      // 如果当前行是折叠的，则展开它并折叠其他所有行
      if (!expandedLibraries.value[row.original_path]) {
        // 折叠所有行
        Object.keys(expandedLibraries.value).forEach(key => {
          expandedLibraries.value[key] = false
        })
        // 展开当前行
        expandedLibraries.value[row.original_path] = true
      } else {
        // 当前行已展开，则折叠它
        expandedLibraries.value[row.original_path] = false
      }
    }
    
    const addLog = (message) => {
      logs.value.push(`[${new Date().toLocaleTimeString()}] ${message}`)
    }
    
    const startProgress = (status, text) => {
      progress.value = 0
      progressStatus.value = status
      progressText.value = text
      
      // 模拟进度
      progressTimer.value = setInterval(() => {
        if (progress.value < 90) {
          progress.value += 5
        }
      }, 1000)
    }
    
    const stopProgress = (success = true) => {
      if (progressTimer.value) {
        clearInterval(progressTimer.value)
        progressTimer.value = null
      }
      
      if (success) {
        progress.value = 100
        progressStatus.value = 'success'
      } else {
        progressStatus.value = 'exception'
      }
    }
    
    const handleScanCommand = (command) => {
      if (command === 'incremental') {
        scanFiles(false); // 增量扫描
      } else if (command === 'full') {
        scanFiles(true); // 全量扫描
      }
    };
    
    const scanFiles = async (fullScan = false) => {
      try {
        scanning.value = true
        localLoading.value = true
        startProgress('', '正在扫描文件...')
        addLog(`开始${fullScan ? '全量' : '增量'}扫描文件...`)
        await store.scanFiles(fullScan)
        addLog('文件扫描完成')
        ElMessage.success('文件扫描完成')
        stopProgress(true)
        // 设置已扫描标记
        hasScanned.value = true
        
        // 设置需要排序标志
        store.needsSorting = true
        
        // 强制等待表格数据更新
        await nextTick()
        
        // 重置展开状态
        expandedLibraries.value = {} 
        store.settings.media_libraries.forEach(library => {
          expandedLibraries.value[library.path] = true // 默认展开所有媒体库
        })
        
        // 使用setTimeout确保表格完全渲染后再选中文件
        setTimeout(async () => {
          try {
            if (!tableRef.value) {
              console.error('表格引用不存在，无法选中文件')
              addLog('表格引用不存在，无法选中文件')
              return
            }
            
            // 先清除所有选择
            tableRef.value.clearSelection()
            
            // 等待清除操作完成
            await nextTick()
            
            // 获取所有叶子节点（实际文件）且未锁定的文件
            const leafFiles = files.value.filter(file => file.isLeaf && !isFileLocked(file))
            
            // 日志记录找到的文件数量
            console.log(`找到 ${leafFiles.length} 个未锁定文件准备选中`)
            addLog(`找到 ${leafFiles.length} 个未锁定文件`)
            
            // 如果没有找到文件则提前返回
            if (leafFiles.length === 0) {
              addLog('没有找到可选中的未锁定文件')
              return
            }
            
            // 一次性选中所有未锁定文件
            for (const file of leafFiles) {
              tableRef.value.toggleRowSelection(file, true)
            }
            
            // 更新store中的选中文件状态
            store.selectedFiles = leafFiles
            
            // 添加日志记录选中结果
            addLog(`已选中 ${leafFiles.length} 个文件`)
            console.log(`成功选中 ${leafFiles.length} 个文件`)
          } catch (error) {
            console.error('选中文件失败:', error)
            addLog('选中文件失败: ' + error.message)
          }
        }, 100)
      } catch (error) {
        console.error('扫描文件失败:', error)
        addLog('扫描文件失败: ' + error.message)
        ElMessage.error('扫描文件失败: ' + error.message)
        stopProgress(false)
      } finally {
        scanning.value = false
        localLoading.value = false
      }
    }
    
    const identifyFiles = async () => {
      try {
        identifying.value = true
        localLoading.value = true
        startProgress('', '正在识别文件...')
        addLog('开始识别文件...')
        
        // 获取当前选中的文件
        const selectedFiles = [...store.selectedFiles]
        
        // 筛选出没有TMDB ID的文件，只对这些文件进行AI识别
        const filesToIdentify = selectedFiles.filter(file => 
          !file.tmdb || !file.tmdb.id
        )
        
        // 记录日志
        addLog(`从 ${selectedFiles.length} 个选中文件中，过滤出 ${filesToIdentify.length} 个无TMDB ID的文件进行AI识别`)
        console.log(`从 ${selectedFiles.length} 个选中文件中，过滤出 ${filesToIdentify.length} 个无TMDB ID的文件进行AI识别`)
        
        // 设置要识别的文件路径列表
        await store.setFilesToIdentify(filesToIdentify.map(file => file.original_path))
        
        // 调用AI识别接口
        await store.identifyFiles()
        
        addLog('文件识别完成')
        ElMessage.success('文件识别完成')
        stopProgress(true)
        
        // 强制更新表格数据
        await nextTick()
        expandedLibraries.value = {} // 重置展开状态
        store.settings.media_libraries.forEach(library => {
          expandedLibraries.value[library.path] = true // 默认展开所有媒体库
        })
        
        // 等待表格更新完成
        await nextTick()
        
        // 清除所有选择
        tableRef.value.clearSelection()
        
        // 获取所有有 TMDB ID 的文件且未锁定的文件（包括原本就有的和新识别的）
        const filesWithTmdb = files.value.filter(file => 
          file.isLeaf && file.tmdb && file.tmdb.id && !isFileLocked(file)
        )
        
        // 只选中未锁定的有TMDB ID的文件
        filesWithTmdb.forEach(file => {
          tableRef.value.toggleRowSelection(file, true)
        })
        
        // 更新 store 中的选中文件
        store.selectedFiles = filesWithTmdb
        
        // 添加日志
        addLog(`已自动选中 ${filesWithTmdb.length} 个成功识别的文件`)
      } catch (error) {
        console.error('识别文件失败:', error)
        addLog('识别文件失败: ' + error.message)
        ElMessage.error('识别文件失败: ' + error.message)
        stopProgress(false)
      } finally {
        identifying.value = false
        localLoading.value = false
      }
    }
    
    const renameFiles = async () => {
      try {
        renaming.value = true
        localLoading.value = true
        startProgress('', '正在重命名文件...')
        addLog('开始重命名文件...')
        
        // 保存当前所有选中的文件
        const currentSelectedFiles = [...store.selectedFiles]
        
        // 调用store的renameFiles方法并获取结果
        const result = await store.renameFiles()
        
        // 处理返回的结果
        if (result) {
          const { message, success, warnings, errors } = result
          
          // 显示操作结果
          let type = 'success'
          if (errors > 0 && success === 0) {
            type = 'error'
          } else if (errors > 0 || warnings > 0) {
            type = 'warning'
          }
          
          ElMessage({
            message: message,
            type: type,
            duration: 5000
          })
          
          // 记录日志
          addLog(message)
          
          // 如果有详细结果，记录到日志
          if (result.results && result.results.length > 0) {
            // 记录成功的操作
            const successResults = result.results.filter(r => r.status === 'success')
            if (successResults.length > 0) {
              addLog(`成功重命名的文件: ${successResults.length}个`)
              successResults.forEach(r => {
                logs.value.push({
                  type: 'success',
                  message: r.message
                })
                
                // 更新文件状态为已重命名，不重新加载表格
                if (r.file) {
                  // 查找store中的文件
                  const fileToUpdate = store.files.find(f => f.original_path === r.file)
                  if (fileToUpdate) {
                    // 设置为已重命名状态，同时标记为已锁定
                    fileToUpdate.renamed = true
                    if (fileToUpdate.tmdb && fileToUpdate.tmdb.id) {
                      // 更新原始路径
                      fileToUpdate.original_path = r.new_path || fileToUpdate.original_path
                    }
                    addLog(`标记文件为已重命名: ${r.file} -> ${r.new_path || '相同路径'}`)
                  } else {
                    addLog(`警告: 找不到要更新的文件: ${r.file}`)
                  }
                }
              })
            }
            
            // 记录未变更的操作
            const warningResults = result.results.filter(r => r.status === 'warning')
            if (warningResults.length > 0) {
              addLog(`未变更的文件: ${warningResults.length}个`)
              warningResults.forEach(r => {
                logs.value.push({
                  type: 'warning',
                  message: r.message
                })
                
                // 处理已解锁但未修改的文件，重新标记为已重命名
                if (r.file) {
                  // 查找store中的文件
                  const fileToUpdate = store.files.find(f => f.original_path === r.file)
                  if (fileToUpdate) {
                    // 设置为已重命名状态，这样会重新锁定文件
                    fileToUpdate.renamed = true
                    addLog(`重新锁定未变更文件: ${r.file}`)
                  }
                }
              })
            }
            
            // 记录失败的操作
            const errorResults = result.results.filter(r => r.status === 'error')
            if (errorResults.length > 0) {
              addLog(`重命名失败的文件: ${errorResults.length}个`)
              errorResults.forEach(r => {
                logs.value.push({
                  type: 'error',
                  message: r.message
                })
              })
            }
            
            // 处理自动删除的文件结果
            const deletedResults = result.results.filter(r => r.operation === 'delete' && r.status === 'success')
            if (deletedResults.length > 0) {
              addLog(`自动删除的重复文件: ${deletedResults.length}个`)
              
              // 处理每个被删除的文件
              deletedResults.forEach(r => {
                logs.value.push({
                  type: 'warning',
                  message: `自动删除重复文件: ${r.file}`
                })
                
                if (r.file) {
                  // 标记文件为已删除，就像手动删除时一样
                  const filePath = r.file
                  deletedFiles.value[filePath] = true
                  
                  // 找到对应的文件对象
                  const fileToUpdate = store.files.find(f => f.original_path === filePath)
                  if (fileToUpdate) {
                    // 设置删除标记，直接修改store中的文件对象
                    fileToUpdate.deleted = true
                    addLog(`标记文件为已删除（重复）: ${filePath}`)
                  } else {
                    addLog(`警告: 找不到被自动删除的文件: ${filePath}`)
                  }
                }
              })
            }
          }
          
          stopProgress(true)
          
          // 不完全重置表格，只触发一次更新以刷新状态
          await nextTick()
          
          // 重置选择状态，然后还原
          tableRef.value.clearSelection()
          
          // 重新应用选中状态（除去已重命名/已锁定的文件）
          for (const file of currentSelectedFiles) {
            const fileInTable = files.value.find(f => 
              f.original_path === file.original_path && f.isLeaf && !isFileLocked(f)
            )
            if (fileInTable) {
              tableRef.value.toggleRowSelection(fileInTable, true)
            }
          }
          
          // 更新store中的选中文件
          store.selectedFiles = store.selectedFiles.filter(f => !isFileLocked(f))
          
          // 添加额外的日志帮助调试
          const filesWithRenamed = store.files.filter(file => file.renamed)
          addLog(`【调试】重命名后，有 ${filesWithRenamed.length} 个文件标记为已重命名状态`)
          
          // 确保更新files计算属性
          nextTick(() => {
            // 重新检查锁定状态
            const lockedCount = files.value.filter(f => isFileLocked(f)).length
            addLog(`【调试】当前有 ${lockedCount} 个文件处于锁定状态`)
          })
          
        } else {
          ElMessage.error('重命名操作未返回结果')
          addLog('重命名操作未返回结果')
          stopProgress(false)
        }
      } catch (error) {
        console.error('重命名文件失败:', error)
        addLog('重命名文件失败: ' + (error.message || String(error)))
        ElMessage.error('重命名文件失败: ' + (error.message || String(error)))
        stopProgress(false)
        // 添加错误日志
        logs.value.push({
          type: 'error',
          message: `重命名失败: ${error.message || String(error)}`
        })
      } finally {
        // 确保状态重置，延迟一点以确保UI更新完成
        setTimeout(() => {
          renaming.value = false
          localLoading.value = false
        }, 300)
      }
    }
    
    const handleSelectionChange = (selection) => {
      // 保存当前选中状态的引用，以便在toggleFileLock中使用
      const currentStoreFiles = store.selectedFiles || []
      
      // 如果是toggleFileLock内部调用tableRef.toggleRowSelection导致的选择变化
      // 并且selection的长度小于当前store中的选中文件数量，则可能是选择被清空了
      // 在这种情况下，我们应该保留现有选择并添加/移除特定文件
      if (selection.length === 0 && currentStoreFiles.length > 0) {
        // 这可能是一个误触发，不更新选择状态
        console.log('忽略可能的误触发选择清空事件')
        return
      }
      
      // 常规选择变更处理
      // 更新所有文件的选中状态
      files.value.forEach(file => {
        if (file.isLeaf) {
          file.selected = selection.some(item => item.original_path === file.original_path)
        }
      })
      
      // 更新 store 中的选中文件
      store.selectedFiles = selection.filter(file => file.isLeaf)
      
      // 添加日志
      addLog(`选中状态已更新，当前选中 ${store.selectedFiles.length} 个文件`)
    }
    
    const formatFileName = (fileName) => {
      return fileName // 直接返回原始文件名，不做截取
    }
    
    // 从文件名中提取年份
    const extractYearFromFileName = (fileName) => {
      // 匹配四位数字年份，通常这些年份会在1900-2099之间
      const yearRegex = /\b(19\d{2}|20\d{2})\b/;
      const match = fileName.match(yearRegex);
      return match ? match[1] : '';
    }
    
    // 规范化文件名以用于搜索
    const normalizeFileName = (fileName, year) => {
      // 步骤1: 移除文件扩展名
      let normalized = fileName.replace(/\.[^/.]+$/, "");
      
      // 步骤2: 替换点号和方括号为空格
      normalized = normalized.replace(/\./g, " ");  // 将所有点号替换为空格
      normalized = normalized.replace(/[\[\]]/g, " ");  // 将所有方括号替换为空格
      
      // 不再执行以下步骤：
      // - 移除年份
      // - 提取括号内容
      // - 移除标点符号
      // - 重新添加括号内容
      
      // 只做最基本的空格清理
      normalized = normalized.trim();
      // 处理可能的连续空格
      normalized = normalized.replace(/\s+/g, " ");
      
      return normalized;
    }
    
    const tableRowClassName = ({ row }) => {
      if (row.isLeaf) {
        // 优先检查是否已重命名，确保样式正确应用
        if (row.renamed) {
          return 'renamed-file'
        } else if (row.deleted || isPathDeleted(row.original_path)) {
          return 'deleted-file'
        } else if (isFileLocked(row)) {
          return 'locked-file'
        } else if (!row.tmdb || !row.tmdb.id) {
          return 'no-tmdb-id'
        }
      }
      return ''
    }
    
    const handleIdentify = (row) => {
      // 如果文件被锁定，则解锁它
      if (isFileLocked(row)) {
        toggleFileLock(row)
        return
      }
      
      // 重置对话框状态，确保每次打开都显示搜索表单而不是结果
      showResults.value = false
      searchResults.value = []
      currentMovieInfo.value = null
      
      // 从文件名中提取文件名（移除路径部分）
      const fileName = row.label;
      // 提取真正的文件名（不含路径）
      const fileNameOnly = fileName.split(/[\/\\]/).pop();
      
      // 从文件名中提取年份
      const extractedYear = extractYearFromFileName(fileNameOnly);
      
      // 规范化文件名用于搜索
      const normalizedFileName = normalizeFileName(fileNameOnly, extractedYear);
      
      identifyDialogVisible.value = true
      // 如果有TMDB数据，预填充电影中文名
      identifyForm.value = {
        ...identifyForm.value,
        query: row.tmdb && row.tmdb.title ? row.tmdb.title : normalizedFileName,
        year: row.tmdb && row.tmdb.year ? row.tmdb.year.toString() : extractedYear,
        filePath: row.original_path  // 保存文件路径以便后续更新
      }
      
      // 检查文件名是否包含tmdb ID
      if (row.tmdb && row.tmdb.id) {
        // 加载TMDB电影信息
        loadMovieById(row.tmdb.id);
      }
      
      // 添加延迟以确保对话框完全打开
      setTimeout(() => {
        if (queryInput.value) {
          queryInput.value.focus();
        }
      }, 300);
    }
    
    const searchTMDB = async () => {
      try {
        if (!identifyForm.value.query) {
          ElMessage.warning('请输入搜索关键词')
          return
        }
        
        if (!identifyForm.value.filePath) {
          ElMessage.warning('未选择要识别的文件')
          return
        }
        
        searching.value = true
        searchResults.value = []
        showResults.value = false
        selectedMovieId.value = null
        
        const selectedLanguage = identifyForm.value.language ? `, 语言: ${identifyForm.value.language}` : ''
        addLog(`搜索TMDB: ${identifyForm.value.query}${identifyForm.value.year ? ` (${identifyForm.value.year})` : ''}${selectedLanguage}`)
        
        const response = await api.post('/files/search_tmdb', {
          query: identifyForm.value.query,
          year: identifyForm.value.year,
          language: identifyForm.value.language,
          file_path: identifyForm.value.filePath
        })
        
        if (response.data && response.data.success) {
          // 检查是返回搜索结果
          if (response.data.results) {
            // 显示搜索结果，按热度排序
            searchResults.value = response.data.results.sort((a, b) => {
              return (b.popularity || 0) - (a.popularity || 0)
            })
            showResults.value = true
            addLog(`TMDB检索完成，找到 ${searchResults.value.length} 个相关电影`)
          } else {
            // 旧版API可能会直接返回file对象，为了兼容性保留此逻辑
            if (response.data.file) {
              // 更新文件信息
              await updateFileWithTMDBInfo(response.data.file)
              identifyDialogVisible.value = false
            } else {
              addLog('API返回了成功但格式不正确')
              ElMessage.warning('API返回了成功但格式不正确')
            }
          }
        } else {
          addLog('TMDB检索未找到匹配的电影')
          ElMessage.warning('未找到匹配的电影')
        }
      } catch (error) {
        console.error('检索TMDB失败:', error)
        addLog('检索TMDB失败: ' + (error.response?.data?.detail || error.message))
        ElMessage.error('检索TMDB失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        searching.value = false
      }
    }
    
    const selectMovie = async (movie) => {
      try {
        searching.value = true
        selectedMovieId.value = movie.id // 记录当前选中的电影ID
        addLog(`选择电影: ${movie.title} (${movie.year || '未知年份'})`)
        
        // 添加短暂延迟使视觉反馈更明显
        await new Promise(resolve => setTimeout(resolve, 200))
        
        // 通过 get_movie_by_id 获取电影详情（含中文标题：若原标题无中文则从 alternative_titles/translations 取）
        let movieInfo = movie
        if (identifyForm.value.filePath && movie.id) {
          try {
            const response = await api.post('/files/get_movie_by_id', {
              movie_id: typeof movie.id === 'string' ? parseInt(movie.id, 10) : movie.id,
              file_path: identifyForm.value.filePath
            })
            if (response.data && response.data.success && response.data.results && response.data.results.length > 0) {
              movieInfo = response.data.results[0]
              addLog(`已使用 TMDB 中文名: ${movieInfo.title}`)
            }
          } catch (err) {
            console.warn('get_movie_by_id 失败，使用搜索结果数据', err)
          }
        }
        
        // 检查是否有年份，没有年份则提示用户并取消操作
        if (!movieInfo.year) {
          addLog(`警告: 电影 ${movieInfo.title} 未获取到年份信息，无法生成标准命名`)
          ElMessage.warning(`电影 ${movieInfo.title} 未获取到年份信息，无法生成标准命名`)
          identifyDialogVisible.value = false
          return
        }
        
        // 移除非法路径字符（如 / * 等），用于文件夹和文件名
        const sanitizePathComponent = (s) => {
          if (!s || typeof s !== 'string') return s || ''
          return s.replace(/[\\/:*?"<>|]/g, '').replace(/\s+/g, ' ').trim()
        }
        // 生成子文件夹名称（使用含中文的 title），并移除非法字符
        const folderName = sanitizePathComponent(`${movieInfo.title} (${movieInfo.year}) {tmdb-${movieInfo.id}}`)
        // 生成文件名（不再添加后缀），并移除非法字符
        const baseFileName = sanitizePathComponent(`${movieInfo.title} (${movieInfo.year})`)
        const fileExtension = getFileExtension(identifyForm.value.filePath)
        const fileName = `${baseFileName}${fileExtension}`
        
        // 构建文件信息对象
        const fileInfo = {
          original_path: identifyForm.value.filePath,
          new_name: fileName,
          new_sub_folder: folderName,
          tmdb: {
            id: movieInfo.id,
            title: movieInfo.title,
            original_title: movieInfo.original_title,
            year: movieInfo.year,
            overview: movieInfo.overview || '',
            poster_path: movieInfo.poster_path || '',
            vote_average: movieInfo.vote_average || 0,
            popularity: movieInfo.popularity || 0
          }
        }
        
        // 更新文件信息（已包含选中状态处理）
        await updateFileWithTMDBInfo(fileInfo)
        
        // 添加短暂延迟和过渡效果
        await new Promise(resolve => setTimeout(resolve, 300))
        
        // 先隐藏结果，后关闭对话框，使过渡更平滑
        showResults.value = false
        await nextTick()
        identifyDialogVisible.value = false
        
      } catch (error) {
        console.error('选择电影失败:', error)
        addLog('选择电影失败: ' + (error.response?.data?.detail || error.message))
        ElMessage.error('选择电影失败: ' + (error.response?.data?.detail || error.message))
        selectedMovieId.value = null // 重置选中状态
      } finally {
        searching.value = false
      }
    }
    
    // 获取文件扩展名的辅助函数
    const getFileExtension = (filepath) => {
      if (!filepath) return '';
      const parts = filepath.split('.');
      return parts.length > 1 ? `.${parts[parts.length - 1]}` : '';
    }
    
    const cancelSearch = () => {
      if (showResults.value) {
        // 返回搜索表单
        showResults.value = false
        searchResults.value = []
      } else {
        // 关闭对话框
        identifyDialogVisible.value = false
      }
    }
    
    const updateFileWithTMDBInfo = async (updatedFile) => {
      // 保存当前所有选中的文件
      const currentSelectedFiles = [...store.selectedFiles];
      
      // 更新store中的文件信息
      store.files = store.files.map(file => {
        if (file.original_path === updatedFile.original_path) {
          // 更新这个文件的信息，但不设置renamed=true，因为此时只是识别了文件，还没有重命名
          return {
            ...file,
            new_name: updatedFile.new_name,
            new_sub_folder: updatedFile.new_sub_folder,
            tmdb: updatedFile.tmdb
          }
        }
        return file
      })
      
      // 等待表格更新
      await nextTick()
      
      // 重新应用所有文件的选中状态
      currentSelectedFiles.forEach(selectedFile => {
        const fileInTable = files.value.find(f => 
          f.original_path === selectedFile.original_path && f.isLeaf && !isFileLocked(f)
        )
        if (fileInTable) {
          tableRef.value.toggleRowSelection(fileInTable, true)
        }
      })
      
      // 确保更新后的文件也被选中（如果它不是锁定状态）
      const updatedFileInTable = files.value.find(f => 
        f.original_path === updatedFile.original_path && f.isLeaf && !isFileLocked(f)
      )
      
      if (updatedFileInTable) {
        // 检查是否已在当前选中文件中
        const isAlreadySelected = currentSelectedFiles.some(
          f => f.original_path === updatedFileInTable.original_path
        )
        
        // 如果不在当前选中文件中，添加它
        if (!isAlreadySelected) {
          tableRef.value.toggleRowSelection(updatedFileInTable, true)
          // 更新store中的选中文件
          store.selectedFiles = [...currentSelectedFiles, updatedFileInTable]
        } else {
          // 如果已在选中文件中，确保store.selectedFiles包含最新版本
          store.selectedFiles = currentSelectedFiles.map(f => 
            f.original_path === updatedFileInTable.original_path ? updatedFileInTable : f
          )
        }
      } else {
        // 如果文件不在表格中或已锁定，恢复原始选中状态
        store.selectedFiles = currentSelectedFiles
      }
      
      addLog(`TMDB识别完成，找到电影：${updatedFile.tmdb.title} (${updatedFile.tmdb.year})`)
      ElMessage.success(`电影识别成功：${updatedFile.tmdb.title}`)
    }
    
    // 检查文件是否符合命名标准（包含tmdb-xxxx）
    const isStandardNamed = (row) => {
      // 检查原始路径是否包含 {tmdb-数字} 格式
      if (!row.original_path) return false
      
      // 检查路径中是否有 {tmdb-数字} 格式
      const tmdbPattern = /\{tmdb-\d+\}/
      return tmdbPattern.test(row.original_path)
    }
    
    // 文件锁定状态记录
    const lockedFiles = ref({})
    
    // 检查文件是否被锁定
    const isFileLocked = (row) => {
      // 如果文件已被删除，视为锁定且不可解锁
      if (row.deleted || isPathDeleted(row.original_path)) {
        return true
      }
      
      // 检查renamed状态 - 重命名后的文件也可以解锁
      if (row.renamed) {
        // 检查是否已手动解锁
        if (row.original_path in lockedFiles.value) {
          return lockedFiles.value[row.original_path]
        }
        // 默认重命名后是锁定的
        return true
      }
      
      // 如果文件有TMDB ID但没有年份，不应该被锁定
      if (row.tmdb && row.tmdb.id && (!row.tmdb.year || row.tmdb.year === 'null' || row.tmdb.year === 'undefined')) {
        return false
      }
      
      // 如果文件符合命名标准且未被手动解锁，则认为它是锁定的
      if (row.original_path in lockedFiles.value) {
        return lockedFiles.value[row.original_path]
      }
      return isStandardNamed(row)
    }
    
    // 切换文件锁定状态
    const toggleFileLock = (row) => {
      if (row.original_path) {
        // 检查是否是重命名后的文件或标准命名文件
        if (row.renamed || isStandardNamed(row)) {
          // 默认是锁定的，切换为解锁
          lockedFiles.value[row.original_path] = false
          addLog(`已解锁文件: ${row.label}`)
          
          // 解锁后，把文件设为选中状态，但不触发selection-change事件
          const currentSelectedFiles = [...store.selectedFiles]
          
          // 只有当文件不在当前选中的文件列表中时才添加
          if (!currentSelectedFiles.some(file => file.original_path === row.original_path)) {
            // 使用nextTick确保DOM已更新，文件已解锁
            nextTick(() => {
              // 选中该文件但不触发handleSelectionChange
              tableRef.value.toggleRowSelection(row, true)
              
              // 手动更新store中的选中文件，添加新解锁的文件
              store.selectedFiles = [...currentSelectedFiles, row]
            })
          }
        } else {
          // 如果之前解锁了，现在恢复锁定状态
          if (row.original_path in lockedFiles.value) {
            delete lockedFiles.value[row.original_path]
            addLog(`已锁定文件: ${row.label}`)
            
            // 锁定后，移除选中状态，但不影响其他文件
            nextTick(() => {
              // 取消选中该文件
              tableRef.value.toggleRowSelection(row, false)
              
              // 从store中的选中文件中移除该文件
              store.selectedFiles = store.selectedFiles.filter(
                file => file.original_path !== row.original_path
              )
            })
          }
        }
      }
    }
    
    // 判断是否是高度可信的识别结果
    const isHighlyReliableMatch = (row) => {
      // 必须具备TMDB标题、年份以及原始路径信息
      if (!row.tmdb || !row.tmdb.title || !row.tmdb.year || !row.original_path) {
        return false
      }

      const normalizeForMatch = (value) => {
        if (!value) return ''
        return value
          .toString()
          .normalize('NFKC')
          .replace(/[^a-z0-9\u4e00-\u9fa5]+/gi, ' ')
          .replace(/\s+/g, ' ')
          .toLowerCase()
          .trim()
      }

      const normalizedTitle = normalizeForMatch(row.tmdb.title)
      const yearTokenMatch = (row.tmdb.year ?? '').toString().match(/\d{4}/)
      const normalizedYear = yearTokenMatch ? yearTokenMatch[0] : ''

      if (!normalizedTitle || !normalizedYear) {
        return false
      }

      // 提取文件名（不含路径与扩展名）
      let fileNameSource = row.label || row.original_path
      if (fileNameSource.includes('/')) {
        fileNameSource = fileNameSource.split('/').pop()
      } else if (fileNameSource.includes('\\')) {
        fileNameSource = fileNameSource.split('\\').pop()
      }
      fileNameSource = fileNameSource.replace(/\.[^/.]+$/, '')

      const normalizedFileName = normalizeForMatch(fileNameSource)

      // 目录路径部分（去除文件名）
      let directoryPath = row.label || row.original_path
      if (directoryPath.includes('/')) {
        directoryPath = directoryPath.substring(0, directoryPath.lastIndexOf('/'))
      } else if (directoryPath.includes('\\')) {
        directoryPath = directoryPath.substring(0, directoryPath.lastIndexOf('\\'))
      } else {
        directoryPath = ''
      }
      const normalizedDirPath = normalizeForMatch(directoryPath)

      // 完整原始路径
      const normalizedOriginalPath = normalizeForMatch(row.original_path)

      const searchSources = [normalizedFileName, normalizedDirPath, normalizedOriginalPath].filter(Boolean)

      const titleMatch = searchSources.some((source) => source.includes(normalizedTitle))
      const yearMatch = searchSources.some((source) => source.includes(normalizedYear))

      return titleMatch && yearMatch
    }
    
    // 获取按钮类型
    const getBtnType = (row) => {
      // 如果文件已被删除，返回info类型（灰色按钮）
      if (row.deleted || (row.original_path && deletedFiles && row.original_path in deletedFiles.value)) {
        return 'info'
      }
      
      if (isFileLocked(row)) {
        return 'success'
      }
      
      // 如果有TMDB ID，但没有年份信息，使用警告样式
      if (row.tmdb && row.tmdb.id && (!row.tmdb.year || row.tmdb.year === 'null' || row.tmdb.year === 'undefined')) {
        return 'warning'
      }
      
      // 如果有TMDB ID和年份，判断是否高度可信
      if (row.tmdb && row.tmdb.id && row.tmdb.year) {
        // 高度可信的识别结果保持primary类型
        if (isHighlyReliableMatch(row)) {
          return 'primary'
        }
        // 一般可信的识别结果使用蓝色（info类型修改后的样式）
        return 'info'
      }
      
      // 未识别的文件
      return 'warning'
    }
    
    // 获取按钮文本
    const getBtnText = (row) => {
      // 如果文件已被删除，返回"不可用"文本
      if (row.deleted || (row.original_path && deletedFiles && row.original_path in deletedFiles.value)) {
        return '不可用'
      }
      
      if (isFileLocked(row)) {
        return '修改'
      }
      
      // 如果有TMDB ID但没有年份信息
      if (row.tmdb && row.tmdb.id && (!row.tmdb.year || row.tmdb.year === 'null' || row.tmdb.year === 'undefined')) {
        return '缺少年份'
      }
      
      // 如果有TMDB ID和年份
      if (row.tmdb && row.tmdb.id && row.tmdb.year) {
        // 高度可信的识别结果添加勾号
        if (isHighlyReliableMatch(row)) {
          return `✓ ${row.tmdb.id}`
        }
        return row.tmdb.id
      }
      
      return '手工识别'
    }
    
    // 简化loadMovieById函数，使用专门的端点
    const loadMovieById = async (movieId) => {
      try {
        searching.value = true;
        addLog(`加载TMDB电影信息: ID=${movieId}`);
        
        // 调用专门的获取电影详情接口
        const response = await api.post('/files/get_movie_by_id', {
          movie_id: movieId,
          file_path: identifyForm.value.filePath
        });
        
        if (response.data && response.data.success) {
          if (response.data.results && response.data.results.length > 0) {
            // 从results中获取第一个结果 (使用新的API响应格式)
            const movieInfo = response.data.results[0];
            
            currentMovieInfo.value = {
              id: movieInfo.id,
              title: movieInfo.title,
              original_title: movieInfo.original_title || movieInfo.title,
              year: movieInfo.year || '',
              overview: movieInfo.overview || '暂无简介',
              poster_path: movieInfo.poster_path || '',
              vote_average: movieInfo.vote_average || 0,
              popularity: movieInfo.popularity || 0
            };
            addLog(`成功加载电影信息: ${currentMovieInfo.value.title}`);
          } else if (response.data.file && response.data.file.tmdb) {
            // 兼容旧版API响应格式
            const tmdb = response.data.file.tmdb;
            
            currentMovieInfo.value = {
              id: tmdb.id,
              title: tmdb.title,
              original_title: tmdb.original_title || tmdb.title,
              year: tmdb.year || '',
              overview: tmdb.overview || '暂无简介',
              poster_path: tmdb.poster_path || '',
              vote_average: tmdb.vote_average || 0,
              popularity: tmdb.popularity || 0
            };
            addLog(`成功加载电影信息: ${currentMovieInfo.value.title}`);
          } else {
            addLog('服务器返回的数据格式不正确');
            ElMessage.warning('无法解析电影信息');
          }
        } else {
          addLog('无法加载电影信息');
          ElMessage.warning('无法加载电影信息');
        }
      } catch (error) {
        console.error('加载电影信息失败:', error);
        addLog('加载电影信息失败: ' + (error.response?.data?.detail || error.message));
        ElMessage.error('加载电影信息失败');
      } finally {
        searching.value = false;
      }
    }
    
    // 显示文件详情对话框
    const showFileDetails = async (file) => {
      // 重置文件详情
      fileDetails.value = null
      fileDetailsVisible.value = true
      
      try {
        // 调用后端API获取文件详情
        const response = await api.post('/files/get_file_details', {
          file_path: file.original_path
        })
        
        // 后端直接返回数据对象，不包含success字段
        if (response.data) {
          // 更新文件详情，使用正确的字段名
          fileDetails.value = {
            fullPath: response.data.full_path || file.original_path,
            createdTime: response.data.creation_time,
            modifiedTime: response.data.modification_time,
            size: response.data.size
          }
        } else {
          ElMessage.error('获取文件详情失败')
          fileDetailsVisible.value = false
        }
      } catch (error) {
        console.error('获取文件详情失败:', error)
        ElMessage.error('获取文件详情失败: ' + (error.response?.data?.detail || error.message))
        fileDetailsVisible.value = false
      }
    }
    
    // 格式化文件大小
    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 GB'
      
      return (bytes / Math.pow(1024, 3)).toFixed(2) + ' GB'
    }
    
    // 格式化文件大小为KB，添加千分位分隔
    const formatFileSizeInKB = (bytes) => {
      if (bytes === 0) return '0 KB'
      
      const kb = Math.round(bytes / 1024)
      // 添加千分位分隔符
      return kb.toLocaleString() + ' KB'
    }
    
    // 在setup函数适当位置添加ref
    const queryInput = ref(null);
    
    // 删除文件
    const deleteFile = async () => {
      if (!fileDetails.value || !fileDetails.value.fullPath) {
        ElMessage.error('文件路径不存在')
        return
      }
      
      try {
        // 保存当前所有选中的文件
        const currentSelectedFiles = [...store.selectedFiles]
        
        deleting.value = true
        
        // 调用后端API删除文件
        const response = await api.post('/files/delete_file', {
          file_path: fileDetails.value.fullPath
        })
        
        if (response.data && response.data.success) {
          // 标记文件为已删除，使用普通对象
          const filePath = fileDetails.value.fullPath
          deletedFiles.value[filePath] = true
          
          // 找到对应的文件对象
          const fileToUpdate = store.files.find(f => f.original_path === filePath)
          if (fileToUpdate) {
            // 设置删除标记 - 直接修改store中的文件对象
            fileToUpdate.deleted = true
            
            // 从selectedFiles中移除被删除的文件
            store.selectedFiles = currentSelectedFiles.filter(f => f.original_path !== filePath)
          }
          
          // 关闭对话框
          fileDetailsVisible.value = false
          
          // 等待表格更新
          await nextTick()
          
          // 清空表格所有选择
          tableRef.value.clearSelection()
          
          // 重新应用除被删除文件外的所有选中状态
          for (const selectedFile of store.selectedFiles) {
            const fileInTable = files.value.find(f => 
              f.original_path === selectedFile.original_path && f.isLeaf && !isFileLocked(f)
            )
            if (fileInTable) {
              tableRef.value.toggleRowSelection(fileInTable, true)
            }
          }
          
          // 显示成功消息
          ElMessage.success('文件已成功删除')
          addLog(`文件已删除: ${filePath}`)
        } else {
          ElMessage.error(response.data?.message || '删除文件失败')
          addLog(`删除文件失败: ${response.data?.message || '未知错误'}`)
        }
      } catch (error) {
        console.error('删除文件失败:', error)
        ElMessage.error('删除文件失败: ' + (error.response?.data?.detail || error.message))
        addLog(`删除文件失败: ${error.response?.data?.detail || error.message}`)
      } finally {
        deleting.value = false
      }
    }
    
    // 添加一个辅助函数检查文件是否已删除
    const isPathDeleted = (path) => {
      if (!path || !deletedFiles) return false
      return Object.prototype.hasOwnProperty.call(deletedFiles, path)
    }
    
    return {
      files,
      hasFiles,
      loading,
      scanning,
      identifying,
      renaming,
      progress,
      progressStatus,
      progressText,
      logs,
      scanFiles,
      identifyFiles,
      renameFiles,
      handleSelectionChange,
      toggleRow,
      formatFileName,
      tableRowClassName,
      tableRef,
      identifyDialogVisible,
      identifyForm,
      searching,
      showResults,
      searchResults,
      selectedMovieId,
      handleIdentify,
      searchTMDB,
      selectMovie,
      cancelSearch,
      isFileLocked,
      getBtnType,
      getBtnText,
      hasScanned,
      currentMovieInfo,
      queryInput,
      handleScanCommand,
      fileDetailsVisible,
      fileDetails,
      showFileDetails,
      formatFileSize,
      formatFileSizeInKB,
      deleting,
      deleteFile,
      deletedFiles,
      isPathDeleted
    }
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/theme.scss' as *;

.rename-view {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  h2 {
    color: $dark-text-primary;
    margin: 0;
  }
  
  .actions {
    display: flex;
    gap: 12px;
    align-items: center; /* 确保按钮垂直对齐 */
    
    .action-btn {
      min-width: 110px; /* 恢复按钮原来的宽度 */
      padding: 10px 16px;
      border-radius: $radius-md;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      transition: all 0.3s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      
      .el-icon {
        font-size: 16px;
      }
      
      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
      }
      
      &:active {
        transform: translateY(0);
      }
      
      &.is-disabled {
        opacity: 0.7;
        
        &:hover {
          transform: none;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
      }
    }
  }
}

.progress-container {
  margin-bottom: 20px;
  
  .progress-bar {
    margin-bottom: 10px;
  }
  
  .progress-text {
    color: $dark-text-primary;
    font-size: 0.875rem;
  }
}

.file-path {
  display: flex;
  align-items: center;
  gap: 10px;
  
  .el-icon {
    color: $primary-purple;
  }
  
  .library-name {
    color: $primary-purple;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 1px 6px;
    background-color: rgba($primary-purple, 0.1);
    border-radius: $radius-md;
    margin-left: -10px;
  }
  
  .directory-path {
    color: $dark-text-secondary;
  }
  
  .file-name {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
    display: block;
  }
}

.log-container {
  margin-top: 20px;
  background-color: rgba(#1e1e1e, 0.7);
  border-radius: 4px;
  border: 1px solid #363636;
  padding: 12px;
  
  h3 {
    margin-bottom: 12px;
    color: #e1e1e1;
    font-size: 16px;
    border-bottom: 1px solid #363636;
    padding-bottom: 8px;
  }
  
  .log-scrollbar {
    border-radius: 2px;
    background-color: rgba(#242424, 0.5);
  }
  
  .log-item {
    padding: 8px 12px;
    border-bottom: 1px solid rgba(#363636, 0.5);
    color: #e1e1e1;
    font-family: "Consolas", monospace;
    font-size: 13px;
    
    &:last-child {
      border-bottom: none;
    }
    
    &:hover {
      background-color: rgba(#2c2c2c, 0.5);
    }
    
    &.type-success {
      border-left: 3px solid #67c23a;
    }
    
    &.type-error {
      border-left: 3px solid #f56c6c;
    }
    
    &.type-warning {
      border-left: 3px solid #e6a23c;
    }
  }
}

.search-results {
  .movie-item {
    padding: 12px;
    border-radius: $radius-md;
    border: 1px solid $dark-border;
    background-color: rgba($dark-bg-secondary, 0.7);
    margin-bottom: 12px;
    display: flex;
    gap: 16px;
    cursor: pointer; /* 恢复鼠标指针样式 */
    transition: all 0.2s ease;
    min-height: 138px;
    
    &:hover {
      background-color: rgba($purple-700, 0.2);
      border-color: $purple-400;
      transform: translateY(-2px);
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }
    
    &:active {
      transform: translateY(0);
    }
    
    &.selected {
      background-color: rgba($purple-700, 0.3);
      border-color: $purple-500;
      transform: scale(1.01);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
      pointer-events: none; /* 恢复选中状态禁用指针事件 */
    }
    
    .movie-poster {
      flex-shrink: 0;
      width: 92px;
      height: 138px;
      overflow: hidden;
      border-radius: $radius-sm;
      background-color: $dark-bg-primary;
      border: 1px solid $dark-border;
      position: relative;
      
      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      
      .selected-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba($purple-700, 0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        
        .selecting-icon {
          font-size: 24px;
          color: white;
          animation: spin 1.2s linear infinite;
        }
      }
    }
    
    .movie-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 8px;
      
      .movie-title {
        color: $dark-text-primary;
        font-size: 18px;
        font-weight: 600;
      }
      
      .movie-original-title {
        color: $dark-text-secondary;
        font-size: 14px;
      }
      
      .movie-overview {
        color: $dark-text-secondary;
        font-size: 14px;
        margin-top: 4px;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }
  }
  
  .no-results {
    padding: 30px;
    text-align: center;
    color: $dark-text-secondary;
    font-style: italic;
  }
}

:deep(.tmdb-id-btn) {
  width: 90px;
  text-overflow: ellipsis;
  overflow: hidden;
  
  /* 调整warning类型按钮的样式 */
  &.el-button--warning {
    background-color: #C27232 !important;
    border-color: #A05A28 !important;
    color: $white !important;
    
    &:hover {
      background-color: #A05A28 !important;
      border-color: #834A20 !important;
    }
  }
  
  /* 调整info类型按钮为蓝色，用于一般可信的识别结果 */
  &.el-button--info {
    background-color: #409EFF !important; /* 使用Element Plus默认蓝色 */
    border-color: #337ECC !important;
    color: $white !important;
    
    &:hover {
      background-color: #337ECC !important;
      border-color: #2C6CB3 !important;
    }
    
    /* 对于已删除文件的info按钮保持灰色 */
    .deleted-file & {
      background-color: #909399 !important;
      border-color: #909399 !important;
      
      &:hover, &:active, &:focus {
        background-color: #909399 !important;
        border-color: #909399 !important;
      }
    }
  }
}

.locked-file {
  background-color: rgba($success, 0.1);
  td {
    opacity: 0.8;
  }
  
  :deep(.el-checkbox) {
    .el-checkbox__input.is-checked {
      .el-checkbox__inner {
        background-color: transparent;
        border-color: #dcdfe6;
        
        &:after {
          display: none;
        }
      }
    }
  }
}

.lock-tag {
  color: $success;
  font-weight: 600;
  margin-right: 4px;
  background-color: rgba($success, 0.1);
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 0.8rem;
}

.log-placeholder {
  margin-top: 20px;
  padding: 16px;
  background-color: rgba($dark-bg-secondary, 0.3);
  border-radius: $radius-md;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $dark-text-secondary;
  font-size: 14px;
  gap: 8px;
  border: 1px dashed rgba($dark-border, 0.5);
  
  .el-icon {
    color: $purple-400;
  }
}

/* 修改表格加载时的覆盖样式 */
:deep(.el-loading-mask) {
  background-color: rgba($dark-bg-secondary, 0.9) !important;
  
  .el-loading-spinner {
    .path {
      stroke: $purple-400 !important; 
    }
    
    .el-loading-text {
      color: $dark-text-primary !important;
    }
  }
}

/* 识别对话框样式 */
:deep(.identify-dialog) {
  .el-dialog__header {
    padding: 16px 24px;
    margin-right: 0;
    border-bottom: 1px solid $dark-border;
    
    .el-dialog__title {
      font-size: 18px;
      font-weight: 500;
    }
  }
  
  .el-dialog__body {
    padding: 24px;
    will-change: contents;
    backface-visibility: hidden;
    transform: translateZ(0);
  }
  
  .el-dialog__footer {
    border-top: 1px solid $dark-border;
    padding: 16px 24px;
  }
  
  /* 特别针对手工识别对话框内的输入框样式 */
  .identify-form {
    .el-form-item__label {
      color: $dark-text-primary;
      padding: 0 0 8px 0;
      font-weight: 500;
    }
    
    .el-form-item {
      margin-bottom: 16px;
    }
    
    /* 完全覆盖Element Plus的输入框样式 */
    .el-input {
      width: 100%;
      
      .el-input__wrapper {
        box-shadow: 0 0 0 1px $dark-border inset !important;
        background-color: rgba($dark-bg-secondary, 0.8) !important;
        border: none !important;
        border-radius: 4px !important;
        
        &:hover {
          box-shadow: 0 0 0 1px $purple-400 inset !important;
        }
        
        &.is-focus {
          box-shadow: 0 0 0 1px $purple-500 inset !important;
        }
      }
      
      .el-input__inner {
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        background-color: transparent !important;
        color: $dark-text-primary !important;
      }
    }
    
    /* 多行文本框样式 */
    .query-textarea {
      width: 100%;
      
      .el-textarea__inner {
        background-color: rgba($dark-bg-secondary, 0.8) !important;
        border: 1px solid $dark-border !important;
        border-radius: 4px !important;
        color: $dark-text-primary !important;
        padding: 10px !important;
        line-height: 1.5 !important;
        
        &:hover {
          border-color: $purple-400 !important;
        }
        
        &:focus {
          border-color: $purple-500 !important;
          box-shadow: 0 0 0 1px $purple-500 !important;
        }
      }
    }
  }
  
  .movie-item {
    backface-visibility: hidden;
  }
}

/* 添加图标旋转动画 */
@keyframes spin {
  0% { 
    transform: rotate(0deg); 
  }
  100% { 
    transform: rotate(360deg); 
  }
}

/* 修改对话框动画 */
:deep(.el-dialog) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* 定义弹出框和淡入淡出效果 */
:deep(.el-dialog__wrapper) {
  transition: opacity 0.3s ease !important;
}

:deep(.el-overlay) {
  transition: opacity 0.3s ease !important;
}

/* 文件详情对话框样式 */
:deep(.file-details-dialog) {
  .el-dialog__header {
    padding: 14px 20px;
    margin-right: 0;
    border-bottom: 1px solid $dark-border;
    
    .el-dialog__title {
      font-size: 16px;
      font-weight: 500;
    }
  }
  
  .el-dialog__body {
    padding: 20px;
  }
}

.file-details {
  .detail-item {
    margin-bottom: 12px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    .detail-label {
      font-weight: 500;
      margin-right: 6px;
      color: $dark-text-secondary;
    }
    
    .detail-value {
      word-break: break-all;
    }
  }
}

.file-details-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 150px;
  gap: 12px;
  
  .loading-icon {
    font-size: 24px;
    animation: spin 1.2s linear infinite;
    color: $purple-400;
  }
}

.current-movie-info {
  margin-bottom: 20px;
  
  .movie-item {
    padding: 12px;
    border-radius: $radius-md;
    border: 1px solid $dark-border;
    background-color: rgba($dark-bg-secondary, 0.7);
    margin-bottom: 12px;
    display: flex;
    gap: 16px;
    transition: all 0.2s ease;
    min-height: 138px; /* 确保最小高度一致 */
    
    &.selected {
      background-color: rgba($purple-700, 0.3);
      border-color: $purple-500;
      transform: scale(1.01);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    
    .movie-loading {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      width: 100%;
      color: $dark-text-secondary;
      gap: 12px;
      
      .loading-icon {
        font-size: 24px;
        animation: spin 1.2s linear infinite;
        color: $purple-400;
      }
    }

    .movie-placeholder {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      width: 100%;
      color: $dark-text-secondary;
      gap: 12px;
      
      .el-icon {
        font-size: 24px;
        color: $dark-text-secondary;
      }
    }
    
    .movie-poster {
      flex-shrink: 0;
      width: 92px;
      height: 138px;
      overflow: hidden;
      border-radius: $radius-sm;
      background-color: $dark-bg-primary;
      border: 1px solid $dark-border;
      position: relative;
      
      img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
    }
    
    .movie-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 8px;
      
      .movie-title {
        color: $dark-text-primary;
        font-size: 18px;
        font-weight: 600;
      }
      
      .movie-original-title {
        color: $dark-text-secondary;
        font-size: 14px;
      }
      
      .movie-overview {
        color: $dark-text-secondary;
        font-size: 14px;
        margin-top: 4px;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }
  }
}

/* 添加重命名成功文件的样式，并确保它始终显示锁定样式 */
:deep(.renamed-file) {
  background-color: rgba(103, 194, 58, 0.1) !important; // 浅绿色背景，使用!important确保优先级
  
  td {
    color: #67c23a !important; // 绿色文字，使用!important确保优先级
    font-weight: 500;
  }
  
  &:hover > td {
    background-color: rgba(103, 194, 58, 0.2) !important; // 悬停时的背景色
  }
  
  &::after {
    content: '✓ 已重命名';
    position: absolute;
    right: 20px;
    color: #67c23a;
    font-size: 12px;
  }
  
  /* 禁用选择功能 */
  :deep(.el-checkbox) {
    .el-checkbox__input {
      cursor: not-allowed;
      opacity: 0.5;
      
      .el-checkbox__inner {
        background-color: transparent !important;
        border-color: #dcdfe6 !important;
        
        &:after {
          display: none !important;
        }
      }
    }
  }
}

:deep(.locked-file) {
  background-color: rgba(230, 230, 230, 0.5);
  
  td {
    color: #909399;
    font-style: italic;
  }
  
  &:hover > td {
    background-color: rgba(230, 230, 230, 0.7) !important;
  }
}

:deep(.no-tmdb-id) {
  td {
    color: #e6a23c;
  }
}

/* 添加右上角评分和热度样式 */
.movie-ratings-corner {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  flex-direction: row; /* 改为水平排列 */
  gap: 6px;
  z-index: 2;
  
  .vote, .popularity {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    padding: 2px 6px;
    border-radius: 4px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
  }
  
  .vote {
    color: #F7B752;
    background-color: rgba(30, 30, 32, 0.8); /* 暗色半透明背景 */
    
    .el-icon {
      color: #F7B752;
    }
  }
  
  .popularity {
    color: #9C89FF;
    background-color: rgba(30, 30, 32, 0.8); /* 暗色半透明背景 */
    
    .el-icon {
      color: #9C89FF;
    }
  }
}

/* 调整电影卡片布局以支持右上角评分 */
.movie-item {
  position: relative;
  padding-right: 8px;
}

.movie-info {
  padding-right: 60px; /* 为评分留出空间 */
}

/* 特别调整对话框的拖动样式 */
:deep(.el-dialog) {
  cursor: default;
  
  .el-dialog__header {
    cursor: move;
  }
  
  /* 添加硬件加速，提高拖动性能 */
  will-change: transform;
  transform: translate3d(0, 0, 0);
  transition: none;
}

/* 提高对话框内容的渲染性能 */
:deep(.identify-dialog) {
  .el-dialog__body {
    will-change: contents;
    backface-visibility: hidden;
    transform: translateZ(0);
  }
  
  .movie-item {
    backface-visibility: hidden;
  }
}

/* 添加已删除文件的样式 */
:deep(.deleted-file) {
  background-color: rgba(245, 108, 108, 0.1); // 浅红色背景
  
  td {
    color: #f56c6c; // 红色文字
    text-decoration: line-through; // 添加删除线
    opacity: 0.7;
  }
  
  &:hover > td {
    background-color: rgba(245, 108, 108, 0.2) !important; // 悬停时的背景色
  }
  
  &::after {
    content: '已删除';
    position: absolute;
    right: 20px;
    color: #f56c6c;
    font-size: 12px;
  }
  
  .tmdb-id-btn {
    cursor: not-allowed;
    opacity: 0.7;
    
    &:hover, &:active, &:focus {
      background-color: #909399 !important;
      border-color: #909399 !important;
      color: #fff !important;
      transform: none !important;
      box-shadow: none !important;
    }
  }
}
</style> 