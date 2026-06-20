import Keycloak from "keycloak-js";

let keycloakInstance: Keycloak | null = null;
// Flag modulo-level: sopravvive ai remount di React StrictMode
let _initPromise: Promise<boolean> | null = null;

/**
 * Restituisce sempre la stessa istanza Keycloak (singleton).
 * L'inizializzazione (kc.init) è responsabilità del layout che la usa.
 */
export function getKeycloak(): Keycloak {
  if (!keycloakInstance) {
    keycloakInstance = new Keycloak({
      url: process.env.NEXT_PUBLIC_KEYCLOAK_URL!,
      realm: process.env.NEXT_PUBLIC_KEYCLOAK_REALM!,
      clientId: process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID!,
    });
  }
  return keycloakInstance;
}

/**
 * Inizializza Keycloak una sola volta — sicuro con React StrictMode.
 * Usa un flag a livello di modulo che sopravvive ai remount del componente.
 */
export function initKeycloakOnce(
  options: Parameters<Keycloak["init"]>[0]
): Promise<boolean> {
  if (_initPromise) return _initPromise;
  _initPromise = getKeycloak().init(options);
  return _initPromise;
}

export function hasRole(keycloak: Keycloak, role: string): boolean {
  return keycloak.hasRealmRole(role);
}

export function isStaff(keycloak: Keycloak): boolean {
  return hasRole(keycloak, "staff") || hasRole(keycloak, "dirigenza");
}

export function isDirigenza(keycloak: Keycloak): boolean {
  return hasRole(keycloak, "dirigenza");
}

export function isSocio(keycloak: Keycloak): boolean {
  return (
    hasRole(keycloak, "socio") ||
    hasRole(keycloak, "staff") ||
    hasRole(keycloak, "dirigenza") ||
    hasRole(keycloak, "allenatore")
  );
}
