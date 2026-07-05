"use client";

import { useState } from "react";

/**
 * Carica un widget esterno solo dopo consenso esplicito dell'utente (click-to-load).
 * Evita di impostare cookie di terze parti e di scaricare script al primo caricamento
 * della pagina (privacy + performance). Finché non si clicca, mostra un segnaposto
 * con il link diretto al canale.
 */
export function EmbedConsent({
  platform,
  url,
  children,
}: {
  platform: string;
  url: string;
  children: React.ReactNode;
}) {
  const [loaded, setLoaded] = useState(false);

  if (loaded) return <>{children}</>;

  return (
    <div className="flex min-h-[320px] flex-col items-center justify-center gap-4 rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <p className="max-w-xs text-sm text-slate-600">
        Per mostrare gli ultimi contenuti da <strong>{platform}</strong> viene caricato un widget
        esterno, che può impostare cookie di terze parti.
      </p>
      <button
        type="button"
        onClick={() => setLoaded(true)}
        className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
      >
        Mostra i contenuti di {platform}
      </button>
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm font-medium text-brand-600 hover:underline"
      >
        oppure apri {platform} ↗
      </a>
    </div>
  );
}
