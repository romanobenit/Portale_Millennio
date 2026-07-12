import { clsx } from "clsx";

/**
 * Logo ufficiale Millennio (marchio "a picchi"), servito da `public/logo.svg`.
 * Il file è l'SVG originale dell'associazione, ripulito dall'artboard bianco e
 * con il viewBox ritagliato alla fascia del marchio.
 */
export function Logo({ className }: { className?: string }) {
  return (
    // SVG locale, statico e fidato: <img> è sufficiente (niente ottimizzazione next/image).
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/logo.svg"
      alt="Millennio ASD"
      className={clsx("h-10 w-auto sm:h-12 lg:h-14", className)}
      width={250}
      height={35}
    />
  );
}
