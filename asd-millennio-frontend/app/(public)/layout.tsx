import { type ReactNode } from "react";
import { Navbar } from "@/components/site/Navbar";
import { Footer } from "@/components/site/Footer";

/**
 * Layout del sito pubblico (marketing): header + contenuto + footer condivisi.
 * Separato dall'area riservata (/dashboard) che ha un proprio layout autenticato.
 */
export default function PublicLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-white">
      <Navbar />
      <main id="main" className="flex-1">
        {children}
      </main>
      <Footer />
    </div>
  );
}
