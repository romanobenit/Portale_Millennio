import { siteSocialItems } from "@/components/site/SocialIcons";
import { socialHandles, type SocialPlatform } from "@/lib/social";

/**
 * Card "Segui" per i canali senza feed live nel provider attuale.
 * Sostituibile con un componente di feed quando si passa al provider "api".
 */
export function FollowCard({ platform }: { platform: SocialPlatform }) {
  const item = siteSocialItems.find((s) => s.key === platform);
  if (!item) return null;

  const { label, href, Icon } = item;
  const handle = socialHandles[platform];

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${label}: @${handle} (apre in una nuova scheda)`}
      className="group flex h-full items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
    >
      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
        <Icon className="h-6 w-6" />
      </span>
      <span className="min-w-0">
        <span className="block font-semibold text-slate-900">{label}</span>
        <span className="block truncate text-sm text-slate-500">@{handle}</span>
      </span>
      <span
        className="ml-auto text-brand-600 transition-transform group-hover:translate-x-1"
        aria-hidden="true"
      >
        ↗
      </span>
    </a>
  );
}
