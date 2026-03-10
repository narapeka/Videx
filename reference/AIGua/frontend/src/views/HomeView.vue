<template>
  <div class="home">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="welcome-card">
          <div class="card-header">
            <h2>欢迎使用AIGua</h2>
          </div>
          <div class="welcome-content">
            <p>这是一套为影视媒体文件管理爱好者开发的本地工具集，帮助您更高效地整理和管理您的媒体文件。</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="feature-cards">
      <el-col :span="8">
        <el-card class="feature-card" @click="$router.push('/rename')">
          <div class="feature-content">
            <el-icon class="feature-icon"><Edit /></el-icon>
            <h3>智能重命名</h3>
            <p>对媒体文件进行智能识别并标准化重命名。</p>
            <ul class="feature-list">
              <li>支持批量重命名</li>
              <li>智能识别影片信息</li>
              <li>支持自定义命名规则</li>
              <li>预览重命名效果</li>
            </ul>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="feature-card" @click="$router.push('/transfer')">
          <div class="feature-content">
            <el-icon class="feature-icon"><FolderOpened /></el-icon>
            <h3>智能转存</h3>
            <p>智能整理并转存媒体文件到指定目录。</p>
            <ul class="feature-list">
              <li>自动分类整理</li>
              <li>跳过重复文件</li>
              <li>预览转存路径</li>
              <li>支持大批量处理</li>
            </ul>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="feature-card" @click="$router.push('/config')">
          <div class="feature-content">
            <el-icon class="feature-icon"><Setting /></el-icon>
            <h3>系统配置</h3>
            <p>配置媒体库路径、API 密钥等系统设置。</p>
            <ul class="feature-list">
              <li>管理媒体库路径</li>
              <li>配置 API 密钥</li>
              <li>设置代理服务器</li>
              <li>调整批处理大小</li>
            </ul>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { Edit, Setting, FolderOpened } from '@element-plus/icons-vue'
</script>

<style lang="scss" scoped>
@use '@/styles/theme.scss' as *;

.home {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.welcome-card {
  margin-bottom: 30px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  color: $dark-text-primary;
  font-size: 24px;
}

.welcome-content {
  color: $dark-text-secondary;
  font-size: 16px;
  line-height: 1.6;
}

.feature-cards {
  margin-top: 20px;
}

.feature-card {
  height: 100%;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid $dark-border !important;
  background-color: $dark-bg-card !important;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
  border-color: $purple-500 !important;
}

.feature-content {
  text-align: center;
  padding: 20px;
}

.feature-icon {
  font-size: 48px;
  color: $purple-400;
  margin-bottom: 20px;
}

.feature-content h3 {
  margin: 0 0 15px 0;
  color: $dark-text-primary;
  font-size: 20px;
}

.feature-content p {
  color: $dark-text-secondary;
  margin-bottom: 20px;
  line-height: 1.6;
}

.feature-list {
  text-align: left;
  list-style: none;
  padding: 0;
  margin: 0;
}

.feature-list li {
  color: $dark-text-secondary;
  margin-bottom: 8px;
  padding-left: 24px;
  position: relative;
}

.feature-list li::before {
  content: "•";
  color: $purple-400;
  position: absolute;
  left: 8px;
}

@media (max-width: 768px) {
  .el-col {
    width: 100%;
    margin-bottom: 16px;
  }
  
  .feature-cards {
    margin-top: 20px;
  }
}
</style> 