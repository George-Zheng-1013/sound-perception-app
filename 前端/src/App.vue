<template>
    <div id="app">
        <header class="app-header">
            <h1 class="app-title">
                <el-icon class="title-icon">
                    <Microphone />
                </el-icon>
                声音感知识别系统
            </h1>
            <p class="app-subtitle">基于AI的非语言声音智能识别平台</p>
        </header>

        <main class="app-main">
            <RouterView />
        </main>

        <footer class="app-footer">
            <p>&copy; 2024 声音感知识别系统 | 挑战杯作品</p>
        </footer>
    </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import { Microphone } from '@element-plus/icons-vue'
</script>

<style scoped>
#app {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    background: #f8f9fa;
}

.app-header {
    background: white;
    padding: 1.5rem 0;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    position: sticky;
    top: 0;
    z-index: 100;
}

.app-title {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    font-size: 2rem;
    font-weight: 600;
    color: #2c3e50;
    margin: 0 0 0.5rem 0;
}

.title-icon {
    font-size: 2rem;
    color: #409EFF;
}

.app-subtitle {
    font-size: 1rem;
    color: #6c757d;
    margin: 0;
    font-weight: 400;
}

.app-main {
    flex: 1;
    padding: 0;
}

.app-footer {
    background: #2c3e50;
    color: white;
    text-align: center;
    padding: 1rem 0;
    margin-top: auto;
}

.app-footer p {
    margin: 0;
    font-size: 0.9rem;
    opacity: 0.8;
}

/* 响应式设计 */
@media (max-width: 768px) {
    .app-title {
        font-size: 1.6rem;
        flex-direction: column;
        gap: 8px;
    }

    .title-icon {
        font-size: 1.6rem;
    }

    .app-subtitle {
        font-size: 0.9rem;
    }

    .app-header {
        padding: 1rem;
    }
}

@media (max-width: 480px) {
    .app-title {
        font-size: 1.4rem;
    }

    .title-icon {
        font-size: 1.4rem;
    }

    .app-subtitle {
        font-size: 0.8rem;
    }
}
</style>
