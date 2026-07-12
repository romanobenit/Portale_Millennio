import type { MetadataRoute } from "next";
import { siteConfig, discipline } from "@/lib/site";

/**
 * Sitemap del sito pubblico. Cresce man mano che vengono aggiunte le pagine
 * negli step successivi (Chi siamo, Attività, Corsi, Eventi, News, Contatti).
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteConfig.url.replace(/\/$/, "");
  const routes = [
    "/",
    "/chi-siamo",
    "/attivita",
    ...discipline.map((d) => `/attivita/${d.slug}`),
    "/corsi",
    "/eventi",
    "/news",
    "/contatti",
  ]; // aggiornato a ogni nuova pagina pubblica
  const now = new Date();

  return routes.map((path) => ({
    url: `${base}${path}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: path === "/" ? 1 : 0.7,
  }));
}
