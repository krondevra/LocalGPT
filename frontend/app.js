window.addEventListener("DOMContentLoaded", () => {
    const chatList = document.getElementById("chatList");
    const chatMessages = document.getElementById("chatMessages");
    const chatInput = document.getElementById("chatInput");
    const sendBtn = document.getElementById("sendBtn");
    const newChatBtn = document.getElementById("newChatBtn");
    const deleteChatBtn = document.getElementById("deleteChatBtn");

    async function loadUser() {
        const token = localStorage.getItem("token");
        if (!token) {
            window.location.href = "/";
            return;
        }

        try {
            const res = await fetch("/auth/me", {
                headers: { "Authorization": "Bearer " + token }
            });

            if (!res.ok) {
                window.location.href = "/";
                return;
            }

            const data = await res.json();
            document.getElementById("userDisplay").textContent = "Logged in as " + data.name;
        } catch (e) {
            window.location.href = "/";
        }
    }

    document.getElementById("logoutBtn").addEventListener("click", () => {
        localStorage.removeItem("token");
        window.location.href = "/";
    });

    let currentChatId = null;

    async function loadChats() {
        const res = await fetch("/api/chats", {
            headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
        });
        if (!res.ok) return;

        const chats = await res.json();
        chatList.innerHTML = "";

        chats.forEach(c => {
            const li = document.createElement("li");
            li.className = "chat-item" + (c.id === currentChatId ? " selected" : "");
            li.textContent = "Chat " + c.id;
            li.onclick = () => selectChat(c.id);
            chatList.appendChild(li);
        });

        if (!currentChatId && chats.length > 0) {
            await selectChat(chats[0].id);
        }
    }

    async function selectChat(id) {
        currentChatId = id;

        const res = await fetch(`/api/chats/${id}/messages`, {
            headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
        });

        if (!res.ok) return;

        const messages = await res.json();
        chatMessages.innerHTML = "";

        messages.forEach(m => {
            const div = document.createElement("div");
            div.className = "msg " + (m.role === "user" ? "msg-user" : "msg-bot");
            div.innerHTML = marked.parse(m.content);
            chatMessages.appendChild(div);
        });

        await loadChats(); // refresh selection highlight
    }

    newChatBtn.onclick = async () => {
        const res = await fetch("/api/create_chat", {
            method: "POST",
            headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
        });

        if (!res.ok) return;

        const data = await res.json();
        currentChatId = data.chat_id;

        await loadChats();
        await selectChat(currentChatId);
    };

    deleteChatBtn.onclick = async () => {
        if (!currentChatId) return;

        const res = await fetch(`/api/delete_chat/id?chat_id=${currentChatId}`, {
            method: "DELETE",
            headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
        });

        if (!res.ok) return;

        currentChatId = null;
        chatMessages.innerHTML = "";
        await loadChats();
    };

sendBtn.onclick = async () => {
    if (!currentChatId) return;

    const text = chatInput.value.trim();
    if (!text) return;

    chatInput.value = "";

    // show user message immediately
    const u = document.createElement("div");
    u.className = "msg msg-user";
    u.textContent = text;
    chatMessages.appendChild(u);

    // show "typing..." placeholder
    const typing = document.createElement("div");
    typing.className = "msg msg-bot";
    typing.textContent = "Typing...";
    chatMessages.appendChild(typing);

    // lock UI while waiting
    sendBtn.disabled = true;
    chatInput.disabled = true;

    try {
        const res = await fetch(`/api/chats/${currentChatId}/send?message=` + encodeURIComponent(text), {
            method: "POST",
            headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
        });

        if (!res.ok) {
            const t = await res.text();
            typing.textContent = "Error: " + t;
            return;
        }

        const data = await res.json();
        typing.innerHTML = marked.parse(data.assistant);


        // optional: autoscroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;

    } catch (e) {
        typing.textContent = "Network error: " + e;
    } finally {
        sendBtn.disabled = false;
        chatInput.disabled = false;
        chatInput.focus();
    }
};

    (async () => {
        await loadUser();
        await loadChats();
    })();
});
