import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const http = axios.create({
  baseURL: BASE_URL,
});

// Attach the JWT (as issued by POST /auth/login) to every request once
// the user is signed in. Token is kept in localStorage under this key.
export const TOKEN_KEY = "vulnara_access_token";

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Normalize FastAPI's `{ detail: "..." }` / `{ error: { message } }` error
// shapes into a single readable string for the UI layer.
http.interceptors.response.use(
  (res) => res,
  (err) => {
    const data = err?.response?.data;
    const message =
      data?.error?.message ||
      (typeof data?.detail === "string" ? data.detail : null) ||
      err.message ||
      "Request failed";
    return Promise.reject(new Error(message));
  }
);

export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000";
