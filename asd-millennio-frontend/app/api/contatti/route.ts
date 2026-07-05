import { NextResponse } from "next/server";
import { siteConfig } from "@/lib/site";

/**
 * Endpoint del form di contatto.
 * Invia un'email all'associazione tramite Resend (server-side).
 * Se RESEND_API_KEY non è configurata, registra il messaggio e degrada in modo
 * controllato (l'utente riceve l'invito a usare email/telefono diretti).
 *
 * Sicurezza: validazione server-side + honeypot anti-bot. Le chiavi restano
 * server-side (mai esposte al client).
 */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(req: Request) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "BAD_REQUEST" }, { status: 400 });
  }

  // Honeypot: se valorizzato è un bot → fingiamo successo senza fare nulla.
  if (typeof body._hp === "string" && body._hp.trim() !== "") {
    return NextResponse.json({ ok: true });
  }

  const nome = String(body.nome ?? "").trim();
  const email = String(body.email ?? "").trim();
  const telefono = String(body.telefono ?? "").trim();
  const messaggio = String(body.messaggio ?? "").trim();

  const fieldErrors: Record<string, string> = {};
  if (nome.length < 2) fieldErrors.nome = "Inserisci il tuo nome.";
  if (!EMAIL_RE.test(email)) fieldErrors.email = "Inserisci un'email valida.";
  if (messaggio.length < 10) fieldErrors.messaggio = "Scrivi un messaggio (almeno 10 caratteri).";
  if (Object.keys(fieldErrors).length > 0) {
    return NextResponse.json({ error: "VALIDATION", fieldErrors }, { status: 422 });
  }

  const apiKey = process.env.RESEND_API_KEY;
  const to = siteConfig.contact.email;
  const from = process.env.EMAIL_FROM || "onboarding@resend.dev";

  // Degradazione controllata: senza chiave non possiamo inviare.
  if (!apiKey || !to) {
    console.warn("[contatti] RESEND non configurato — messaggio non inviato:", { nome, email });
    return NextResponse.json({ ok: false, delivered: false }, { status: 200 });
  }

  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: `Sito Millennio <${from}>`,
        to: [to],
        reply_to: email,
        subject: `Nuovo messaggio dal sito — ${nome}`,
        text:
          `Nuovo contatto dal sito ${siteConfig.url}\n\n` +
          `Nome: ${nome}\n` +
          `Email: ${email}\n` +
          `Telefono: ${telefono || "—"}\n\n` +
          `Messaggio:\n${messaggio}\n`,
      }),
    });

    if (!res.ok) {
      const detail = await res.text();
      console.error("[contatti] Errore Resend:", res.status, detail);
      return NextResponse.json({ error: "SEND_FAILED" }, { status: 502 });
    }

    return NextResponse.json({ ok: true, delivered: true });
  } catch (err) {
    console.error("[contatti] Errore di rete verso Resend:", err);
    return NextResponse.json({ error: "SEND_FAILED" }, { status: 502 });
  }
}
