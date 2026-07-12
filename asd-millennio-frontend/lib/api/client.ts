import axios, { type AxiosInstance } from "axios";
import { getKeycloak } from "@/lib/auth/keycloak";

// IMPORTANTE: questo modulo è esclusivamente browser-side.
// Non importarlo in Server Components o route handlers.
// Il token è browser-scoped: nessun rischio di cross-request leak.
// Non usiamo throw perché Next.js esegue i moduli anche durante il prerendering statico di build.
if (typeof window === "undefined") {
  console.warn("[client.ts] apiClient importato in ambiente SSR — assicurarsi che le chiamate avvengano solo lato client.");
}

// Fallback statico (usato solo se Keycloak non è ancora inizializzato).
let _token: string | null = null;

export function setAuthToken(token: string | null): void {
  _token = token;
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: { "Content-Type": "application/json" },
});

// Prima di OGNI richiesta rinfresca il token Keycloak se sta per scadere.
// L'access token ha vita breve (~5 min): senza questo, dopo la scadenza tutte
// le chiamate autenticate tornano 401. updateToken(30) è un no-op se il token
// è ancora valido per più di 30 secondi.
apiClient.interceptors.request.use(async (config) => {
  try {
    const kc = getKeycloak();
    if (kc.authenticated) {
      await kc.updateToken(30);
      if (kc.token) {
        config.headers.Authorization = `Bearer ${kc.token}`;
        return config;
      }
    }
  } catch {
    // refresh fallito (es. refresh token scaduto): si prosegue col fallback statico
  }
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
