import type { MetadataRoute } from "next";
import { siteConfig } from "@/lib/site";

/** robots.txt: indicizza il sito pubblico, esclude le aree riservate e l'API. */
export default function robots(): MetadataRoute.Robots {
  const base = siteConfig.url.replace(/\/$/, "");
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/dashboard", "/dirigenza", "/staff", "/api"],
    },
    sitemap: `${base}/sitemap.xml`,
  };
}
