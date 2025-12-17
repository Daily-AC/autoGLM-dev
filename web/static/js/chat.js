/**
 * AutoGLM Console - Chat Renderer
 * 对话区渲染核心模块
 */

class ChatRenderer {
    constructor(container) {
        this.container = container;
        this.currentTask = null;
        this.currentThinking = null;
        this.lastActionId = null;
        this.taskStartTime = null;
        this.timerInterval = null;
        
        // 去重用
        this.lastBubbleType = null;
        this.lastBubbleContent = null;
        
        // 虚拟滚动配置
        this.virtualScrollEnabled = false;
        this.maxVisibleTasks = 50;
        this.tasks = [];
    }
    
    /**
     * 创建新任务卡片
     */
    createTask(userInput) {
        // 清理之前的状态
        this.completeCurrentThinking();
        this.resetDeduplication();
        
        const taskId = Utils.generateId('task');
        this.taskStartTime = Date.now();
        
        const taskHtml = `
        <div class="task-card task-running" id="${taskId}">
            <!-- Task Header -->
            <div class="task-header">
                <div class="user-avatar">U</div>
                <div class="task-content">
                    <div class="task-input">${this.escapeHtml(userInput)}</div>
                </div>
                <div class="task-meta">
                    <span class="status-badge badge-running">
                        <span class="badge-dot"></span>
                        执行中
                    </span>
                    <span class="task-timer" id="${taskId}-timer">00:00</span>
                </div>
            </div>
            
            <!-- Task Body -->
            <div class="task-body">
                <div class="actions-container" id="${taskId}-actions"></div>
                <div class="task-loading" id="${taskId}-loading">
                    <div class="loading-spinner"></div>
                    <span>正在处理中...</span>
                </div>
            </div>
        </div>`;
        
        this.container.insertAdjacentHTML('beforeend', taskHtml);
        this.currentTask = document.getElementById(taskId);
        this.tasks.push(taskId);
        
        // 启动计时器
        this.startTimer(taskId);
        
        // 滚动到底部
        Utils.scrollToBottom(this.container);
        
        // 虚拟滚动：如果任务过多，移除旧任务
        this.pruneOldTasks();
        
        return this.currentTask;
    }
    
    /**
     * 追加思考内容（流式）
     */
    appendThinking(text) {
        if (!this.currentTask) return;
        
        const cleanText = Utils.stripAnsi(text || '').trim();
        if (!cleanText || cleanText === '<answer>' || /^<\/?answer>+$/.test(cleanText)) {
            return;
        }
        
        // 如果没有当前思考块，创建一个
        if (!this.currentThinking) {
            const thinkingId = Utils.generateId('thinking');
            const actionsContainer = this.currentTask.querySelector('.actions-container');
            
            const thinkingHtml = `
            <div class="thinking-block" id="${thinkingId}">
                <div class="block-header" onclick="window.ChatRenderer.toggleThinking('${thinkingId}')">
                    <span class="block-icon">💭</span>
                    <span class="block-label">Agent 思考过程</span>
                    <div class="block-status">
                        <span class="thinking-cursor"></span>
                    </div>
                    <svg class="block-caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M6 9l6 6 6-6"/>
                    </svg>
                </div>
                <div class="block-content custom-scrollbar">
                    <div class="thinking-stream"></div>
                </div>
            </div>`;
            
            actionsContainer.insertAdjacentHTML('beforeend', thinkingHtml);
            this.currentThinking = document.getElementById(thinkingId);
        }
        
        // 追加文字
        const stream = this.currentThinking.querySelector('.thinking-stream');
        if (stream) {
            stream.textContent += cleanText;
            // 滚动思考区域到底部
            const content = this.currentThinking.querySelector('.block-content');
            if (content) {
                content.scrollTop = content.scrollHeight;
            }
        }
        
        // 如果聊天区域接近底部，自动滚动
        if (Utils.isNearBottom(this.container)) {
            Utils.scrollToBottom(this.container);
        }
    }
    
    /**
     * 设置思考内容（全量替换）
     */
    setThinking(text) {
        if (!this.currentTask) return;
        
        const cleanText = Utils.stripAnsi(text || '').trim();
        if (!cleanText) return;
        
        // 如果没有当前思考块，创建一个
        if (!this.currentThinking) {
            this.appendThinking(cleanText);
            return;
        }
        
        const stream = this.currentThinking.querySelector('.thinking-stream');
        if (stream) {
            stream.textContent = cleanText;
            // 滚动到底部
            const content = this.currentThinking.querySelector('.block-content');
            if (content) {
                content.scrollTop = content.scrollHeight;
            }
        }
    }
    
    /**
     * 完成当前思考块
     */
    completeCurrentThinking() {
        if (!this.currentThinking) return;
        
        this.currentThinking.classList.add('completed');
        const label = this.currentThinking.querySelector('.block-label');
        if (label) label.textContent = '已完成思考';
        
        // 移除光标
        const cursor = this.currentThinking.querySelector('.thinking-cursor');
        if (cursor) cursor.remove();
        
        this.currentThinking = null;
    }
    
    /**
     * 添加动作卡片
     */
    addAction(actionName, details, startTime = Date.now()) {
        if (!this.currentTask) return null;
        
        // 完成之前的思考
        this.completeCurrentThinking();
        
        // 格式化动作信息
        const actionInfo = Utils.formatActionForDisplay(actionName, details);
        
        // 去重检查
        const actionKey = `${actionName}:${JSON.stringify(details)}`;
        if (this.lastBubbleType === 'action' && this.lastBubbleContent === actionKey) {
            return null;
        }
        this.lastBubbleType = 'action';
        this.lastBubbleContent = actionKey;
        
        // 完成上一个动作
        if (this.lastActionId) {
            this.completeAction(this.lastActionId);
        }
        
        const actionId = Utils.generateId('action');
        const actionsContainer = this.currentTask.querySelector('.actions-container');
        const detailsJson = JSON.stringify(actionInfo.rawDetails, null, 2);
        
        const actionHtml = `
        <div class="action-card ${actionInfo.cssClass} status-running" id="${actionId}" data-start-time="${startTime}">
            <div class="action-main">
                <span class="action-icon">${actionInfo.icon}</span>
                <div class="action-info">
                    <span class="action-name">${actionInfo.name}</span>
                    ${actionInfo.target ? `<span class="action-arrow">→</span><span class="action-target">${this.escapeHtml(actionInfo.target)}</span>` : ''}
                </div>
                <div class="action-meta">
                    <div class="action-status">
                        <div class="spinner"></div>
                    </div>
                    <span class="action-duration">...</span>
                    <div class="action-buttons">
                        <button class="btn-action btn-copy" title="复制JSON" onclick="window.ChatRenderer.copyActionJson('${actionId}')">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                                <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                            </svg>
                        </button>
                        <button class="btn-action btn-expand" title="展开详情" onclick="window.ChatRenderer.toggleActionDetails('${actionId}')">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M9 18l6-6-6-6"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
            <div class="action-details" data-json='${this.escapeHtml(detailsJson)}'>
                <div class="action-details-inner">
                    <pre class="json-view"><code class="language-json">${this.escapeHtml(detailsJson)}</code></pre>
                </div>
            </div>
        </div>`;
        
        // 直接插入到 actions-container 中，保证与 Thinking 的顺序一致
        actionsContainer.insertAdjacentHTML('beforeend', actionHtml);
        
        this.lastActionId = actionId;
        
        // 语法高亮
        this.highlightJson(actionId);
        
        // 滚动到底部
        if (Utils.isNearBottom(this.container)) {
            Utils.scrollToBottom(this.container);
        }
        
        return actionId;
    }
    
    /**
     * 完成某个动作
     */
    completeAction(actionId, success = true) {
        const action = document.getElementById(actionId);
        if (!action) return;
        
        // 计算耗时
        const startTime = parseInt(action.dataset.startTime || Date.now());
        const duration = Date.now() - startTime;
        
        // 更新状态
        action.classList.remove('status-running');
        action.classList.add(success ? 'status-success' : 'status-error');
        
        // 更新状态图标
        const statusEl = action.querySelector('.action-status');
        if (statusEl) {
            statusEl.innerHTML = success 
                ? '<svg class="icon-success" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>'
                : '<svg class="icon-error" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>';
        }
        
        // 更新耗时
        const durationEl = action.querySelector('.action-duration');
        if (durationEl) {
            durationEl.textContent = Utils.formatDuration(duration);
        }
    }
    
    /**
     * 添加结果块
     */
    addResult(message, status = 'success') {
        if (!this.currentTask) return;
        
        // 完成当前思考和最后一个动作
        this.completeCurrentThinking();
        if (this.lastActionId) {
            this.completeAction(this.lastActionId, status === 'success');
            this.lastActionId = null;
        }
        
        // 移除loading indicator
        const loadingIndicator = this.currentTask.querySelector('.task-loading');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
        
        // 去重检查
        const cleanMessage = Utils.stripAnsi(message || '').trim();
        if (this.lastBubbleType === 'result' && this.lastBubbleContent === cleanMessage) {
            return;
        }
        this.lastBubbleType = 'result';
        this.lastBubbleContent = cleanMessage;
        
        const resultClass = status === 'success' ? 'result-success' : 
                           status === 'failed' ? 'result-failed' : 'result-takeover';
        const resultIcon = status === 'success' ? '✅' : 
                          status === 'failed' ? '❌' : '⚠️';
        const resultLabel = status === 'success' ? '任务完成' : 
                           status === 'failed' ? '任务失败' : '需要协助';
        
        let resultHtml = `
        <div class="result-block ${resultClass}">
            <div class="result-header">
                <span>${resultIcon}</span>
                <span>${resultLabel}</span>
            </div>
            <div class="result-content">${this.escapeHtml(cleanMessage)}</div>`;
        
        // 如果是takeover，添加确认按钮
        if (status === 'takeover') {
            resultHtml += `
            <div style="padding: 0 16px 16px;">
                <button class="takeover-btn" onclick="window.ChatRenderer.confirmTakeover()">
                    ✓ 我已完成操作，继续执行
                </button>
            </div>`;
        }
        
        resultHtml += `</div>`;
        
        const taskBody = this.currentTask.querySelector('.task-body');
        taskBody.insertAdjacentHTML('beforeend', resultHtml);
        
        // 更新任务卡片状态
        this.currentTask.classList.remove('task-running');
        this.currentTask.classList.add(status === 'success' ? 'task-success' : 'task-failed');
        
        // 更新状态徽章
        const badge = this.currentTask.querySelector('.status-badge');
        if (badge) {
            badge.classList.remove('badge-running');
            badge.classList.add(status === 'success' ? 'badge-success' : 'badge-error');
            badge.innerHTML = status === 'success' 
                ? '✓ 完成' 
                : (status === 'failed' ? '✗ 失败' : '⚠ 等待');
        }
        
        // 停止计时器
        this.stopTimer();
        
        // 如果失败，添加继续按钮
        if (status === 'failed') {
            this.addContinueButtons();
        }
        
        // 清理当前任务引用
        if (status !== 'takeover') {
            this.currentTask = null;
        }
        
        Utils.scrollToBottom(this.container);
    }
    
    /**
     * 添加继续/重试按钮
     */
    addContinueButtons() {
        if (!this.currentTask) return;
        
        const taskBody = this.currentTask.querySelector('.task-body');
        
        const buttonsHtml = `
        <div class="continue-actions">
            <button class="btn-continue btn-primary" onclick="window.ChatRenderer.continueTask()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                继续任务
            </button>
            <button class="btn-continue btn-secondary" onclick="window.ChatRenderer.resetAndNew()">
                重新开始
            </button>
        </div>`;
        
        taskBody.insertAdjacentHTML('beforeend', buttonsHtml);
    }
    
    /**
     * 启动任务计时器
     */
    startTimer(taskId) {
        const timerEl = document.getElementById(`${taskId}-timer`);
        if (!timerEl) return;
        
        this.timerInterval = setInterval(() => {
            const elapsed = Date.now() - this.taskStartTime;
            const seconds = Math.floor(elapsed / 1000);
            const minutes = Math.floor(seconds / 60);
            const secs = seconds % 60;
            timerEl.textContent = `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        }, 1000);
    }
    
    /**
     * 停止计时器
     */
    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }
    
    /**
     * 重置去重状态
     */
    resetDeduplication() {
        this.lastBubbleType = null;
        this.lastBubbleContent = null;
    }
    
    /**
     * 转义HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * JSON语法高亮
     */
    highlightJson(actionId) {
        if (typeof Prism !== 'undefined') {
            const action = document.getElementById(actionId);
            if (action) {
                const codeBlock = action.querySelector('code.language-json');
                if (codeBlock) {
                    Prism.highlightElement(codeBlock);
                }
            }
        }
    }
    
    /**
     * 虚拟滚动：移除旧任务
     */
    pruneOldTasks() {
        if (!this.virtualScrollEnabled) return;
        
        while (this.tasks.length > this.maxVisibleTasks) {
            const oldTaskId = this.tasks.shift();
            const oldTask = document.getElementById(oldTaskId);
            if (oldTask) {
                oldTask.remove();
            }
        }
    }
    
    // ===== 静态方法（供HTML调用） =====
    
    static toggleThinking(thinkingId) {
        const block = document.getElementById(thinkingId);
        if (!block) return;
        block.classList.toggle('collapsed');
    }
    
    static toggleActionDetails(actionId) {
        const action = document.getElementById(actionId);
        if (!action) return;
        
        const details = action.querySelector('.action-details');
        const btn = action.querySelector('.btn-expand svg');
        
        if (details.classList.contains('expanded')) {
            details.classList.remove('expanded');
            if (btn) btn.style.transform = 'rotate(0deg)';
        } else {
            details.classList.add('expanded');
            if (btn) btn.style.transform = 'rotate(90deg)';
        }
    }
    
    static async copyActionJson(actionId) {
        const action = document.getElementById(actionId);
        if (!action) return;
        
        const details = action.querySelector('.action-details');
        const json = details?.dataset?.json || '{}';
        
        const success = await Utils.copyToClipboard(json);
        
        // 视觉反馈
        const btn = action.querySelector('.btn-copy');
        if (btn && success) {
            btn.classList.add('copied');
            setTimeout(() => btn.classList.remove('copied'), 1500);
        }
    }
    
    static async confirmTakeover() {
        try {
            await fetch('/api/takeover_confirm', { method: 'POST' });
        } catch (e) {
            console.log('Takeover confirm sent');
        }
    }
    
    static async continueTask() {
        // 移除继续按钮
        const continueActions = document.querySelector('.continue-actions');
        if (continueActions) continueActions.remove();
        
        try {
            await fetch('/api/chat/continue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (e) {
            console.error('Continue failed:', e);
        }
    }
    
    static resetAndNew() {
        const continueActions = document.querySelector('.continue-actions');
        if (continueActions) continueActions.remove();
        
        const input = document.getElementById('prompt-input');
        if (input) input.focus();
    }
}

// 导出到全局
window.ChatRenderer = ChatRenderer;
