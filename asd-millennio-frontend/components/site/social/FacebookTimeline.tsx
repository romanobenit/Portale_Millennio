import { EmbedConsent } from "./EmbedConsent";

/**
 * Feed live della pagina Facebook tramite Page Plugin ufficiale (iframe, nessun
 * token né SDK). Caricato solo dopo consenso (vedi EmbedConsent).
 */
export function FacebookTimeline({ pageUrl }: { pageUrl: string }) {
  const src =
    "https://www.facebook.com/plugins/page.php?" +
    new URLSearchParams({
      href: pageUrl,
      tabs: "timeline",
      width: "500",
      height: "560",
      small_header: "false",
      adapt_container_width: "true",
      hide_cover: "false",
      show_facepile: "true",
    }).toString();

  return (
    <EmbedConsent platform="Facebook" url={pageUrl}>
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <iframe
          src={src}
          title="Ultimi post da Facebook — ASD Millennio"
          className="mx-auto block h-[560px] w-full max-w-[500px]"
          style={{ border: "none" }}
          scrolling="no"
          allowFullScreen
          allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
        />
      </div>
    </EmbedConsent>
  );
}
