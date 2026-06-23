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

document.getElementById("loginSubmit").addEventListener("click", function(){
    loginMessage.textContent = "placeholder";
});

document.getElementById("signupSubmit").addEventListener("click", function(){
    signupMessage.textContent = "placeholder";
});

showLogin();
