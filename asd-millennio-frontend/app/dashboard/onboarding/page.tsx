"use client";

import { useState } from "react";
import { getKeycloak } from "@/lib/auth/keycloak";
import {
  creaProfilo,
  caricaDocumento,
  avviaTesseramento,
  firmaConsensoSocio,
  OnboardingData,
} from "@/lib/api/tesseramento";
import toast from "react-hot-toast";
import { clsx } from "clsx";

const CATEGORIE: { value: string; label: string }[] = [
  { value: "volley", label: "Pallavolo" },
  { value: "badminton", label: "Badminton" },
  { value: "kung_fu", label: "Kung Fu" },
  { value: "pickleball", label: "Pickleball" },
  { value: "sostenitore", label: "Socio sostenitore" },
];

const STEPS = ["Dati", "Documento", "Consensi", "Categoria e pagamento"];

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [socioId, setSocioId] = useState<string | null>(null);

  const [form, setForm] = useState<OnboardingData>({
    nome: "", cognome: "", data_nascita: "", codice_fiscale: "", indirizzo: "", telefono: "",
  });
  const [file, setFile] = useState<File | null>(null);
  const [consensi, setConsensi] = useState({ privacy: false, trattamento_dati: false });
  const [categoria, setCategoria] = useState("volley");

  const kc = getKeycloak();
  if (!kc.token) {
    kc.login();
    return null;
  }

  const set = (k: keyof OnboardingData, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const submitDati = async () => {
    if (!form.nome || !form.cognome || !form.data_nascita || form.codice_fiscale.length !== 16) {
      toast.error("Compila nome, cognome, data di nascita e un codice fiscale valido (16 caratteri).");
      return;
    }
    setBusy(true);
    try {
      const socio = await creaProfilo(form);
      setSocioId(socio.id);
      setStep(1);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore nella creazione del profilo");
    } finally {
      setBusy(false);
    }
  };

  const submitDocumento = async () => {
    if (!file) {
      toast.error("Carica il documento d'identità.");
      return;
    }
    setBusy(true);
    try {
      await caricaDocumento("identita", file);
      setStep(2);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore nel caricamento del documento");
    } finally {
      setBusy(false);
    }
  };

  const submitConsensi = async () => {
    if (!consensi.privacy || !consensi.trattamento_dati) {
      toast.error("Devi accettare entrambi i consensi per proseguire.");
      return;
    }
    if (!socioId) return;
    setBusy(true);
    try {
      await firmaConsensoSocio(socioId, "privacy", socioId);
      await firmaConsensoSocio(socioId, "trattamento_dati", socioId);
      setStep(3);
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore nella registrazione dei consensi");
    } finally {
      setBusy(false);
    }
  };

  const paga = async () => {
    setBusy(true);
    try {
      const res = await avviaTesseramento(categoria);
      window.location.href = res.stripe_checkout_url;
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Errore nell'avvio del pagamento");
      setBusy(false);
    }
  };

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Tesseramento</h1>
      <p className="text-gray-500 text-sm mb-6">
        Completa i passaggi per tesserarti. La tessera sarà attiva subito dopo il pagamento;
        lo staff conferma la validità entro 30 giorni.
      </p>

      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-2 flex-1">
            <div className={clsx(
              "h-7 w-7 rounded-full flex items-center justify-center text-xs font-semibold shrink-0",
              i < step ? "bg-green-600 text-white" : i === step ? "bg-blue-700 text-white" : "bg-gray-200 text-gray-500",
            )}>{i < step ? "✓" : i + 1}</div>
            <span className={clsx("text-xs hidden sm:block", i === step ? "text-gray-900 font-medium" : "text-gray-400")}>{s}</span>
            {i < STEPS.length - 1 && <div className="h-px flex-1 bg-gray-200" />}
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        {step === 0 && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Nome" value={form.nome} onChange={(v) => set("nome", v)} />
              <Field label="Cognome" value={form.cognome} onChange={(v) => set("cognome", v)} />
            </div>
            <Field label="Data di nascita" type="date" value={form.data_nascita} onChange={(v) => set("data_nascita", v)} />
            <Field label="Codice fiscale" value={form.codice_fiscale} onChange={(v) => set("codice_fiscale", v.toUpperCase())} />
            <Field label="Indirizzo" value={form.indirizzo ?? ""} onChange={(v) => set("indirizzo", v)} />
            <Field label="Telefono" value={form.telefono ?? ""} onChange={(v) => set("telefono", v)} />
            <button onClick={submitDati} disabled={busy} className={btn}>Continua</button>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">Carica un documento d&apos;identità valido (PDF o immagine). Lo staff verificherà che corrisponda al codice fiscale.</p>
            <input type="file" accept=".pdf,image/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-gray-600 file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:text-blue-700" />
            <button onClick={submitDocumento} disabled={busy} className={btn}>Continua</button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3">
            <Consenso checked={consensi.privacy} onChange={(v) => setConsensi((c) => ({ ...c, privacy: v }))}
              label="Ho letto e accetto l'informativa privacy (GDPR)." />
            <Consenso checked={consensi.trattamento_dati} onChange={(v) => setConsensi((c) => ({ ...c, trattamento_dati: v }))}
              label="Acconsento al trattamento dei miei dati personali per il tesseramento." />
            <button onClick={submitConsensi} disabled={busy} className={btn}>Continua</button>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-3">
            <label className="block text-xs font-medium text-gray-600">Categoria</label>
            <select value={categoria} onChange={(e) => setCategoria(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {CATEGORIE.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            <p className="text-xs text-gray-500">Verrai reindirizzato al pagamento sicuro della quota associativa.</p>
            <button onClick={paga} disabled={busy} className={btn}>{busy ? "Reindirizzamento…" : "Paga la quota e tesserati"}</button>
          </div>
        )}
      </div>
    </div>
  );
}

const btn = "w-full rounded-lg bg-blue-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 transition-colors mt-2";

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
    </div>
  );
}

function Consenso({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="flex items-start gap-3 cursor-pointer">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="mt-0.5 h-4 w-4 rounded border-gray-300" />
      <span className="text-sm text-gray-700">{label}</span>
    </label>
  );
}
