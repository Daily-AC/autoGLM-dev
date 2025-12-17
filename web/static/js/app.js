/**
 * AutoGLM Console - Main Application
 * 主应用入口和全局逻辑
 */

// ===== 全局状态 =====
let profiles = [];
let logCursor = 0;
let chatRenderer = null;

// ===== DOM元素引用 =====
const elements = {
    get chatContainer() { return document.getElementById('chat-container'); },
    get promptInput() { return document.getElementById('prompt-input'); },
    get btnSend() { return document.getElementById('btn-send'); },
    get btnStop() { return document.getElementById('btn-stop'); },
    get btnRestart() { return document.getElementById('btn-restart'); },
    get logsContent() { return document.getElementById('logs-content'); },
    get terminalDrawer() { return document.getElementById('terminal-drawer'); },
    get inputContainer() { return document.getElementById('input-container'); },
    get mainLayoutArea() { return document.getElementById('main-layout-area'); },
    get profileList() { return document.getElementById('profile-list'); },
    get profileModal() { return document.getElementById('profile-modal'); },
    get statusModal() { return document.getElementById('status-modal'); },
    get confirmModal() { return document.getElementById('confirm-modal'); },
    // 状态指示器
    get dotAdb() { return document.getElementById('dot-adb'); },
    get dotApi() { return document.getElementById('dot-api'); },
    get dotAgent() { return document.getElementById('dot-agent'); },
    get textAgent() { return document.getElementById('text-agent'); },
    get headerStatusText() { return document.getElementById('header-status-text'); }
};

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', () => {
    // 初始化ChatRenderer
    chatRenderer = new ChatRenderer(elements.chatContainer);
    
    // 绑定事件
    bindEvents();
    
    // 加载数据
    fetchProfiles();
    checkStatus();
    
    // 启动轮询
    setInterval(checkStatus, 1000);
    pollLogs();
    
    // 重置loading状态（防止刷新后卡死）
    setTimeout(() => setLoading(false), 500);
    
    console.log('[AutoGLM] App initialized - VERSION 2024-12-14-v4');
});

// ===== 事件绑定 =====
function bindEvents() {
    // 发送按钮
    if (elements.btnSend) {
        elements.btnSend.onclick = sendTask;
    }
    
    // 停止按钮
    if (elements.btnStop) {
        elements.btnStop.onclick = stopTask;
    }
    
    // 重启按钮
    if (elements.btnRestart) {
        elements.btnRestart.onclick = resetSession;
    }
    
    // 输入框回车发送
    if (elements.promptInput) {
        elements.promptInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                if (elements.btnSend.disabled) {
                    e.preventDefault();
                    return;
                }
                if (!e.shiftKey) {
                    e.preventDefault();
                    sendTask();
                }
            }
        });
    }
    
    // 快捷键: Ctrl+\ 切换终端
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === '\\') {
            e.preventDefault();
            toggleTerminal();
        }
    });
}

// ===== Profiles 管理 =====
async function fetchProfiles() {
    try {
        const res = await fetch('/api/profiles');
        profiles = await res.json();
        renderProfiles();
    } catch (e) {
        console.error('Failed to fetch profiles:', e);
    }
}

function renderProfiles() {
    const list = elements.profileList;
    if (!list) return;
    
    list.innerHTML = '<div class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-3 ml-2">Service Profiles</div>';
    
    profiles.forEach((p, idx) => {
        const isActive = p.is_active;
        const card = document.createElement('div');
        card.className = `group relative p-3 rounded-xl transition-all duration-200 border cursor-pointer mb-2
            ${isActive ? 'bg-white/10 border-accent/40 shadow-[0_0_15px_-5px_#2CC985]' : 'bg-transparent border-transparent hover:bg-white/5 hover:border-white/10'}`;
        
        card.onclick = (e) => {
            if (e.target.closest('button')) return;
            activateProfile(idx);
        };
        
        card.innerHTML = `
            <div class="flex justify-between items-start">
                <div>
                    <div class="text-sm font-bold ${isActive ? 'text-white' : 'text-gray-400 group-hover:text-gray-200'}">${p.name}</div>
                    <div class="text-[10px] text-gray-500 mt-0.5 font-mono bg-black/30 px-1.5 py-0.5 rounded inline-block">
                        ${p.provider || 'Auto'} • ${p.model}
                    </div>
                </div>
                ${isActive ? '<div class="w-2 h-2 rounded-full bg-accent animate-pulse-slow"></div>' : ''}
            </div>
            <div class="absolute right-2 top-8 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onclick="openModal(${idx})" class="p-1.5 rounded hover:bg-white/20 text-gray-400 hover:text-white">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                </button>
                <button onclick="deleteProfile(${idx})" class="p-1.5 rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                </button>
            </div>
        `;
        list.appendChild(card);
    });
}

function openModal(editIdx = -1) {
    const modal = elements.profileModal;
    const title = document.getElementById('modal-title');
    document.getElementById('p-index').value = editIdx;
    
    modal.classList.remove('hidden');
    
    if (editIdx >= 0) {
        const p = profiles[editIdx];
        title.textContent = "Edit Service";
        document.getElementById('p-name').value = p.name;
        document.getElementById('p-provider').value = p.provider || "OpenAI";
        document.getElementById('p-url').value = p.base_url;
        document.getElementById('p-key').value = p.api_key;
        document.getElementById('p-model').value = p.model;
    } else {
        title.textContent = "Add Service";
        document.getElementById('p-name').value = "";
        document.getElementById('p-provider').value = "OpenAI";
        document.getElementById('p-url').value = "";
        document.getElementById('p-key').value = "";
        document.getElementById('p-model').value = "";
    }
}

function closeModal() {
    elements.profileModal.classList.add('hidden');
}

async function saveProfile() {
    const idx = parseInt(document.getElementById('p-index').value);
    const name = document.getElementById('p-name').value;
    const provider = document.getElementById('p-provider').value;
    const url = document.getElementById('p-url').value;
    const key = document.getElementById('p-key').value;
    const model = document.getElementById('p-model').value;
    
    if (!name) return alert("Service Name is required");
    
    const newProfile = { name, provider, base_url: url, api_key: key, model, is_active: false };
    
    if (idx >= 0) {
        newProfile.is_active = profiles[idx].is_active;
        profiles[idx] = newProfile;
    } else {
        if (profiles.length === 0) newProfile.is_active = true;
        profiles.push(newProfile);
    }
    
    await updateServer();
    closeModal();
}

async function deleteProfile(idx) {
    if (!confirm("Delete?")) return;
    profiles.splice(idx, 1);
    await updateServer();
}

async function activateProfile(idx) {
    // 立即反馈：API状态变为灰色闪烁
    if (elements.dotApi) {
        elements.dotApi.className = 'w-1.5 h-1.5 rounded-full bg-gray-500 animate-pulse shadow-sm';
    }
    
    profiles.forEach((p, i) => p.is_active = (i === idx));
    await updateServer();
    
    // 强制重新检查状态
    setTimeout(checkStatus, 500);
}

async function updateServer() {
    await fetch('/api/profiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profiles)
    });
    renderProfiles();
}

// ===== 任务管理 =====
async function sendTask() {
    const task = elements.promptInput.value.trim();
    if (!task) return;
    
    // 创建任务UI
    chatRenderer.createTask(task);
    elements.promptInput.value = '';
    setLoading(true);
    
    // 预检查
    const status = await checkStatus(true);
    
    const errors = [];
    if (!status.adb) errors.push({ title: "ADB Connection Failed", desc: "No Android device detected via ADB." });
    if (!status.api) errors.push({ title: "API Service Unavailable", desc: "Cannot connect to the LLM API provider." });
    if (status.agent === 'busy') errors.push({ title: "Agent Busy", desc: "The agent is currently executing another task." });
    
    if (errors.length > 0) {
        setLoading(false);
        showStatusErrors(errors);
        return;
    }
    
    // 发送任务
    try {
        await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task })
        });
    } catch (e) {
        alert(e);
        setLoading(false);
    }
}

async function stopTask() {
    if (!confirm("Stop current task?")) return;
    
    try {
        await fetch('/api/chat/stop', { method: 'DELETE' });
        setLoading(false);
        chatRenderer.addResult('Task stopped by user.', 'failed');
    } catch (e) {
        alert(e);
    }
}

async function resetSession() {
    showConfirm("Reset Session", "Clear conversation logic and reset agent state?", async () => {
        try {
            await fetch('/api/chat/reset', { method: 'POST' });
            elements.chatContainer.innerHTML = '';
            chatRenderer = new ChatRenderer(elements.chatContainer);
            
            // 添加欢迎消息
            elements.chatContainer.innerHTML = `
                <div class="flex gap-4 animate-fade-in">
                    <div class="w-8 h-8 rounded-full bg-gradient-to-br from-green-400 to-emerald-600 flex-shrink-0 flex items-center justify-center text-black text-xs font-bold shadow-lg shadow-green-500/20">AI</div>
                    <div class="flex-1 space-y-2">
                        <div class="glass-panel p-4 rounded-2xl rounded-tl-none text-gray-200 border border-white/10 shadow-xl">
                            <p class="leading-relaxed">Session Reset. Ready for new task.</p>
                        </div>
                    </div>
                </div>`;
            
            setLoading(false);
            checkStatus();
        } catch (e) {
            alert(e);
        }
    });
}

// ===== UI状态管理 =====
function setLoading(loading) {
    if (loading) {
        elements.btnSend.disabled = true;
        elements.btnSend.innerHTML = '<svg class="animate-spin h-5 w-5 text-black" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
        elements.btnSend.classList.add('opacity-50', 'cursor-not-allowed');
        elements.btnStop.classList.remove('hidden');
    } else {
        elements.btnSend.disabled = false;
        elements.btnSend.innerHTML = 'Send';
        elements.btnSend.classList.remove('opacity-50', 'cursor-not-allowed');
        elements.btnStop.classList.add('hidden');
    }
}

// ===== 终端抽屉 =====
let isTerminalOpen = false;

function toggleTerminal() {
    const drawer = elements.terminalDrawer;
    const inputContainer = elements.inputContainer;
    const mainLayout = elements.mainLayoutArea;
    
    isTerminalOpen = !isTerminalOpen;
    
    if (isTerminalOpen) {
        drawer.style.transform = "translateY(0)";
        inputContainer.style.transform = "translateY(-300px)";
        if (mainLayout) mainLayout.style.paddingBottom = "400px";
        
        setTimeout(() => {
            Utils.scrollToBottom(elements.chatContainer);
        }, 300);
    } else {
        drawer.style.transform = "translateY(120%)";
        inputContainer.style.transform = "translateY(0)";
        if (mainLayout) mainLayout.style.paddingBottom = "100px";
    }
}

// ===== 确认对话框 =====
let confirmCallback = null;

function showConfirm(title, desc, onConfirm) {
    document.getElementById('confirm-title').innerText = title;
    document.getElementById('confirm-desc').innerText = desc;
    elements.confirmModal.classList.remove('hidden');
    confirmCallback = onConfirm;
    
    document.getElementById('confirm-btn-yes').onclick = () => closeConfirm(true);
}

function closeConfirm(isYes) {
    elements.confirmModal.classList.add('hidden');
    if (isYes && confirmCallback) confirmCallback();
    confirmCallback = null;
}

// ===== 状态错误对话框 =====
function showStatusErrors(errors) {
    const list = document.getElementById('status-error-list');
    list.innerHTML = '';
    
    errors.forEach(err => {
        const item = document.createElement('div');
        item.className = "bg-red-500/5 border border-red-500/10 rounded-lg p-3 flex gap-3 items-start";
        item.innerHTML = `
            <svg class="w-5 h-5 text-red-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <div>
                <div class="text-red-400 font-bold text-xs uppercase tracking-wider mb-1">${err.title}</div>
                <div class="text-gray-400 text-xs">${err.desc}</div>
            </div>
        `;
        list.appendChild(item);
    });
    
    elements.statusModal.classList.remove('hidden');
}

// ===== 状态检查 =====
async function checkStatus(returnData = false) {
    try {
        const res = await fetch('/api/status');
        const status = await res.json();
        
        // 更新ADB状态
        if (elements.dotAdb) {
            elements.dotAdb.className = `w-1.5 h-1.5 rounded-full transition-colors duration-500 ${status.adb ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' : 'bg-red-500'}`;
        }
        
        // 更新API状态
        if (elements.dotApi) {
            let apiClass = 'bg-gray-500 animate-pulse';
            if (status.api === true) apiClass = 'bg-green-500 shadow-[0_0_8px_#22c55e]';
            else if (status.api === false) apiClass = 'bg-red-500';
            elements.dotApi.className = `w-1.5 h-1.5 rounded-full transition-colors duration-500 ${apiClass}`;
        }
        
        // 更新Agent状态
        if (elements.dotAgent) {
            if (status.agent === 'busy') {
                elements.dotAgent.className = 'w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse shadow-[0_0_8px_#facc15]';
                if (elements.textAgent) {
                    elements.textAgent.innerText = 'BUSY';
                    elements.textAgent.className = 'text-[10px] uppercase font-bold text-yellow-500 tracking-wider';
                }
                if (!elements.btnSend.disabled) setLoading(true);
            } else {
                const isReady = status.agent === 'ready';
                elements.dotAgent.className = `w-1.5 h-1.5 rounded-full transition-colors duration-500 ${isReady ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' : 'bg-gray-600'}`;
                if (elements.textAgent) {
                    elements.textAgent.innerText = isReady ? 'READY' : 'OFFLINE';
                    elements.textAgent.className = `text-[10px] uppercase font-bold tracking-wider ${isReady ? 'text-gray-200' : 'text-gray-400'}`;
                }
            }
        }
        
        if (returnData) return status;
        
    } catch (e) {
        if (returnData) return { adb: false, api: false, agent: 'offline' };
    }
}

// ===== 日志轮询 =====
async function pollLogs() {
    try {
        const res = await fetch(`/api/logs?since=${logCursor}`);
        const data = await res.json();
        
        if (data.logs.length > 0) {
            appendLogs(data.logs);
            logCursor = data.next_cursor;
        }
    } catch (e) {
        // Ignore
    }
    
    setTimeout(pollLogs, 200);
}

function appendLogs(logs) {
    logs.forEach(line => {
        if (!line) return;
        line = Utils.stripAnsi(line);
        if (!line.trim()) return;
        
        let entry = null;
        try {
            if (line.trim().startsWith('{')) {
                entry = JSON.parse(line);
            }
        } catch (e) {
            // Not JSON
        }
        
        if (entry && entry.tag) {
            // 处理结构化日志
            processLogEntry(entry);
            
            // 同时显示在终端
            appendToTerminal(entry);
        } else {
            // 处理纯文本日志
            // 兼容旧格式的思考日志 (如果后端未发送 JSON 格式)
            if (line.includes('💭')) {
                const thoughtText = line.substring(line.indexOf('💭') + 2).trim();
                if (chatRenderer) {
                    chatRenderer.appendThinking(thoughtText);
                }
            }
            // 始终添加到终端
            appendLogToTerminal(line);
        }
    });
}

function processLogEntry(entry) {
    switch (entry.tag) {
        case 'STREAM':
            const streamContent = (entry.msg || '').trim();
            if (streamContent && streamContent !== '<answer>' && !/^<\/?answer>+$/.test(streamContent)) {
                 if (chatRenderer) {
                     chatRenderer.appendThinking(streamContent);
                 }
            }
            break;
            
        case 'THOUGHT':
            const thoughtContent = (entry.msg || '').trim();
            if (thoughtContent) {
                if (chatRenderer) {
                    // THOUGHT 是全量日志，使用 setThinking 替换流式内容
                    chatRenderer.setThinking(thoughtContent);
                }
            }
            break;
            
        case 'ACTION':
            const actionName = entry.msg || 'unknown';
            const actionData = entry.details?.action_details || entry.details;
            if (chatRenderer) {
                chatRenderer.addAction(actionName, actionData);
            }
            break;
            
        case 'RESULT':
            const resultMsg = Utils.stripAnsi(entry.msg || '').trim();
            if (chatRenderer) {
                chatRenderer.addResult(resultMsg, 'success');
            }
            setLoading(false);
            break;
            
        case 'TAKEOVER':
            const takeoverMsg = Utils.stripAnsi(entry.msg || '').trim();
            if (chatRenderer) {
                chatRenderer.addResult(takeoverMsg, 'takeover');
            }
            setLoading(false);
            break;
            
        case 'FAILED':
            const failedMsg = Utils.stripAnsi(entry.msg || '').trim();
            if (chatRenderer) {
                chatRenderer.addResult(failedMsg, 'failed');
            }
            setLoading(false);
            break;
            
        case 'CANCELLED':
            setLoading(false);
            break;
    }
    
    // 处理错误级别日志
    if (entry.level === 'ERROR') {
        setLoading(false);
    }
}

function appendToTerminal(entry) {
    const consoleEl = elements.logsContent;
    if (!consoleEl || entry.tag === 'STREAM') return;
    
    let colorClass = "text-gray-400";
    if (entry.level === "ERROR") colorClass = "text-red-400 font-bold";
    else if (entry.level === "WARN") colorClass = "text-yellow-400";
    else if (entry.level === "AGENT") colorClass = "text-blue-400";
    else if (entry.tag === "THOUGHT") colorClass = "text-gray-500 italic";
    
    const timeStr = new Date(entry.ts * 1000).toLocaleTimeString([], { hour12: false });
    const lineStr = `[${timeStr}] ${entry.msg}`;
    
    const d = document.createElement('div');
    d.className = `${colorClass} hover:text-gray-200 transition-colors border-b border-white/5 pb-1 mb-1`;
    d.textContent = lineStr;
    
    if (entry.details && Object.keys(entry.details).length > 0) {
        const det = document.createElement('div');
        det.className = "text-[10px] text-gray-600 pl-4 overflow-hidden hidden font-mono mt-1";
        det.textContent = JSON.stringify(entry.details, null, 2);
        d.appendChild(det);
        d.onclick = () => det.classList.toggle('hidden');
        d.style.cursor = "pointer";
    }
    consoleEl.appendChild(d);
    
    // 自动滚动
    if (consoleEl.scrollHeight - consoleEl.scrollTop - consoleEl.clientHeight < 100) {
        consoleEl.scrollTop = consoleEl.scrollHeight;
    }
}

function appendLogToTerminal(line) {
    const consoleEl = elements.logsContent;
    if (!consoleEl) return;
    
    const d = document.createElement('div');
    d.className = line.includes("ERROR") ? "text-red-400" : "text-gray-500 hover:text-gray-300";
    d.textContent = "> " + line;
    consoleEl.appendChild(d);
    consoleEl.scrollTop = consoleEl.scrollHeight;
}

// ===== 远程控制 =====
const overlay = document.getElementById('control-overlay');
const inputPopover = document.getElementById('text-input-popover');
const remoteInput = document.getElementById('remote-input');

let isDragging = false;
let startX = 0, startY = 0;
let startTime = 0;

if (overlay) {
    const onStart = (e) => {
        e.preventDefault();
        isDragging = false;
        const pt = getPoint(e);
        startX = pt.x;
        startY = pt.y;
        startTime = Date.now();
    };
    
    const onMove = (e) => {
        if (e.buttons === 0 && e.type !== 'touchmove') return;
        const pt = getPoint(e);
        const dist = Math.hypot(pt.x - startX, pt.y - startY);
        if (dist > 0.02) isDragging = true;
    };
    
    const onEnd = async (e) => {
        const pt = getPoint(e, true);
        const duration = Date.now() - startTime;
        
        if (isDragging) {
            await apiCall('/api/control/swipe', {
                start_x: startX, start_y: startY,
                end_x: pt.x, end_y: pt.y,
                duration: Math.min(Math.max(duration, 100), 1000)
            });
        } else {
            showTapEffect(e);
            await apiCall('/api/control/tap', { x: startX, y: startY });
        }
        isDragging = false;
    };
    
    overlay.addEventListener('mousedown', onStart);
    overlay.addEventListener('mousemove', onMove);
    overlay.addEventListener('mouseup', onEnd);
    overlay.addEventListener('touchstart', onStart);
    overlay.addEventListener('touchmove', onMove);
    overlay.addEventListener('touchend', onEnd);
}

function getPoint(e, isEnd = false) {
    const rect = overlay.getBoundingClientRect();
    let clientX, clientY;
    
    if (e.changedTouches && e.changedTouches.length > 0) {
        clientX = e.changedTouches[0].clientX;
        clientY = e.changedTouches[0].clientY;
    } else {
        clientX = e.clientX;
        clientY = e.clientY;
    }
    
    const x = (clientX - rect.left) / rect.width;
    const y = (clientY - rect.top) / rect.height;
    return { x: Math.max(0, Math.min(1, x)), y: Math.max(0, Math.min(1, y)) };
}

function showTapEffect(e) {
    const rect = overlay.getBoundingClientRect();
    let x, y;
    if (e.changedTouches) {
        x = e.changedTouches[0].clientX - rect.left;
        y = e.changedTouches[0].clientY - rect.top;
    } else {
        x = e.clientX - rect.left;
        y = e.clientY - rect.top;
    }
    
    const ripple = document.createElement('div');
    ripple.className = 'absolute bg-white/50 rounded-full w-8 h-8 pointer-events-none animate-ping';
    ripple.style.left = (x - 16) + 'px';
    ripple.style.top = (y - 16) + 'px';
    overlay.appendChild(ripple);
    setTimeout(() => ripple.remove(), 500);
}

async function apiCall(url, data) {
    try {
        await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    } catch (e) {
        console.error('Control Error:', e);
    }
}

function sendKey(keycode) {
    apiCall('/api/control/key', { keycode });
}

function toggleTextInput() {
    if (inputPopover.classList.contains('hidden')) {
        inputPopover.classList.remove('hidden');
        remoteInput.focus();
    } else {
        inputPopover.classList.add('hidden');
    }
}

async function sendTextInput() {
    const text = remoteInput.value;
    if (text) {
        await apiCall('/api/control/input', { text });
        remoteInput.value = '';
        toggleTextInput();
    }
}

if (remoteInput) {
    remoteInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendTextInput();
    });
}

// ===== 导出全局函数 =====
window.openModal = openModal;
window.closeModal = closeModal;
window.saveProfile = saveProfile;
window.deleteProfile = deleteProfile;
window.activateProfile = activateProfile;
window.sendTask = sendTask;
window.checkStatus = checkStatus;
window.toggleTerminal = toggleTerminal;
window.sendKey = sendKey;
window.toggleTextInput = toggleTextInput;
window.sendTextInput = sendTextInput;
