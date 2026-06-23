async function loadUser() {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "/";
        return;
    }

    try {
        const res = await fetch("/auth/me", {
            headers: {
                "Authorization": "Bearer " + token
            }
        });

        if (!res.ok) {
            window.location.href = "/";
            return;
        }

        const data = await res.json();
        const el = document.getElementById("userDisplay");
        el.textContent = "Logged in as " + data.name;

    } catch (e) {
        window.location.href = "/";
    }
}

loadUser();

document.getElementById("logoutBtn").addEventListener("click", function () {
    localStorage.removeItem("token");
    window.location.href = "/";
});
