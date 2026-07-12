"use client";

import { useState } from "react";
import { siteConfig } from "@/lib/site";

type Status = "idle" | "loading" | "success" | "degraded" | "error";

const initial = { nome: "", email: "", telefono: "", messaggio: "", privacy: false };

/** Form di contatto accessibile con validazione, honeypot e invio a /api/contatti. */
export function ContactForm() {
  const [values, setValues] = useState(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<Status>("idle");
  const [hp, setHp] = useState(""); // honeypot

  const set = (k: keyof typeof initial) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setValues((v) => ({ ...v, [k]: e.target.type === "checkbox" ? (e.target as HTMLInputElement).checked : e.target.value }));

  function validate() {
    const err: Record<string, string> = {};
    if (values.nome.trim().length < 2) err.nome = "Inserisci il tuo nome.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) err.email = "Inserisci un'email valida.";
    if (values.messaggio.trim().length < 10) err.messaggio = "Scrivi un messaggio (almeno 10 caratteri).";
    if (!values.privacy) err.privacy = "Devi acconsentire al trattamento dei dati.";
    return err;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const err = validate();
    setErrors(err);
    if (Object.keys(err).length > 0) return;

    setStatus("loading");
    try {
      const res = await fetch("/api/contatti", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...values, _hp: hp }),
      });
      const data = await res.json().catch(() => ({}));

      if (res.status === 422 && data.fieldErrors) {
        setErrors(data.fieldErrors);
        setStatus("error");
        return;
      }
      if (!res.ok) {
        setStatus("error");
        return;
      }
      setStatus(data.delivered === false ? "degraded" : "success");
      if (data.delivered !== false) setValues(initial);
    } catch {
      setStatus("error");
    }
  }

  if (status === "success") {
    return (
      <div role="status" className="rounded-2xl border border-green-200 bg-green-50 p-6 text-green-800">
        <p className="font-semibold">Messaggio inviato!</p>
        <p className="mt-1 text-sm">Grazie per averci scritto: ti risponderemo al più presto.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {/* honeypot (nascosto agli utenti, visibile ai bot) */}
      <input
        type="text"
        name="_hp"
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        value={hp}
        onChange={(e) => setHp(e.target.value)}
        className="hidden"
      />

      <Field id="nome" label="Nome e cognome" error={errors.nome} required>
        <input
          id="nome"
          type="text"
          autoComplete="name"
          value={values.nome}
          onChange={set("nome")}
          aria-invalid={!!errors.nome}
          aria-describedby={errors.nome ? "nome-err" : undefined}
          className={inputCls(!!errors.nome)}
        />
      </Field>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field id="email" label="Email" error={errors.email} required>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={values.email}
            onChange={set("email")}
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? "email-err" : undefined}
            className={inputCls(!!errors.email)}
          />
        </Field>
        <Field id="telefono" label="Telefono (facoltativo)">
          <input
            id="telefono"
            type="tel"
            autoComplete="tel"
            value={values.telefono}
            onChange={set("telefono")}
            className={inputCls(false)}
          />
        </Field>
      </div>

      <Field id="messaggio" label="Messaggio" error={errors.messaggio} required>
        <textarea
          id="messaggio"
          rows={5}
          value={values.messaggio}
          onChange={set("messaggio")}
          aria-invalid={!!errors.messaggio}
          aria-describedby={errors.messaggio ? "messaggio-err" : undefined}
          className={inputCls(!!errors.messaggio)}
        />
      </Field>

      <div>
        <label className="flex items-start gap-3 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={values.privacy}
            onChange={set("privacy")}
            aria-invalid={!!errors.privacy}
            className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-600"
          />
          <span>
            Acconsento al trattamento dei miei dati per essere ricontattato, secondo l&apos;informativa
            sulla privacy.
          </span>
        </label>
        {errors.privacy && (
          <p className="mt-1 text-sm text-brand-700">{errors.privacy}</p>
        )}
      </div>

      {status === "degraded" && (
        <p role="alert" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          Al momento non riusciamo a inviare il modulo. Scrivici a{" "}
          <a className="font-semibold underline" href={`mailto:${siteConfig.contact.email}`}>
            {siteConfig.contact.email}
          </a>{" "}
          o chiama il {siteConfig.contact.phone}.
        </p>
      )}
      {status === "error" && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
          Si è verificato un errore. Riprova o contattaci direttamente via email o telefono.
        </p>
      )}

      <button
        type="submit"
        disabled={status === "loading"}
        className="inline-flex items-center justify-center rounded-lg bg-brand-600 px-6 py-3 font-semibold text-white shadow-sm transition-colors hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 disabled:opacity-60"
      >
        {status === "loading" ? "Invio in corso…" : "Invia messaggio"}
      </button>
    </form>
  );
}

function inputCls(hasError: boolean) {
  return `w-full rounded-lg border px-3 py-2.5 text-slate-900 shadow-sm outline-none transition-colors focus:ring-2 ${
    hasError
      ? "border-red-400 focus:border-red-500 focus:ring-red-200"
      : "border-slate-300 focus:border-brand-500 focus:ring-brand-200"
  }`;
}

function Field({
  id,
  label,
  error,
  required,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-slate-800">
        {label} {required && <span className="text-brand-600" aria-hidden="true">*</span>}
      </label>
      {children}
      {error && (
        <p id={`${id}-err`} className="mt-1 text-sm text-brand-700">
          {error}
        </p>
      )}
    </div>
  );
}
