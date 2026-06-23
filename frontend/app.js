window.addEventListener("DOMContentLoaded", () => {
    const chatList = document.getElementById("chatList");
    const chatMessages = document.getElementById("chatMessages");
    const chatInput = document.getElementById("chatInput");
    const chatForm = document.getElementById("chatForm");
    const sendBtn = document.getElementById("sendBtn");
    const sidebar = document.getElementById("sidebar");
    const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
    const sidebarCloseBtn = document.getElementById("sidebarCloseBtn");
    const sidebarBackdrop = document.getElementById("sidebarBackdrop");
    const newChatBtn = document.getElementById("newChatBtn");
    const deleteChatBtn = document.getElementById("deleteChatBtn");
    const statusBanner = document.getElementById("statusBanner");
    const chatTitleInput = document.getElementById("chatTitleInput");
    const chatTitleHeading = document.getElementById("chatTitleHeading");
    const renameChatBtn = document.getElementById("renameChatBtn");

    let currentChatId = null;
    let currentUser = null;

    function isSmallScreen() {
        return window.matchMedia("(max-width: 768px)").matches;
    }

    function openSidebar() {
        document.body.classList.add("sidebar-open");
        document.body.classList.remove("sidebar-collapsed");
        sidebarBackdrop.classList.remove("hidden");
        sidebarToggleBtn.setAttribute("aria-expanded", "true");
    }

    function closeSidebar() {
        document.body.classList.remove("sidebar-open");
        sidebarBackdrop.classList.add("hidden");
        if (!isSmallScreen()) {
            document.body.classList.add("sidebar-collapsed");
            sidebarToggleBtn.setAttribute("aria-expanded", "false");
        } else {
            sidebarToggleBtn.setAttribute("aria-expanded", "false");
        }
    }

    function toggleSidebar() {
        if (isSmallScreen()) {
            if (document.body.classList.contains("sidebar-open")) {
                closeSidebar();
            } else {
                openSidebar();
            }
            return;
        }

        document.body.classList.toggle("sidebar-collapsed");
        const expanded = !document.body.classList.contains("sidebar-collapsed");
        sidebarToggleBtn.setAttribute("aria-expanded", String(expanded));
    }

    function getToken() {
        return localStorage.getItem("token");
    }

    function authHeaders(extra = {}) {
        return {
            "Authorization": "Bearer " + getToken(),
            ...extra,
        };
    }

    function jsonHeaders() {
        return authHeaders({ "Content-Type": "application/json" });
    }

    function setStatus(message, type = "") {
        statusBanner.textContent = message || "";
        statusBanner.className = "status-banner" + (type ? " " + type : "");
    }

    async function readJsonSafely(response) {
        try {
            return await response.json();
        } catch (_) {
            return null;
        }
    }

    function errorText(data, fallback) {
        if (data && typeof data.detail === "string") return data.detail;
        return fallback;
    }

    function formatDate(value) {
        if (!value) return "";
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return "";
        return date.toLocaleString([], { dateStyle: "short", timeStyle: "short" });
    }

    function safeMarkdown(text) {
        const source = text || "";
        if (window.marked && window.DOMPurify) {
            return window.DOMPurify.sanitize(window.marked.parse(source));
        }

        // Fallback: show plain text if Markdown libraries are not loaded.
        const div = document.createElement("div");
        div.textContent = source;
        return div.innerHTML;
    }

    function showEmptyState(title, text) {
        chatMessages.innerHTML = "";
        const box = document.createElement("div");
        box.className = "empty-state";
        box.innerHTML = `<h2>${title}</h2><p>${text}</p>`;
        chatMessages.appendChild(box);
    }

    function closeAllChatMenus() {
        document.querySelectorAll(".chat-dropdown").forEach(menu => menu.classList.add("hidden"));
        document.querySelectorAll(".chat-menu-button").forEach(button => button.setAttribute("aria-expanded", "false"));
    }

    function positionChatMenu(menu, button) {
        const rect = button.getBoundingClientRect();
        const menuWidth = 180;
        const gap = 6;

        menu.classList.remove("hidden");

        const menuHeight = menu.offsetHeight || 92;
        let left = rect.right - menuWidth;
        let top = rect.bottom + gap;

        left = Math.max(10, Math.min(left, window.innerWidth - menuWidth - 10));

        if (top + menuHeight > window.innerHeight - 10) {
            top = rect.top - menuHeight - gap;
        }
        top = Math.max(10, top);

        menu.style.left = left + "px";
        menu.style.top = top + "px";
    }

    function removeDetachedChatMenus() {
        document.querySelectorAll("body > .chat-dropdown").forEach(menu => menu.remove());
    }

    function appendMessage(role, content) {
        const div = document.createElement("div");
        div.className = "msg " + (role === "user" ? "msg-user" : "msg-bot");

        if (role === "assistant") {
            div.innerHTML = safeMarkdown(content);
        } else {
            div.textContent = content;
        }

        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return div;
    }

    function createThinkingBubble() {
        const bubble = document.createElement("div");
        bubble.className = "msg msg-bot thinking-bubble";
        bubble.innerHTML = `
            <span class="thinking-label">Thinking</span>
            <span class="thinking-dots" aria-hidden="true">.</span>
        `;

        const dots = bubble.querySelector(".thinking-dots");
        let count = 1;
        const timer = window.setInterval(() => {
            count = count >= 3 ? 1 : count + 1;
            dots.textContent = ".".repeat(count);
        }, 420);

        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return {
            element: bubble,
            stop() {
                window.clearInterval(timer);
            },
        };
    }

    async function loadUser() {
        const token = getToken();
        if (!token) {
            window.location.href = "/";
            return;
        }

        try {
            const response = await fetch("/auth/me", { headers: authHeaders() });
            if (!response.ok) {
                localStorage.removeItem("token");
                window.location.href = "/";
                return;
            }

            currentUser = await response.json();
            document.getElementById("userDisplay").textContent = "Logged in as " + currentUser.name;
        } catch (_) {
            localStorage.removeItem("token");
            window.location.href = "/";
        }
    }

    async function loadChats() {
        removeDetachedChatMenus();

        const response = await fetch("/api/chats", { headers: authHeaders() });
        if (!response.ok) {
            setStatus("Could not load chats.", "error");
            return;
        }

        const chats = await response.json();
        chatList.innerHTML = "";

        if (chats.length === 0) {
            const li = document.createElement("li");
            li.className = "chat-item-date";
            li.textContent = "No chats yet.";
            chatList.appendChild(li);
            currentChatId = null;
            chatTitleInput.value = "";
            chatTitleHeading.textContent = "No chat selected";
            showEmptyState("No chats yet", "Create your first chat using the New chat button.");
            return;
        }

        chats.forEach(chat => {
            const li = document.createElement("li");
            li.className = "chat-row";

            const wrap = document.createElement("div");
            wrap.className = "chat-item-wrap" + (chat.id === currentChatId ? " selected" : "");

            const button = document.createElement("button");
            button.type = "button";
            button.className = "chat-item" + (chat.id === currentChatId ? " selected" : "");
            button.dataset.chatId = String(chat.id);
            button.setAttribute("aria-current", chat.id === currentChatId ? "true" : "false");
            button.innerHTML = `
                <span class="chat-item-title"></span>
                <span class="chat-item-date"></span>
            `;
            button.querySelector(".chat-item-title").textContent = chat.title || ("Chat " + chat.id);
            button.querySelector(".chat-item-date").textContent = formatDate(chat.updated_at);
            button.addEventListener("click", () => {
                closeAllChatMenus();
                selectChat(chat.id);
                if (isSmallScreen()) closeSidebar();
            });

            const menuButton = document.createElement("button");
            menuButton.type = "button";
            menuButton.className = "chat-menu-button";
            menuButton.setAttribute("aria-label", "Open chat menu for " + (chat.title || ("Chat " + chat.id)));
            menuButton.setAttribute("aria-expanded", "false");
            menuButton.textContent = "⋯";

            const menu = document.createElement("div");
            menu.className = "chat-dropdown hidden";
            menu.innerHTML = `
                <button class="chat-menu-action" type="button" data-action="rename">
                    <span class="chat-menu-icon" aria-hidden="true">✎</span>
                    <span>Rename chat</span>
                </button>
                <button class="chat-menu-action danger" type="button" data-action="delete">
                    <span class="chat-menu-icon" aria-hidden="true">🗑</span>
                    <span>Delete chat</span>
                </button>
            `;
            document.body.appendChild(menu);

            menuButton.addEventListener("click", event => {
                event.stopPropagation();
                const isOpen = !menu.classList.contains("hidden");
                closeAllChatMenus();
                if (!isOpen) {
                    positionChatMenu(menu, menuButton);
                    menuButton.setAttribute("aria-expanded", "true");
                }
            });

            menu.addEventListener("click", event => {
                event.stopPropagation();
            });

            menu.querySelector('[data-action="rename"]').addEventListener("click", event => {
                event.stopPropagation();
                closeAllChatMenus();
                renameChatById(chat.id, chat.title || ("Chat " + chat.id));
            });

            menu.querySelector('[data-action="delete"]').addEventListener("click", event => {
                event.stopPropagation();
                closeAllChatMenus();
                deleteChatById(chat.id);
            });

            wrap.appendChild(button);
            wrap.appendChild(menuButton);
            li.appendChild(wrap);
            chatList.appendChild(li);
        });

        if (!currentChatId) {
            await selectChat(chats[0].id);
        }
    }

    async function selectChat(id) {
        currentChatId = id;
        setStatus("Loading chat...");

        const chatResponse = await fetch("/api/chats", { headers: authHeaders() });
        if (chatResponse.ok) {
            const chats = await chatResponse.json();
            const selected = chats.find(chat => chat.id === id);
            chatTitleInput.value = selected ? selected.title : "";
            chatTitleHeading.textContent = selected ? selected.title : "Selected chat";
        }

        const response = await fetch(`/api/chats/${id}/messages`, { headers: authHeaders() });
        if (!response.ok) {
            setStatus("Could not load messages.", "error");
            return;
        }

        const messages = await response.json();
        chatMessages.innerHTML = "";

        if (messages.length === 0) {
            showEmptyState("Empty chat", "Write a message to start the conversation.");
        } else {
            messages.forEach(msg => appendMessage(msg.role, msg.content));
        }

        setStatus("");
        await loadChatsSelectionOnly();
    }

    async function loadChatsSelectionOnly() {
        const response = await fetch("/api/chats", { headers: authHeaders() });
        if (!response.ok) return;
        const chats = await response.json();

        chatList.querySelectorAll(".chat-item").forEach(button => {
            const chatId = Number(button.dataset.chatId);
            const wrap = button.closest(".chat-item-wrap");
            if (chatId === currentChatId) {
                button.classList.add("selected");
                button.setAttribute("aria-current", "true");
                wrap?.classList.add("selected");
            } else {
                button.classList.remove("selected");
                button.setAttribute("aria-current", "false");
                wrap?.classList.remove("selected");
            }
        });
    }

    async function createChat() {
        const response = await fetch("/api/create_chat", {
            method: "POST",
            headers: authHeaders(),
        });

        if (!response.ok) {
            setStatus("Could not create chat.", "error");
            return;
        }

        const data = await response.json();
        currentChatId = data.chat_id;
        await loadChats();
        await selectChat(currentChatId);
        chatInput.focus();
    }

    async function deleteChatById(chatId) {
        if (!chatId) return;

        const confirmed = window.confirm("Delete this chat and all its messages?");
        if (!confirmed) return;

        const response = await fetch(`/api/chats/${chatId}`, {
            method: "DELETE",
            headers: authHeaders(),
        });

        if (!response.ok) {
            setStatus("Could not delete chat.", "error");
            return;
        }

        if (currentChatId === chatId) {
            currentChatId = null;
            chatTitleInput.value = "";
            chatTitleHeading.textContent = "No chat selected";
        }

        await loadChats();
        setStatus("Chat deleted.", "success");
    }

    async function deleteCurrentChat() {
        await deleteChatById(currentChatId);
    }

    async function renameChatById(chatId, currentTitle) {
        if (!chatId) return;

        const title = window.prompt("Rename chat", currentTitle || "New chat");
        if (title === null) return;

        const cleanTitle = title.trim();
        if (!cleanTitle) {
            setStatus("Chat title cannot be empty.", "error");
            return;
        }

        const response = await fetch(`/api/chats/${chatId}/title`, {
            method: "PATCH",
            headers: jsonHeaders(),
            body: JSON.stringify({ title: cleanTitle }),
        });

        const data = await readJsonSafely(response);
        if (!response.ok) {
            setStatus(errorText(data, "Could not rename chat."), "error");
            return;
        }

        if (currentChatId === chatId) {
            chatTitleInput.value = data.title || cleanTitle;
            chatTitleHeading.textContent = data.title || cleanTitle;
        }

        setStatus("Chat renamed.", "success");
        await loadChats();
    }

    async function renameCurrentChat() {
        await renameChatById(currentChatId, chatTitleInput.value);
    }

    async function sendMessage(event) {
        event.preventDefault();
        if (!currentChatId) {
            setStatus("Create or select a chat first.", "error");
            return;
        }

        const text = chatInput.value.trim();
        if (!text) return;

        chatInput.value = "";
        chatMessages.querySelector(".empty-state")?.remove();
        appendMessage("user", text);
        const thinking = createThinkingBubble();

        sendBtn.disabled = true;
        chatInput.disabled = true;
        setStatus("Waiting for LM Studio response...");

        try {
            const response = await fetch(`/api/chats/${currentChatId}/send`, {
                method: "POST",
                headers: jsonHeaders(),
                body: JSON.stringify({ message: text }),
            });

            const data = await readJsonSafely(response);
            if (!response.ok) {
                thinking.stop();
                thinking.element.textContent = "Error: " + errorText(data, "Request failed.");
                setStatus(errorText(data, "Request failed."), "error");
                return;
            }

            thinking.stop();
            thinking.element.classList.remove("thinking-bubble");
            thinking.element.innerHTML = safeMarkdown(data.assistant);
            chatTitleInput.value = data.chat_title || chatTitleInput.value;
            chatTitleHeading.textContent = data.chat_title || chatTitleHeading.textContent;
            setStatus("");
            await loadChats();
        } catch (error) {
            thinking.stop();
            thinking.element.textContent = "Network error: " + error;
            setStatus("Network error. Check the backend and LM Studio.", "error");
        } finally {
            sendBtn.disabled = false;
            chatInput.disabled = false;
            chatInput.focus();
        }
    }

    document.getElementById("logoutBtn").addEventListener("click", () => {
        localStorage.removeItem("token");
        window.location.href = "/";
    });

    sidebarToggleBtn.addEventListener("click", toggleSidebar);
    sidebarCloseBtn.addEventListener("click", closeSidebar);
    sidebarBackdrop.addEventListener("click", closeSidebar);

    newChatBtn.addEventListener("click", createChat);
    deleteChatBtn.addEventListener("click", deleteCurrentChat);
    renameChatBtn.addEventListener("click", renameCurrentChat);
    chatForm.addEventListener("submit", sendMessage);
    document.addEventListener("click", closeAllChatMenus);
    window.addEventListener("resize", closeAllChatMenus);
    window.addEventListener("scroll", closeAllChatMenus, true);

    document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
            closeAllChatMenus();
            if (document.body.classList.contains("sidebar-open")) closeSidebar();
        }
    });

    chatInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            chatForm.requestSubmit();
        }
    });

    window.addEventListener("resize", () => {
        if (!isSmallScreen()) {
            document.body.classList.remove("sidebar-open");
            sidebarBackdrop.classList.add("hidden");
        }
    });

    (async () => {
        if (isSmallScreen()) {
            document.body.classList.remove("sidebar-open");
            sidebarToggleBtn.setAttribute("aria-expanded", "false");
        }
        await loadUser();
        await loadChats();
    })();
});
