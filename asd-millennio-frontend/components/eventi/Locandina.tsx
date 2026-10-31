import { clsx } from "clsx";
import { urlLocandina } from "@/lib/api/eventi";

/**
 * Locandina di un evento: l'immagine apre la versione intera in una nuova scheda.
 * `intera` la mostra senza ritagli (evidenza); altrimenti è una miniatura ritagliata.
 */
export function Locandina({
  url,
  titolo,
  intera = false,
  className,
}: {
  url: string;
  titolo?: string | null;
  intera?: boolean;
  className?: string;
}) {
  const src = urlLocandina(url);
  return (
    <a
      href={src}
      target="_blank"
      rel="noopener noreferrer"
      title="Apri la locandina"
      className={clsx("block shrink-0 overflow-hidden", className)}
    >
      {/* Immagine servita dal backend con URL versionato e già ridimensionata: basta <img>. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={titolo ? `Locandina: ${titolo}` : "Locandina dell'evento"}
        loading="lazy"
        className={intera ? "h-auto w-full" : "h-full w-full object-cover object-top"}
      />
    </a>
  );
}
