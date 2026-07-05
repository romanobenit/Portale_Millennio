import type { Metadata } from "next";
import { siteConfig } from "@/lib/site";
import { Hero } from "@/components/site/home/Hero";
import { ChiSiamo } from "@/components/site/home/ChiSiamo";
import { Attivita } from "@/components/site/home/Attivita";
import { PercheSceglierci } from "@/components/site/home/PercheSceglierci";
import { Gallery } from "@/components/site/home/Gallery";
import { SocialWall } from "@/components/site/social/SocialWall";
import { Cta } from "@/components/site/home/Cta";

export const metadata: Metadata = {
  title: "Polisportiva a Cercola dal 2009",
  description: siteConfig.description,
  alternates: { canonical: "/" },
};

export default function HomePage() {
  return (
    <>
      <Hero />
      <ChiSiamo />
      <Attivita />
      <PercheSceglierci />
      <Gallery />
      <SocialWall />
      <Cta />
    </>
  );
}
