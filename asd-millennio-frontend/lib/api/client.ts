import axios, { type AxiosInstance } from "axios";

// IMPORTANTE: questo modulo è esclusivamente browser-side.
// Non importarlo in Server Components o route handlers.
// Il token è browser-scoped (settato solo in useEffect): nessun rischio di cross-request leak.
// Non usiamo throw perché Next.js esegue i moduli anche durante il prerendering statico di build:
// un throw romperebbe la build pur non causando un runtime issue reale.
if (typeof window === "undefined") {
  console.warn("[client.ts] apiClient importato in ambiente SSR — assicurarsi che le chiamate avvengano solo lato client.");
}

let _token: string | null = null;

export function setAuthToken(token: string | null): void {
  _token = token;
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  if (_token) {
    config.headers.Authorization = `Bearer ${_token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg =
      err.response?.data?.message ||
      err.response?.data?.detail ||
      "Errore di rete";
    return Promise.reject(new Error(msg));
  }
);
