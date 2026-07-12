import { Section, SectionHeading } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { SocialIcons } from "@/components/site/SocialIcons";
import { FacebookTimeline } from "./FacebookTimeline";
import { FollowCard } from "./FollowCard";
import { socialProvider } from "@/lib/social";
import { siteConfig } from "@/lib/site";

/**
 * Sezione social della home. Mostra i feed live supportati dal provider attivo
 * (vedi lib/social.ts) e, per gli altri canali, card "Segui" sostituibili.
 */
export function SocialWall() {
  const isLive = (p: "facebook" | "instagram" | "tiktok") => socialProvider.liveFeeds.includes(p);

  return (
    <Section id="social" muted>
      <SectionHeading
        eyebrow="Community"
        title="Seguici sui social"
        subtitle="Gli ultimi aggiornamenti, foto e video dai nostri canali ufficiali."
      />

      <div className="mt-12 grid gap-6 lg:grid-cols-2">
        <Reveal>
          {isLive("facebook") ? (
            <FacebookTimeline pageUrl={siteConfig.social.facebook} />
          ) : (
            <FollowCard platform="facebook" />
          )}
        </Reveal>

        {/* Instagram e TikTok: card "Segui" finché non si attiva il provider "api". */}
        <Reveal delay={120} className="flex flex-col gap-6">
          <FollowCard platform="instagram" />
          <FollowCard platform="tiktok" />
        </Reveal>
      </div>

      <div className="mt-10 flex justify-center">
        <SocialIcons className="flex gap-3" tone="light" />
      </div>
    </Section>
  );
}
