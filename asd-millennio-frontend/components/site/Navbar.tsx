"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import { mainNav, portalLinks } from "@/lib/site";
import { Logo } from "./Logo";
import { Container } from "./Container";

/**
 * Header pubblico sticky, responsive e accessibile.
 * - Desktop: navigazione inline + CTA "Area soci".
 * - Mobile: menu a comparsa (hamburger) con gestione focus/aria.
 */
export function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // Chiudi il menu mobile a ogni cambio di rotta.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Blocca lo scroll del body quando il menu mobile è aperto.
  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/70 bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/70">
      <Container className="flex h-20 items-center justify-between gap-3">
        <Link href="/" aria-label="Millennio ASD — home" className="shrink-0">
          <Logo />
        </Link>

        {/* Navigazione desktop */}
        <nav aria-label="Principale" className="hidden lg:block">
          <ul className="flex items-center gap-1">
            {mainNav.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={isActive(item.href) ? "page" : undefined}
                  className={clsx(
                    "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive(item.href)
                      ? "text-brand-700"
                      : "text-slate-700 hover:text-brand-700",
                  )}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <Link
            href={portalLinks.areaSoci}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
          >
            Area soci
          </Link>
        </div>

        {/* Toggle mobile */}
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md p-2 text-slate-700 lg:hidden focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-600"
          aria-expanded={open}
          aria-controls="mobile-menu"
          aria-label={open ? "Chiudi menu" : "Apri menu"}
          onClick={() => setOpen((v) => !v)}
        >
          <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
            {open ? (
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5M3.75 17.25h16.5" />
            )}
          </svg>
        </button>
      </Container>

      {/* Pannello mobile */}
      {open && (
        <nav id="mobile-menu" aria-label="Principale (mobile)" className="lg:hidden">
          <Container className="space-y-1 border-t border-slate-200 bg-white py-4">
            {mainNav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive(item.href) ? "page" : undefined}
                className={clsx(
                  "block rounded-lg px-3 py-2.5 text-base font-medium",
                  isActive(item.href)
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-800 hover:bg-slate-50",
                )}
              >
                {item.label}
              </Link>
            ))}
            <Link
              href={portalLinks.areaSoci}
              className="mt-2 block rounded-lg bg-brand-600 px-3 py-2.5 text-center text-base font-semibold text-white"
            >
              Area soci
            </Link>
          </Container>
        </nav>
      )}
    </header>
  );
}
