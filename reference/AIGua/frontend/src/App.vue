<template>
  <div class="app-container">
    <Sidebar />
    <div class="main-content">
      <router-view></router-view>
    </div>
  </div>
</template>

<script setup>
import Sidebar from '@/components/Sidebar.vue'
</script>

<style lang="scss">
@use "sass:color";
@use '@/styles/theme.scss' as *;

/* Element Plus 原生CSS变量覆盖 */
:root {
  --el-table-border-color: #{$dark-border} !important;
  --el-table-border: 1px solid #{$dark-border} !important;
  --el-table-header-border-color: #{$dark-border} !important;
  --el-table-header-bg-color: #{$dark-bg-secondary} !important;
  --el-table-row-hover-bg-color: #{$dark-bg-table-hover} !important;
  --el-table-bg-color: #{$dark-bg-table} !important;
  --el-table-tr-bg-color: #{$dark-bg-table} !important;
  --el-table-expanded-cell-bg-color: #{$dark-bg-table} !important;
  --el-table-fixed-box-shadow: 0 0 10px rgba(0, 0, 0, 0.3) !important;

  /* 下拉框相关变量 */
  --el-select-dropdown-bg-color: #{$dark-bg-secondary} !important;
  --el-select-dropdown-border-color: #{$dark-border} !important;
  --el-select-dropdown-item-hover-color: #{$dark-bg-table-hover} !important;
  --el-select-input-focus-border-color: #{$purple-400} !important;
  --el-select-dropdown-item-color: #{$dark-text-primary} !important;

  /* 弹出框相关变量 */
  --el-popover-bg-color: #{$dark-bg-secondary} !important;
  --el-popover-border-color: #{$dark-border} !important;
  --el-popper-border-color: #{$dark-border} !important;
  
  /* 图标颜色变量 */
  --el-icon-color: #{$dark-text-primary} !important;
  --el-color-primary: #{$purple-500} !important;

  /* 下拉框和更多控件变量 */
  --el-fill-color-blank: #{$dark-bg-table} !important;
  --el-bg-color: #{$dark-bg-table} !important;
  --el-bg-color-overlay: #{$dark-bg-secondary} !important;
  --el-border-color: #{$dark-border} !important;
  --el-border-color-light: #{$dark-border} !important;
  --el-text-color-primary: #{$dark-text-primary} !important;
  --el-text-color-regular: #{$dark-text-primary} !important;
  --el-text-color-secondary: #{$dark-text-secondary} !important;
}

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  overflow-x: hidden;
  /* 防止不必要的竖向滚动条 */
  overflow-y: auto;
}

#app {
  height: 100%;
  overflow-x: hidden;
  /* 防止不必要的竖向滚动条 */
  overflow-y: auto;
}

.app-container {
  display: flex;
  height: 100%;
  overflow-x: hidden;
  /* 防止不必要的竖向滚动条 */
  overflow-y: auto;
  position: relative;
}

.main-content {
  flex: 1;
  margin-left: 240px;
  padding: $spacing-xl;
  background-color: $bg-primary;
  min-height: 100vh;
  overflow-x: hidden;
  /* 防止不必要的竖向滚动条 */
  overflow-y: auto;
  box-sizing: border-box;
}

/* Element Plus 主题覆盖 */
.el-card {
  @include card-style;
}

.el-card__header {
  padding: $spacing-md $spacing-lg;
  border-bottom: 1px solid $dark-border;
  background-color: $dark-bg-secondary;
  border-radius: $radius-lg $radius-lg 0 0;
  color: $dark-text-primary;
}

.el-form-item__label {
  font-weight: 500;
  color: $dark-text-primary !important;
}

.el-button {
  border-radius: $radius-md;
  
  &.el-button--primary {
    background-color: $purple-600;
    border-color: $purple-600;
    
    &:hover {
      background-color: $purple-700;
      border-color: $purple-700;
    }
  }
  
  &.el-button--success {
    background-color: $success;
    border-color: $success;
    
    &:hover {
      background-color: color.adjust($success, $lightness: -10%);
      border-color: color.adjust($success, $lightness: -10%);
    }
  }
  
  &.el-button--warning {
    background-color: $warning;
    border-color: $warning;
    
    &:hover {
      background-color: color.adjust($warning, $lightness: -10%);
      border-color: color.adjust($warning, $lightness: -10%);
    }
  }
  
  &.el-button--danger {
    background-color: $error;
    border-color: $error;
    
    &:hover {
      background-color: color.adjust($error, $lightness: -10%);
      border-color: color.adjust($error, $lightness: -10%);
    }
  }
}

.el-input__wrapper {
  border-radius: $radius-md;
  box-shadow: none !important;
  border: 1px solid $dark-border !important;
  background-color: rgba($dark-bg-secondary, 0.8) !important;
  
  &:hover {
    border-color: $purple-400 !important;
  }
  
  &.is-focus {
    border-color: $purple-500 !important;
    box-shadow: 0 0 0 2px rgba($purple-500, 0.2) !important;
  }
}

.el-input__inner {
  color: $dark-text-primary !important;
  background-color: transparent !important;
}

.el-select {
  width: 100%;
}

/* 表格样式 */
.el-table {
  background-color: $dark-bg-table !important;
  border-radius: $radius-lg;
  overflow: hidden;
  border: 1px solid $dark-border !important;
  
  /* 隐藏所有滚动条 */
  &, &:hover, &:focus {
    overflow-x: hidden !important;
    overflow-y: hidden !important;
  }
  
  .el-table__body-wrapper,
  .el-table__header-wrapper,
  .el-table__footer-wrapper {
    overflow-x: hidden !important;
    overflow-y: hidden !important;
    scrollbar-width: none !important;
    -ms-overflow-style: none !important;
    max-width: 100% !important;
    
    &::-webkit-scrollbar {
      width: 0 !important;
      height: 0 !important;
      display: none !important;
      background: transparent !important;
    }
  }
  
  .el-scrollbar,
  .el-scrollbar__wrap,
  .el-scrollbar__view {
    overflow-x: hidden !important;
    overflow-y: hidden !important;
  }
  
  .el-scrollbar__bar.is-horizontal {
    display: none !important;
    height: 0 !important;
    opacity: 0 !important;
    visibility: hidden !important;
  }
  
  .el-table__inner-wrapper {
    border: 1px solid $dark-border !important;
  }
  
  &.el-table--border, 
  &.el-table--group {
    border: 1px solid $dark-border !important;
    border-top: 1px solid $dark-border !important;
    border-bottom: 1px solid $dark-border !important;
    border-left: 1px solid $dark-border !important;
    border-right: 1px solid $dark-border !important;
    
    &::after, 
    &::before {
      background-color: $dark-border !important;
    }
  }
  
  &::before,
  &::after {
    background-color: $dark-border !important;
  }
  
  .el-table__border-left-patch {
    background-color: $dark-bg-secondary !important;
    border-bottom: 1px solid $dark-border !important;
  }
  
  .el-table__header-wrapper {
    background-color: $dark-bg-secondary !important;
    border-bottom: 1px solid $dark-border !important;
  }
  
  .el-table__footer-wrapper {
    background-color: $dark-bg-secondary !important;
    border-top: 1px solid $dark-border !important;
  }
  
  .el-table__fixed::before,
  .el-table__fixed-right::before {
    background-color: $dark-border !important;
  }
  
  .el-table__fixed {
    border-right: 1px solid $dark-border !important;
  }
  
  .el-table__fixed-right {
    border-left: 1px solid $dark-border !important;
  }
  
  .el-table__header {
    background-color: $dark-bg-secondary !important;
  }
  
  th.el-table__cell {
    background-color: $dark-bg-secondary !important;
    color: $dark-text-primary !important;
    font-weight: 600;
    border-bottom: 1px solid $dark-border !important;
  }
  
  .el-table__body-wrapper {
    background-color: $dark-bg-table !important;
  }
  
  td.el-table__cell {
    color: $dark-text-primary !important;
    border-bottom: 1px solid $dark-border !important;
    background-color: $dark-bg-table !important;
  }
  
  tr.el-table__row {
    background-color: $dark-bg-table !important;
  }
  
  tr:hover > td.el-table__cell {
    background-color: $dark-bg-table-hover !important;
  }
  
  .el-table__empty-block {
    min-height: 80px;
    background-color: $dark-bg-table !important;
  }
  
  .el-table__empty-text {
    color: $dark-text-secondary !important;
  }
  
  /* 内嵌表单元素样式 */
  .el-input__wrapper {
    padding: 0 8px;
    box-shadow: none !important;
    background-color: rgba($dark-bg-secondary, 0.8) !important;
    border: 1px solid $dark-border !important;
  }
  
  .el-input__inner {
    color: $dark-text-primary !important;
    background-color: transparent !important;
  }
  
  .el-select .el-input__wrapper {
    box-shadow: none !important;
  }

  /* 全局按钮图标悬停样式修复 */
  .path-selector {
    .el-button, 
    .el-button:hover, 
    .el-button:focus, 
    .el-button:active, 
    .el-button--default,
    .el-button--default:hover,
    .el-button--default:focus, 
    .el-button--default:active {
      .el-icon {
        color: $purple-400 !important;
        fill: $purple-400 !important;
        
        svg {
          color: $purple-400 !important;
          fill: $purple-400 !important;
        }
      }
    }
  }

  /* 修复表格中按钮图标变白问题 */
  .el-button--default {
    &.el-button--small {
      &:hover, &:active, &:focus {
        .el-icon {
          color: $purple-400 !important;
          
          svg {
            fill: $purple-400 !important;
            color: $purple-400 !important;
          }
        }
      }
    }
  }
}

/* 对话框样式 */
.el-dialog {
  border-radius: $radius-lg;
  overflow: hidden;
  background-color: $dark-bg-card !important;
  
  .el-dialog__header {
    background-color: $dark-bg-secondary;
    margin: 0;
    padding: $spacing-md $spacing-lg;
    border-bottom: 1px solid $dark-border;
  }
  
  .el-dialog__title {
    color: $dark-text-primary !important;
  }
  
  .el-dialog__body {
    background-color: $dark-bg-card;
    padding: $spacing-lg;
    color: $dark-text-primary;
  }
  
  .el-dialog__footer {
    background-color: $dark-bg-secondary;
    padding: $spacing-md $spacing-lg;
    border-top: 1px solid $dark-border;
  }
  
  .el-dialog__headerbtn .el-dialog__close {
    color: $dark-text-secondary !important;
  }
}

/* 进度条样式 */
.el-progress-bar__outer {
  background-color: rgba($dark-bg-secondary, 0.5) !important;
  border-radius: $radius-full;
}

.el-progress-bar__inner {
  background-color: $purple-600 !important;
  border-radius: $radius-full;
}

/* 标签页样式 */
.el-tabs__nav-wrap::after {
  background-color: $dark-border !important;
}

.el-tabs__item {
  color: $dark-text-secondary !important;
  
  &.is-active {
    color: $purple-400 !important;
  }
  
  &:hover {
    color: $purple-300 !important;
  }
}

.el-tabs__active-bar {
  background-color: $purple-600 !important;
}

/* 开关样式 */
.el-switch {
  &.is-checked {
    .el-switch__core {
      background-color: $purple-600 !important;
      border-color: $purple-600 !important;
    }
  }
}

/* 复选框样式 */
.el-checkbox {
  .el-checkbox__input {
    &.is-checked {
      .el-checkbox__inner {
        background-color: $purple-600 !important;
        border-color: $purple-600 !important;
      }
    }
  }
  
  .el-checkbox__label {
    color: $dark-text-primary !important;
  }
}

/* 单选框样式 */
.el-radio {
  .el-radio__input {
    &.is-checked {
      .el-radio__inner {
        background-color: $purple-600 !important;
        border-color: $purple-600 !important;
      }
    }
  }
  
  .el-radio__label {
    color: $dark-text-primary !important;
  }
}

/* 动画效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .main-content {
    margin-left: 0;
    padding: $spacing-md;
    width: 100%;
    box-sizing: border-box;
  }
  
  .el-dialog {
    width: 90% !important;
    margin: 0 auto;
  }
  
  .el-table {
    width: 100%;
    overflow-x: auto;
  }
}

.app-container {
  display: flex;
  height: 100%;
  overflow-x: hidden;
}

/* 下拉框和选择器增强样式 */
.el-select-dropdown {
  background-color: $dark-bg-secondary !important;
  border: 1px solid $dark-border !important;
  
  .el-select-dropdown__wrap {
    background-color: $dark-bg-secondary !important;
  }
  
  .el-scrollbar__view {
    background-color: $dark-bg-secondary !important;
  }
  
  .el-select-dropdown__item {
    color: $dark-text-primary !important;
    background-color: $dark-bg-secondary !important;
    
    &.selected,
    &.is-selected,
    &.hover {
      background-color: rgba($purple-700, 0.3) !important;
      color: $purple-400 !important;
    }
    
    &:hover {
      background-color: $dark-bg-table-hover !important;
    }
    
    &:not(.selected):not(.is-selected):not(:hover) {
      background-color: $dark-bg-secondary !important;
    }
  }
}

.el-input__wrapper {
  background-color: $dark-bg-secondary !important;
}

.el-input__inner {
  background-color: $dark-bg-secondary !important;
  color: $dark-text-primary !important;
}

/* 图标颜色修复 */
.el-icon {
  color: $dark-text-primary !important;
  
  svg {
    fill: currentColor !important;
  }
}

.el-select__caret,
.el-input__icon {
  color: $dark-text-primary !important;
}

/* 全局标题和文本颜色 */
h1, h2, h3, h4, h5, h6 {
  color: $dark-text-primary !important;
}

p, span, div {
  color: $dark-text-primary;
}

.text-secondary {
  color: $dark-text-secondary !important;
}

.log-item, .log-content {
  color: $dark-text-primary !important;
}

/* 日志区域样式 */
.log-container {
  background-color: $dark-bg-secondary;
  border: 1px solid $dark-border;
  border-radius: $radius-md;
  
  h3 {
    color: $dark-text-primary !important;
  }
  
  .log-item {
    color: $dark-text-primary !important;
    border-bottom: 1px solid $dark-border;
    
    &:last-child {
      border-bottom: none;
    }
  }
  
  .el-scrollbar__view {
    padding: 10px;
  }
}

/* 深色主题全局样式 */
body {
  background-color: $dark-bg-primary;
  color: $dark-text-primary;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  margin: 0;
  padding: 0;
  transition: background-color 0.3s ease;
}

/* 全局修复输入框双层边框问题 */
.el-input .el-input__wrapper {
  box-shadow: 0 0 0 1px $dark-border inset !important;
  background-color: rgba($dark-bg-secondary, 0.8) !important;
  border: none !important;
  
  &:hover {
    box-shadow: 0 0 0 1px $purple-400 inset !important;
  }
  
  &.is-focus {
    box-shadow: 0 0 0 1px $purple-500 inset !important;
  }
}

.el-input .el-input__inner {
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  background-color: transparent !important;
  color: $dark-text-primary !important;
}

/* 表格内输入框修复 */
.el-table .el-input .el-input__wrapper {
  box-shadow: 0 0 0 1px $dark-border inset !important;
  border: none !important;
  
  &.is-focus {
    box-shadow: 0 0 0 1px $purple-500 inset !important;
  }
}

/* 表单内输入框修复 */
.el-form .el-input .el-input__wrapper {
  box-shadow: 0 0 0 1px $dark-border inset !important;
  border: none !important;
  
  &.is-focus {
    box-shadow: 0 0 0 1px $purple-500 inset !important;
  }
}

/* 树组件样式覆盖 */
.el-tree {
  background-color: transparent !important;
  color: $dark-text-primary !important;
  
  .el-tree-node__content:hover {
    background-color: $dark-bg-table-hover !important;
  }
  
  .el-tree-node:focus > .el-tree-node__content {
    background-color: transparent !important;
    
    &.is-current {
      background-color: rgba($purple-600, 0.2) !important;
    }
  }
  
  .el-tree-node.is-current > .el-tree-node__content {
    background-color: rgba($purple-600, 0.2) !important;
  }
  
  /* 防止子节点自动高亮 */
  .el-tree-node.is-expanded.is-current > .el-tree-node__children .el-tree-node > .el-tree-node__content {
    background-color: transparent !important;
    
    &:hover {
      background-color: $dark-bg-table-hover !important;
    }
    
    /* 单独选中的子节点仍然需要高亮 */
    &.is-current, 
    .el-tree-node.is-current > & {
      background-color: rgba($purple-600, 0.2) !important;
    }
  }
}
</style> 