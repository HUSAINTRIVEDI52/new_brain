import api from './api';

const TOKEN_KEY = 'access_token';
const EMAIL_KEY = 'user_email';

export const authService = {
    async register(email, password, name) {
        try {
            const data = await api.post('/auth/register', { email, password, name });
            if (data.access_token) {
                localStorage.setItem(TOKEN_KEY, data.access_token);
                localStorage.setItem(EMAIL_KEY, data.email);
            }
            return data;
        } catch (error) {
            this.logout(); // Ensure no partial state
            throw error;
        }
    },

    async login(email, password) {
        try {
            const data = await api.post('/auth/login', { email, password });
            if (data.access_token) {
                localStorage.setItem(TOKEN_KEY, data.access_token);
                localStorage.setItem(EMAIL_KEY, data.email);
            }
            return data;
        } catch (error) {
            this.logout(); // Ensure no partial state
            throw error;
        }
    },

    logout() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(EMAIL_KEY);
        // Optional: session-level resets
    },

    isAuthenticated() {
        return !!localStorage.getItem(TOKEN_KEY);
    },

    getUserEmail() {
        return localStorage.getItem(EMAIL_KEY);
    }
};
