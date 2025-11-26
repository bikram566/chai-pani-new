const API_URL = 'http://localhost:8001/api';

// Auth State
let currentUser = null;
const token = localStorage.getItem('token');

// API Client
async function fetchAPI(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers
    });

    if (response.status === 401) {
        logout();
        return null;
    }

    return response;
}

// Auth Functions
async function login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        window.location.href = '/dashboard.html';
    } catch (error) {
        alert(error.message);
    }
}

async function register(username, password, email, role) {
    try {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, email, role })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Registration failed');
        }

        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        window.location.href = '/dashboard.html';
    } catch (error) {
        alert(error.message);
    }
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = '/index.html';
}

async function checkAuth() {
    if (!token) {
        window.location.href = '/index.html';
        return;
    }

    const response = await fetchAPI('/auth/me');
    if (!response || !response.ok) {
        logout();
        return;
    }

    currentUser = await response.json();
    updateUIForUser();
}

function updateUIForUser() {
    const userDisplay = document.getElementById('user-display');
    if (userDisplay && currentUser) {
        userDisplay.textContent = `${currentUser.username} (${currentUser.role})`;
    }

    // Hide/Show elements based on role
    document.querySelectorAll('[data-role]').forEach(el => {
        const roles = el.dataset.role.split(',');
        if (!roles.includes(currentUser.role) && currentUser.role !== 'admin') {
            el.style.display = 'none';
        }
    });
}

// Helper to format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amount);
}
