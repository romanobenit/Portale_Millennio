/**
 * Astrazione del feed social — pensata per essere facilmente sostituibile.
 *
 * Stato attuale: provider "embed".
 *  - Facebook → feed live tramite Page Plugin ufficiale (nessun token richiesto).
 *  - Instagram / TikTok → card "Segui": il loro feed live richiede l'accesso alle
 *    API ufficiali (Instagram Graph API con account business + app review;
 *    TikTok Display API / embed.js), non disponibili senza credenziali dedicate.
 *
 * Come passare ai feed live (provider "api"):
 *  1. implementare i componenti di feed per le piattaforme desiderate;
 *  2. impostare qui `socialProvider = { id: "api", liveFeeds: [...] }`;
 *  3. il resto della UI (SocialWall) si adatta automaticamente.
 */

export type SocialPlatform = "facebook" | "instagram" | "tiktok";

export interface SocialProvider {
  id: "embed" | "api";
  /** Piattaforme che il provider attuale mostra come feed live. */
  liveFeeds: SocialPlatform[];
}

export const socialProvider: SocialProvider = {
  id: "embed",
  liveFeeds: ["facebook"],
};

/** Handle pubblici per le card "Segui". */
export const socialHandles: Record<SocialPlatform, string> = {
  facebook: "Millennioasd",
  instagram: "millennioasd2009",
  tiktok: "domenicoromano153",
};
