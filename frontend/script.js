const loginBox = document.getElementById("loginBox");
const signupBox = document.getElementById("signupBox");

const loginMessage = document.getElementById("loginMessage");
const signupMessage = document.getElementById("signupMessage");

function clearMessages() {
    loginMessage.textContent = "";
    signupMessage.textContent = "";
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

document.getElementById("openSignup").addEventListener("click", function(){
    showSignup();
});

document.getElementById("openLogin").addEventListener("click", function(){
    showLogin();
});

document.getElementById("loginSubmit").addEventListener("click", async function(){
    clearMessages();

    const u = document.getElementById("loginUsername").value.trim();
    const p = document.getElementById("loginPassword").value.trim();

    if (!u || !p) {
        loginMessage.textContent = "Enter username and password.";
        return;
    }

    const form = new FormData();
    form.append("username", u);
    form.append("password", p);

    try {
        const res = await fetch("/auth/login", {
            method: "POST",
            body: form
        });

        if (!res.ok) {
            loginMessage.textContent = "Login failed.";
            return;
        }

        const data = await res.json();
        // save token
        localStorage.setItem("token", data.access_token);

        window.location.href = "/app";
    } catch (e) {
        loginMessage.textContent = "Network error.";
    }
});

document.getElementById("signupSubmit").addEventListener("click", async function(){
    clearMessages();

    const u = document.getElementById("signupUsername").value.trim();
    const p = document.getElementById("signupPassword").value.trim();

    if (!u || !p) {
        signupMessage.textContent = "Enter username and password.";
        return;
    }

    const form = new FormData();
    form.append("username", u);
    form.append("password", p);

    try {
        const res = await fetch("/auth/register", {
            method: "POST",
            body: form
        });

        if (!res.ok) {
            signupMessage.textContent = "Signup failed.";
            return;
        }

        showLogin();
        document.getElementById("loginUsername").value = u;
        loginMessage.textContent = "Account created.";
    } catch (e) {
        signupMessage.textContent = "Network error.";
    }
});

showLogin();
