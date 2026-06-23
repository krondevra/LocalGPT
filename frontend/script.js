const loginBox = document.getElementById("loginBox");
const signupBox = document.getElementById("signupBox");
const loginMessage = document.getElementById("loginMessage");
const signupMessage = document.getElementById("signupMessage");

function clearMessages() {
    loginMessage.textContent = "";
    signupMessage.textContent = "";
}

function getErrorMessage(data, fallback) {
    if (data && typeof data.detail === "string") return data.detail;
    return fallback;
}

function showLogin() {
    clearMessages();
    signupBox.classList.add("hidden");
    loginBox.classList.remove("hidden");
    document.getElementById("loginUsername").focus();
}

function showSignup() {
    clearMessages();
    loginBox.classList.add("hidden");
    signupBox.classList.remove("hidden");
    document.getElementById("signupUsername").focus();
}

async function readJsonSafely(response) {
    try {
        return await response.json();
    } catch (_) {
        return null;
    }
}

async function login() {
    clearMessages();

    const username = document.getElementById("loginUsername").value.trim();
    const password = document.getElementById("loginPassword").value;

    if (!username || !password) {
        loginMessage.textContent = "Enter username and password.";
        return;
    }

    const form = new FormData();
    form.append("username", username);
    form.append("password", password);

    try {
        const response = await fetch("/auth/login", { method: "POST", body: form });
        const data = await readJsonSafely(response);

        if (!response.ok) {
            loginMessage.textContent = getErrorMessage(data, "Login failed.");
            return;
        }

        localStorage.setItem("token", data.access_token);
        window.location.href = "/app";
    } catch (_) {
        loginMessage.textContent = "Network error. Check that the backend is running.";
    }
}

async function signup() {
    clearMessages();

    const username = document.getElementById("signupUsername").value.trim();
    const password = document.getElementById("signupPassword").value;

    if (!username || !password) {
        signupMessage.textContent = "Enter username and password.";
        return;
    }

    const form = new FormData();
    form.append("username", username);
    form.append("password", password);

    try {
        const response = await fetch("/auth/register", { method: "POST", body: form });
        const data = await readJsonSafely(response);

        if (!response.ok) {
            signupMessage.textContent = getErrorMessage(data, "Signup failed.");
            return;
        }

        showLogin();
        document.getElementById("loginUsername").value = username;
        loginMessage.textContent = data.first_user_admin
            ? "Account created. This first account is an admin."
            : "Account created. You can log in now.";
    } catch (_) {
        signupMessage.textContent = "Network error. Check that the backend is running.";
    }
}

document.getElementById("openSignup").addEventListener("click", showSignup);
document.getElementById("openLogin").addEventListener("click", showLogin);
document.getElementById("loginSubmit").addEventListener("click", login);
document.getElementById("signupSubmit").addEventListener("click", signup);

document.addEventListener("keydown", function(event) {
    if (event.key !== "Enter") return;

    if (!loginBox.classList.contains("hidden")) {
        login();
    } else if (!signupBox.classList.contains("hidden")) {
        signup();
    }
});

showLogin();
