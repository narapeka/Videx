<template>
  <div class="transfer">
    <el-card>
      <div class="card-header">
        <h2>智能转存</h2>
      </div>
      <div class="card-content">
        <el-form :model="form" label-width="120px">
          <el-form-item label="源目录">
            <div class="path-selector">
              <el-input v-model="form.sourcePath" readonly size="small" />
              <el-button size="small" @click="openSourceDirectorySelector">
                <el-icon><Folder /></el-icon>
              </el-button>
            </div>
          </el-form-item>
          <el-form-item label="目标目录">
            <div class="path-selector">
              <el-input v-model="form.targetPath" readonly size="small" />
              <el-button size="small" @click="openTargetDirectorySelector">
                <el-icon><Folder /></el-icon>
              </el-button>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="startTransfer" :loading="transferring">
              开始转存
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Folder } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const form = ref({
  sourcePath: '',
  targetPath: ''
})

const transferring = ref(false)

const openSourceDirectorySelector = () => {
  // TODO: 实现源目录选择
}

const openTargetDirectorySelector = () => {
  // TODO: 实现目标目录选择
}

const startTransfer = async () => {
  if (!form.value.sourcePath || !form.value.targetPath) {
    ElMessage.warning('请选择源目录和目标目录')
    return
  }
  
  transferring.value = true
  try {
    // TODO: 实现转存逻辑
    await new Promise(resolve => setTimeout(resolve, 1000)) // 模拟API调用
    ElMessage.success('转存完成')
  } catch (error) {
    ElMessage.error('转存失败：' + error.message)
  } finally {
    transferring.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/theme.scss' as *;

.transfer {
  max-width: 800px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  color: $dark-text-primary;
  font-size: 20px;
}

.path-selector {
  display: flex;
  gap: 8px;
  align-items: center;
}

.path-selector .el-input {
  flex: 1;
}
</style> 