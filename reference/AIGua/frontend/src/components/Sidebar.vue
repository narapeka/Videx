<template>
  <div class="sidebar">
    <div class="logo">
      <div class="logo-text">
        <span class="ai-text">AI</span><span class="gua-text">Gua</span>
      </div>
    </div>
    <el-menu
      :default-active="activeMenu"
      class="sidebar-menu"
      :router="true"
      background-color="#1A1625"
      text-color="#CBD5E0"
      active-text-color="#A78BFA"
    >
      <el-menu-item index="/">
        <el-icon><HomeFilled /></el-icon>
        <span>首页</span>
      </el-menu-item>
      <el-menu-item index="/rename">
        <el-icon><Edit /></el-icon>
        <span>智能重命名</span>
      </el-menu-item>
      <el-menu-item index="/transfer">
        <el-icon><FolderOpened /></el-icon>
        <span>智能转存</span>
      </el-menu-item>
      <el-menu-item index="/config">
        <el-icon><Setting /></el-icon>
        <span>系统配置</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { HomeFilled, Setting, Edit, FolderOpened } from '@element-plus/icons-vue'

const route = useRoute()
const activeMenu = computed(() => {
  return route.path
})
</script>

<style lang="scss" scoped>
@use "sass:color";
@use '@/styles/theme.scss' as *;

.sidebar {
  width: 240px;
  height: 100vh;
  position: fixed;
  left: 0;
  background-color: color.adjust($dark-bg-primary, $lightness: -3%);
  z-index: 10;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}

.logo {
  height: 70px;
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: $dark-bg-primary;
  border-bottom: 1px solid rgba($dark-border, 0.5);
}

.logo-text {
  display: flex;
  align-items: center;
  justify-content: center;
  
  .ai-text {
    font-size: 28px;
    font-weight: 800;
    color: $purple-400;
    letter-spacing: -1px;
    font-style: italic;
  }
  
  .gua-text {
    font-size: 26px;
    font-weight: 400;
    color: $purple-300;
    letter-spacing: 0.5px;
  }
}

.sidebar-menu {
  border-right: none;
  flex: 1;
  background-color: $dark-bg-primary !important;
}

:deep(.el-menu-item) {
  height: 50px;
  line-height: 50px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: $dark-text-secondary !important;
  transition: $transition-base;
  
  &:hover {
    background-color: $dark-bg-secondary !important;
    color: $purple-300 !important;
  }
  
  &.is-active {
    background-color: $purple-900 !important;
    color: $purple-300 !important;
    font-weight: 500;
  }
}

:deep(.el-menu-item .el-icon) {
  font-size: 18px;
  margin-right: 8px;
  transition: $transition-base;
  color: $purple-400;
}

:deep(.el-menu-item:hover .el-icon) {
  transform: scale(1.1);
  color: $purple-300;
}

:deep(.el-menu-item.is-active .el-icon) {
  color: $purple-400;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    
    &.is-open {
      transform: translateX(0);
    }
  }
}
</style> 