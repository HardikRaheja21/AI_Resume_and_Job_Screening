// const API = "http://127.0.0.1:8000";

// // REGISTER
// document.getElementById("registerForm")?.addEventListener("submit", async (e) => {
//     e.preventDefault();

//     const email = document.getElementById("email").value;
//     const password = document.getElementById("password").value;

//     const res = await fetch(`${API}/auth/register`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ email, password })
//     });

//     alert("Registration Successful!");
// });

// // LOGIN
// document.getElementById("loginForm")?.addEventListener("submit", async (e) => {
//     e.preventDefault();

//     const email = document.getElementById("email").value;
//     const password = document.getElementById("password").value;

//     const res = await fetch(`${API}/auth/login`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ email, password })
//     });

//     const data = await res.json();
//     localStorage.setItem("token", data.access_token);
//     alert("Login successful!");
// });

// // UPLOAD RESUME
// document.getElementById("uploadForm")?.addEventListener("submit", async (e) => {
//     e.preventDefault();
    
//     const token = localStorage.getItem("token");
//     const file = document.getElementById("file").files[0];

//     const formData = new FormData();
//     formData.append("file", file);

//     const res = await fetch(`${API}/resumes/upload`, {
//         method: "POST",
//         headers: { "Authorization": "Bearer " + token },
//         body: formData
//     });

//     const data = await res.json();

//     document.getElementById("result").innerText = JSON.stringify(data, null, 2);
// });
// const API = "http://127.0.0.1:8000";


// // REGISTER
// async function register() {
//     const email = document.getElementById("email").value;
//     const password = document.getElementById("password").value;

//     const res = await fetch(`${API}/auth/register`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ email, password })
//     });

//     if (res.ok) {
//         alert("Registration successful!");
//         window.location.href = "login.html";
//     } else {
//         alert("Registration failed!");
//     }
// }


// // LOGIN
// async function login() {
//     const email = document.getElementById("email").value;
//     const password = document.getElementById("password").value;

//     const res = await fetch(`${API}/auth/login`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ email, password })
//     });

//     const data = await res.json();
    
//     if (res.ok) {
//         localStorage.setItem("token", data.access_token);
//         alert("Login successful!");
//         window.location.href = "upload.html";
//     } else {
//         alert("Login failed!");
//     }
// }



// // UPLOAD RESUME + JOB DESCRIPTION
// async function uploadResume() {
//     const token = localStorage.getItem("token");
//     const file = document.getElementById("file").files[0];
//     const jdText = document.getElementById("jd").value;

//     if (!file) return alert("Upload a resume file!");

//     const formData = new FormData();
//     formData.append("file", file);
//     formData.append("jd", jdText);

//     const res = await fetch(`${API}/resumes/upload`, {
//         method: "POST",
//         headers: { "Authorization": "Bearer " + token },
//         body: formData
//     });

//     const data = await res.json();
//     document.getElementById("result").innerText = JSON.stringify(data, null, 2);
// }



const API = "http://127.0.0.1:8000";


// ----------------------- REGISTER -----------------------
async function register() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    const res = await fetch(`${API}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    });

    if (res.ok) {
        alert("Registration successful!");
        window.location.href = "login.html";
    } else {
        const data = await res.json();
        alert(data.detail || "Registration failed!");
    }
}



// ----------------------- LOGIN (FIXED) -----------------------
async function login() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    // OAuth2PasswordRequestForm REQUIRES formData (NOT JSON)
    const formData = new FormData();
    formData.append("username", email);   // Email goes as username
    formData.append("password", password);

    const res = await fetch(`${API}/auth/login`, {
        method: "POST",
        body: formData   // Do NOT add headers
    });

    const data = await res.json();

    if (res.ok) {
        localStorage.setItem("token", data.access_token);
        alert("Login successful!");
        window.location.href = "upload.html";
    } else {
        alert(data.detail || "Login failed!");
    }
}



// ----------------------- UPLOAD RESUME -----------------------
async function uploadResume() {
    const token = localStorage.getItem("token");
    const file = document.getElementById("file").files[0];
    const jdText = document.getElementById("jd").value;

    if (!file) return alert("Upload a resume file!");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("jd", jdText);

    const res = await fetch(`${API}/resumes/upload`, {
        method: "POST",
        headers: {
            "Authorization": "Bearer " + token
        },
        body: formData
    });

    const data = await res.json();
    document.getElementById("result").innerText =
        JSON.stringify(data, null, 2);
}
