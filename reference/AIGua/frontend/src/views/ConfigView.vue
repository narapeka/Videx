<template>
  <div class="config-container">
    <div class="page-header">
      <h1>系统配置</h1>
      <el-button type="primary" @click="saveConfig" :icon="Check">保存配置</el-button>
    </div>

    <el-row>
      <!-- 通用设置卡片 -->
      <el-col :span="24">
        <el-card class="config-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Setting /></el-icon>
              <span>通用设置</span>
            </div>
          </template>
          <el-form :model="config" label-position="top" size="small">
            <el-form-item label="代理地址">
              <template #label>
                <div class="label-with-icon">
                  <span>代理地址</span>
                  <el-tooltip content="访问外部API的代理服务器" placement="top">
                    <el-icon class="help-icon"><InfoFilled /></el-icon>
                  </el-tooltip>
                </div>
              </template>
              <el-input v-model="config.proxy_url" placeholder="例如: 127.0.0.1:7890">
                <template #prefix>
                  <el-icon><Connection /></el-icon>
                </template>
              </el-input>
            </el-form-item>
            
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item>
                  <template #label>
                    <div class="label-with-icon">
                      <span>媒体文件扩展名</span>
                      <el-tooltip content="支持的媒体文件扩展名（用分号分隔，如：.mp4;.mkv）" placement="top">
                        <el-icon class="help-icon"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <el-input v-model="config.media_extension">
                    <template #prefix>
                      <el-icon><Film /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item>
                  <template #label>
                    <div class="label-with-icon">
                      <span>字幕文件扩展名</span>
                      <el-tooltip content="支持的字幕文件扩展名（用分号分隔，如：.srt;.ass）" placement="top">
                        <el-icon class="help-icon"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <el-input v-model="config.subtitle_extension">
                    <template #prefix>
                      <el-icon><Document /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>
      </el-col>

      <!-- Grok设置卡片 -->
      <el-col :span="24">
        <el-card class="config-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Key /></el-icon>
              <span>Grok 设置</span>
            </div>
          </template>
          <el-form :model="config" label-position="top" size="small">
            <el-form-item label="API Key">
              <el-input v-model="config.grok_api_key" type="password" show-password>
                <template #prefix>
                  <el-icon><Lock /></el-icon>
                </template>
              </el-input>
            </el-form-item>
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item>
                  <template #label>
                    <div class="label-with-icon">
                      <span>批处理大小</span>
                      <el-tooltip content="每批文件数量" placement="top">
                        <el-icon class="help-icon"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <el-input-number 
                    v-model="config.grok_batch_size" 
                    :min="1" 
                    :max="100" 
                    style="width: 100%" 
                    controls-position="right"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item>
                  <template #label>
                    <div class="label-with-icon">
                      <span>速率限制</span>
                      <el-tooltip content="每秒最大请求次数" placement="top">
                        <el-icon class="help-icon"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <el-input-number 
                    v-model="config.grok_rate_limit" 
                    :min="1" 
                    :max="100" 
                    style="width: 100%" 
                    controls-position="right"
                  />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>
      </el-col>

      <!-- TMDB设置卡片 -->
      <el-col :span="24">
        <el-card class="config-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Film /></el-icon>
              <span>TMDB 设置</span>
            </div>
          </template>
          <el-form :model="config" label-position="top" size="small">
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="API Key">
                  <el-input v-model="config.tmdb_api_key" type="password" show-password>
                    <template #prefix>
                      <el-icon><Lock /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item>
                  <template #label>
                    <div class="label-with-icon">
                      <span>速率限制</span>
                      <el-tooltip content="每秒最大请求次数" placement="top">
                        <el-icon class="help-icon"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <el-input-number 
                    v-model="config.tmdb_rate_limit" 
                    :min="1" 
                    :max="100" 
                    style="width: 100%" 
                    controls-position="right"
                  />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
        </el-card>
      </el-col>

      <!-- 媒体库配置卡片 -->
      <el-col :span="24">
        <el-card class="config-card media-lib-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><FolderOpened /></el-icon>
              <span>媒体库配置</span>
            </div>
          </template>
          <div class="media-libraries">
            <el-table :data="config.media_libraries" style="width: 100%" border size="small">
              <el-table-column label="路径" min-width="300">
                <template #default="{ row }">
                  <div class="path-selector">
                    <el-tooltip
                      :content="row.path"
                      placement="top"
                      :show-after="500"
                      :disabled="!row.path"
                    >
                      <el-input v-model="row.path" readonly size="small" />
                    </el-tooltip>
                    <el-button size="small" @click="openDirectorySelector(config.media_libraries.indexOf(row))">
                      <el-icon><Folder /></el-icon>
                    </el-button>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="类型" width="140">
                <template #default="{ row }">
                  <el-select v-model="row.type" style="width: 100%" size="small">
                    <el-option label="电影" value="movie" />
                    <el-option label="电视剧" value="tv" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="70" fixed="right">
                <template #default="{ $index }">
                  <el-button 
                    type="primary"
                    circle
                    size="small"
                    class="delete-btn"
                    @click="removeLibrary($index)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="table-footer">
              <el-button type="primary" size="small" @click="addLibrary">
                <el-icon><Plus /></el-icon>添加媒体库
              </el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 目录选择对话框 -->
    <el-dialog
      v-model="directoryDialogVisible"
      title="选择目录"
      width="60%"
      :close-on-click-modal="false"
    >
      <div class="directory-selector">
        <!-- 面包屑导航 -->
        <div class="breadcrumb">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '' }" @click="handleBreadcrumbClick(-1)">
              根目录
            </el-breadcrumb-item>
            <el-breadcrumb-item
              v-for="(item, index) in currentPath"
              :key="index"
              :to="{ path: '' }"
              @click="handleBreadcrumbClick(index)"
            >
              {{ item }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <!-- 目录树 -->
        <el-tree
          ref="directoryTree"
          :data="directoryList"
          :props="{
            label: 'name',
            children: 'children',
            hasChildren: 'hasChildren'
          }"
          node-key="path"
          highlight-current
          :expand-on-click-node="false"
          :lazy="true"
          :load="loadChildren"
          @node-click="selectDirectory"
          class="directory-tree"
        >
          <template #default="{ data }">
            <span class="custom-tree-node">
              <el-icon><Folder /></el-icon>
              <span>{{ data.name || data.path }}</span>
            </span>
          </template>
        </el-tree>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="directoryDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmDirectory">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Folder, 
  FolderOpened, 
  Plus, 
  Delete, 
  Setting, 
  Key, 
  Lock, 
  Film, 
  Check,
  Connection,
  Document,
  QuestionFilled,
  InfoFilled
} from '@element-plus/icons-vue'
import { useStore } from '@/store'

const store = useStore()
const config = ref({
  grok_api_key: '',
  tmdb_api_key: '',
  proxy_url: '',
  grok_batch_size: 20,
  grok_rate_limit: 1,
  tmdb_rate_limit: 50,
  media_libraries: [],
  media_extension: '',
  subtitle_extension: ''
})

const directoryDialogVisible = ref(false)
const currentPath = ref([])
const directoryList = ref([])
const selectedPath = ref('')
const currentEditingIndex = ref(-1)

// 添加媒体库
const addLibrary = () => {
  config.value.media_libraries.push({
    path: '',
    type: 'movie'
  })
  currentEditingIndex.value = config.value.media_libraries.length - 1
  // 等待 DOM 更新后再打开目录选择器
  nextTick(() => {
    openDirectorySelector(currentEditingIndex.value)
  })
}

// 检查路径是否重复
const isPathDuplicate = (path, excludeIndex = -1) => {
  return config.value.media_libraries.some((library, index) => {
    if (index === excludeIndex) return false
    return library.path === path
  })
}

// 删除媒体库
const removeLibrary = (index) => {
  config.value.media_libraries.splice(index, 1)
}

// 打开目录选择器
const openDirectorySelector = async (index) => {
  console.log('Opening directory selector for index:', index)
  currentEditingIndex.value = index
  currentPath.value = []
  directoryList.value = []
  selectedPath.value = ''
  directoryDialogVisible.value = true
  // 等待对话框显示后再加载目录
  await nextTick()
  console.log('Loading initial directories...')
  await loadDirectories()
}

// 加载目录列表
const loadDirectories = async () => {
  try {
    console.log('Loading directories for path:', currentPath.value.join('/'))
    const directories = await store.getDirectories(currentPath.value.join('/'))
    console.log('Loaded directories:', directories)
    
    if (!Array.isArray(directories)) {
      console.error('Invalid response format:', directories)
      throw new Error('目录列表格式错误')
    }
    
    directoryList.value = directories.map(dir => ({
      name: dir.name,
      path: dir.path,
      hasChildren: true
    }))
    console.log('Processed directory list:', directoryList.value)
  } catch (error) {
    console.error('加载目录失败:', error)
    ElMessage.error('加载目录失败: ' + error.message)
    directoryList.value = []
  }
}

// 加载子目录
const loadChildren = async (node, resolve) => {
  try {
    console.log('Loading children for node:', node)
    const path = node.data.path
    const directories = await store.getDirectories(path)
    console.log('Children response:', directories)
    
    if (!Array.isArray(directories)) {
      console.error('Invalid children response:', directories)
      resolve([])
      return
    }
    
    // 转换子目录数据
    const children = directories.map(dir => ({
      name: dir.name,
      path: dir.path,
      hasChildren: true
    }))
    
    console.log('Resolving children:', children)
    resolve(children)
  } catch (error) {
    console.error('加载子目录失败:', error)
    ElMessage.error('加载子目录失败')
    resolve([])
  }
}

// 选择目录
const selectDirectory = async (data) => {
  console.log('Selected directory:', data)
  if (!data || !data.path) {
    console.error('Invalid directory item:', data)
    return
  }
  selectedPath.value = data.path
  // 更新当前路径
  currentPath.value = data.path.split(/[/\\]/).filter(Boolean)
  console.log('Updated currentPath:', currentPath.value)
}

// 确认选择目录
const confirmDirectory = () => {
  if (!selectedPath.value) {
    ElMessage.warning('请先选择一个目录')
    return
  }
  
  if (currentEditingIndex.value >= 0) {
    // 检查路径是否重复
    if (isPathDuplicate(selectedPath.value, currentEditingIndex.value)) {
      ElMessage.error('该路径已存在，请选择其他路径')
      return
    }
    config.value.media_libraries[currentEditingIndex.value].path = selectedPath.value
  }
  
  directoryDialogVisible.value = false
}

// 保存配置
const saveConfig = async () => {
  try {
    console.log('Saving config:', config.value)
    // 验证媒体库配置
    for (const library of config.value.media_libraries) {
      if (!library.path) {
        ElMessage.error('请选择媒体库路径')
        return
      }
      if (!library.type) {
        ElMessage.error('请选择媒体库类型（电影/电视剧）')
        return
      }
    }

    // 检查路径重复
    for (let i = 0; i < config.value.media_libraries.length; i++) {
      if (isPathDuplicate(config.value.media_libraries[i].path, i)) {
        ElMessage.error(`路径 "${config.value.media_libraries[i].path}" 重复，请修改`)
        return
      }
    }

    // 验证扩展名配置
    if (!config.value.media_extension) {
      ElMessage.warning('媒体文件扩展名为空，将使用默认值')
      config.value.media_extension = '.mp4;.iso;.mkv;.mov'
    }
    
    if (!config.value.subtitle_extension) {
      ElMessage.warning('字幕文件扩展名为空，将使用默认值')
      config.value.subtitle_extension = '.srt;.ass;.ssa'
    }

    // 确保所有必要的字段都存在
    const configToSave = {
      ...config.value,
      media_libraries: config.value.media_libraries.map(library => ({
        path: library.path,
        type: library.type
      })),
      media_extension: config.value.media_extension,
      subtitle_extension: config.value.subtitle_extension
    }

    console.log('Sending config to backend:', configToSave)
    const response = await store.updateConfig(configToSave)
    console.log('Backend response:', response)
    
    // 强制刷新store中的设置，确保立即生效
    await store.loadConfig()
    
    ElMessage.success('配置保存成功')
  } catch (error) {
    console.error('保存配置失败:', error)
    if (error.response) {
      console.error('Error response:', error.response.data)
      ElMessage.error(`保存配置失败: ${error.response.data.detail || error.message}`)
    } else {
      ElMessage.error('保存配置失败: ' + error.message)
    }
  }
}

// 加载配置
const loadConfig = async () => {
  try {
    const config_data = await store.loadConfig()
    console.log('从服务器加载的配置:', config_data)
    
    // 将配置数据合并到本地配置对象
    config.value = {
      grok_api_key: config_data.grok_api_key || '',
      tmdb_api_key: config_data.tmdb_api_key || '',
      proxy_url: config_data.proxy_url || '',
      grok_batch_size: config_data.grok_batch_size || 20,
      grok_rate_limit: config_data.grok_rate_limit || 1,
      tmdb_rate_limit: config_data.tmdb_rate_limit || 50,
      media_libraries: Array.isArray(config_data.media_libraries) ? config_data.media_libraries : [],
      media_extension: config_data.media_extension || '.mp4;.iso;.mkv;.mov',
      subtitle_extension: config_data.subtitle_extension || '.srt;.ass;.ssa'
    }
  } catch (error) {
    console.error('加载配置失败:', error)
    ElMessage.error('加载配置失败: ' + error.message)
  }
}

// 处理面包屑点击
const handleBreadcrumbClick = async (index) => {
  console.log('Breadcrumb clicked:', index)
  if (index === -1) {
    currentPath.value = []
  } else {
    currentPath.value = currentPath.value.slice(0, index + 1)
  }
  console.log('Updated currentPath:', currentPath.value)
  await loadDirectories()
}

onMounted(() => {
  loadConfig()
})
</script>

<style lang="scss" scoped>
@use '@/styles/theme.scss' as *;

.config-container {
  padding: 10px;
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  
  h1 {
    margin: 0;
    font-size: 20px;
    color: $dark-text-primary;
    font-weight: 500;
  }
  
  .el-button {
    padding: 10px 20px;
    font-size: 14px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    transition: all 0.3s ease;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
  }
}

.config-card {
  margin-bottom: 10px;
  border-radius: 6px;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
}

.media-lib-card {
  margin-bottom: 10px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  color: $dark-text-primary;
  
  .el-icon {
    color: $purple-500;
    font-size: 16px;
  }
  
  span {
    font-weight: 500;
    font-size: 14px;
  }
}

.media-libraries {
  width: 100%;
}

.path-selector {
  display: flex;
  gap: 4px;
  align-items: center;
}

.path-selector .el-input {
  flex: 1;
}

.table-footer {
  margin-top: 8px;
  display: flex;
  justify-content: flex-start;
  padding: 0 2px;
}

.setting-description {
  color: $dark-text-secondary;
  font-size: 0.75em;
  margin-top: 2px;
}

.directory-selector {
  height: 400px;
  display: flex;
  flex-direction: column;
}

.breadcrumb {
  margin-bottom: 16px;
  padding: 8px;
  background-color: $dark-bg-secondary;
  border-radius: 4px;
}

.directory-tree {
  flex: 1;
  overflow: auto;
  border: 1px solid $dark-border;
  border-radius: 4px;
  padding: 8px;
  background-color: $dark-bg-secondary;
  color: $dark-text-primary;
}

.custom-tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  color: $dark-text-primary;
  
  .el-icon {
    color: $purple-400;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

// 修复el-input-number组件样式
:deep(.el-input-number) {
  width: 100%;
  
  .el-input-number__decrease,
  .el-input-number__increase {
    background-color: $dark-bg-secondary;
    color: $dark-text-primary;
    border-color: $dark-border;
    
    &:hover {
      color: $purple-400;
    }
    
    .el-icon {
      color: inherit;
    }
  }
  
  &.is-controls-right {
    .el-input-number__decrease, 
    .el-input-number__increase {
      background-color: $dark-bg-secondary;
      border-color: $dark-border;
      line-height: 14px;
      
      &:hover {
        color: $purple-400;
      }
    }
    
    .el-input__wrapper {
      padding-right: 30px;
    }
  }
}

// 让表单项之间的间距更合理
:deep(.el-form-item) {
  margin-bottom: 8px;
  
  .el-form-item__label {
    padding-bottom: 4px;
    line-height: 1.2;
    font-size: 13px;
  }
  
  .el-form-item__content {
    line-height: 1.2;
  }
}

// 确保图标颜色正确
:deep(.el-button .el-icon) {
  color: inherit;
}

// 防止空白卡片占用过多空间
:deep(.el-form) {
  width: 100%;
  max-width: 100%;
  margin: 0;
}

// 为卡片内容添加适当的内边距
:deep(.el-card__body) {
  padding: 8px 12px;
  flex: 1;
}

// 确保卡片标题有足够的内边距
:deep(.el-card__header) {
  padding: 6px 12px;
}

// 调整输入框高度
:deep(.el-input__inner) {
  height: 28px;
  line-height: 28px;
}

:deep(.el-input__wrapper) {
  padding: 0 8px;
}

// 调整表单项间距和标签
:deep(.el-form-item--small .el-form-item__label) {
  margin-bottom: 2px;
}

:deep(.el-select) {
  width: 100%;
}

:deep(.el-dialog__body) {
  padding: 12px;
}

:deep(.el-table) {
  --el-table-header-padding: 6px;
  --el-table-cell-padding: 4px;
}

:deep(.el-button.el-button--small) {
  padding: 5px 11px;
}

.label-with-icon {
  display: flex;
  align-items: center;
  gap: 4px;
  
  .help-icon {
    font-size: 14px !important;
    color: #8a7cc2 !important;
    cursor: pointer;
    transition: color 0.2s;
    
    &:hover {
      color: #a992ff !important;
    }
  }
}

// 添加深度选择器确保样式应用到Element Plus组件内部
:deep(.help-icon svg) {
  color: #8a7cc2 !important;
  fill: #8a7cc2 !important;
}

// 添加删除按钮自定义样式
.delete-btn {
  --el-button-bg-color: transparent !important;
  --el-button-border-color: $dark-border !important;
  --el-button-hover-bg-color: rgba($purple-900, 0.5) !important;
  --el-button-hover-border-color: $purple-500 !important;
  --el-button-hover-text-color: $purple-300 !important;
  --el-button-active-bg-color: rgba($purple-800, 0.7) !important;
  
  .el-icon {
    color: $dark-text-secondary !important;
  }
  
  &:hover .el-icon {
    color: $purple-300 !important;
  }
}
</style> 