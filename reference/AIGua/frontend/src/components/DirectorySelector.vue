<template>
  <div class="directory-selector">
    <el-tree
      ref="treeRef"
      :data="treeData"
      :props="defaultProps"
      node-key="path"
      :load="loadNode"
      lazy
      :expand-on-click-node="false"
      @node-click="handleNodeClick"
    >
      <template #default="{ node }">
        <span class="custom-tree-node">
          <span>{{ node.label }}</span>
        </span>
      </template>
    </el-tree>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { API_ENDPOINTS, API_CONFIG } from '../config/api'

export default {
  name: 'DirectorySelector',
  props: {
    initialPath: {
      type: String,
      default: ''
    }
  },
  emits: ['select'],
  setup(props, { emit }) {
    const treeRef = ref(null)
    const treeData = ref([])
    const defaultProps = {
      children: 'children',
      label: 'name',
      isLeaf: 'isLeaf'
    }

    const loadNode = async (node, resolve) => {
      if (node.level === 0) {
        // 加载根目录
        try {
          const response = await axios.get(API_ENDPOINTS.files.directories, API_CONFIG)
          const data = response.data.directories.map(dir => ({
            name: dir.name,
            path: dir.path,
            isLeaf: false,
            children: []
          }))
          resolve(data)
        } catch (error) {
          ElMessage.error('加载目录失败：' + error.message)
          resolve([])
        }
      } else {
        // 加载子目录
        try {
          const response = await axios.get(API_ENDPOINTS.files.directories, {
            ...API_CONFIG,
            params: { path: node.data.path }
          })
          const data = response.data.directories.map(dir => ({
            name: dir.name,
            path: dir.path,
            isLeaf: false,
            children: []
          }))
          resolve(data)
        } catch (error) {
          ElMessage.error('加载子目录失败：' + error.message)
          resolve([])
        }
      }
    }

    const handleNodeClick = (data) => {
      emit('select', data.path)
    }

    onMounted(() => {
      if (props.initialPath) {
        // 如果有初始路径，展开到该路径
        const pathParts = props.initialPath.split('/')
        let currentPath = ''
        pathParts.forEach(part => {
          if (part) {
            currentPath += '/' + part
            treeRef.value?.expand(currentPath)
          }
        })
      }
    })

    return {
      treeRef,
      treeData,
      defaultProps,
      loadNode,
      handleNodeClick
    }
  }
}
</script>

<style scoped>
.directory-selector {
  padding: 10px;
  max-height: 400px;
  overflow-y: auto;
}

.custom-tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  font-size: 14px;
  padding-right: 8px;
}
</style> 