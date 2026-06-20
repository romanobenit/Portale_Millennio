"use client";

import { type ReactNode } from "react";
import { Toaster } from "react-hot-toast";

// Providers non inizializza Keycloak — lo fa ogni layout protetto.
// Questo evita loop con check-sso iframe e doppia inizializzazione in StrictMode.
export function Providers({ children }: { children: ReactNode }) {
  return (
    <>
      {children}
      <Toaster position="top-right" />
    </>
  );
}
