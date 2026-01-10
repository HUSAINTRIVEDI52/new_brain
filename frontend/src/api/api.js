import axios from 'axios';
import axiosRetry from 'axios-retry';

const API_URL = import.meta.env.NEXT_PUBLIC_API_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000';
const AUTH_KEY = import.meta.env.NEXT_PUBLIC_AUTH_KEY;

const api = axios.create({
    baseURL: API_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
        'X-Auth-Key': AUTH_KEY, // Injecting the public auth key
    },
});

// Setup auto-retries for network errors
axiosRetry(api, {
    retries: 3,
    retryDelay: axiosRetry.exponentialDelay,
    retryCondition: (error) => {
        return axiosRetry.isNetworkOrIdempotentRequestError(error) || error.code === 'ECONNABORTED';
    }
});

// Request Interceptor: Inject JWT
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response Interceptor: Global Error Handling
api.interceptors.response.use(
    (response) => {
        // Log successful requests in development
        if (import.meta.env.DEV) {
            console.log(`[API Search] ${response.config.method.toUpperCase()} ${response.config.url}:`, response.data);
        }
        return response.data;
    },
    (error) => {
        const status = error.response ? error.response.status : null;

        if (status === 401) {
            console.warn('Unauthorized: Clearing session.');
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_email');
            // Force reload to trigger auth redirection if necessary
            window.location.reload();
        }

        const message = error.response?.data?.detail || error.message || 'An unexpected error occurred';
        console.error(`API Error [${error.config?.url}]:`, message);

        return Promise.reject(error);
    }
);

export default api;
