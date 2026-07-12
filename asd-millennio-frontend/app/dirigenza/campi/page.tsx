"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getKeycloak } from "@/lib/auth/keycloak";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"];

interface SlotTemplate {
  id: string;
  giorno_settimana: number;
  ora_inizio: string;
  ora_fine: string;
  num_campi: number;
  costo_ora: number;
  sport: string[];
  attivo: boolean;
  valido_dal: string;
  valido_fino_al: string;
  note: string | null;
}

interface FormState {
  giorno_settimana: number;
  ora_inizio: string;
  ora_fine: string;
  num_campi: number;
  costo_ora: string;
  sport: string;
  attivo: boolean;
  valido_dal: string;
  valido_fino_al: string;
  note: string;
}

const EMPTY_FORM: FormState = {
  giorno_settimana: 5,
  ora_inizio: "16:30",
  ora_fine: "19:30",
  num_campi: 4,
  costo_ora: "30",
  sport: "badminton,pickleball",
  attivo: true,
  valido_dal: new Date().toISOString().slice(0, 10),
  valido_fino_al: `${new Date().getFullYear() + 1}-07-31`,
  note: "",
};

export default function GestioneCampiPage() {
  const [templates, setTemplates] = useState<SlotTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);

  // Rinfresca il token prima di ogni chiamata (l'access token dura ~5 min → evita 401)
  const authHeader = async () => {
    try {
      await getKeycloak().updateToken(30);
    } catch {
      /* refresh best-effort: se fallisce, la richiesta userà il token corrente */
    }
    return `Bearer ${getKeycloak().token ?? ""}`;
  };

  const carica = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/dirigenza/campi/templates`, {
        headers: { Authorization: await authHeader() },
      });
      if (!res.ok) throw new Error("Errore nel caricamento");
      setTemplates(await res.json());
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Errore di rete");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carica();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const apriNuovo = () => {
    setForm(EMPTY_FORM);
    setEditId(null);
    setShowForm(true);
  };

  const apriModifica = (t: SlotTemplate) => {
    setForm({
      giorno_settimana: t.giorno_settimana,
      ora_inizio: t.ora_inizio.slice(0, 5),
      ora_fine: t.ora_fine.slice(0, 5),
      num_campi: t.num_campi,
      costo_ora: String(t.costo_ora),
      sport: t.sport.join(","),
      attivo: t.attivo,
      valido_dal: t.valido_dal,
      valido_fino_al: t.valido_fino_al,
      note: t.note ?? "",
    });
    setEditId(t.id);
    setShowForm(true);
  };

  const salva = async () => {
    setSaving(true);
    try {
      const body = {
        giorno_settimana: form.giorno_settimana,
        ora_inizio: form.ora_inizio + ":00",
        ora_fine: form.ora_fine + ":00",
        num_campi: form.num_campi,
        costo_ora: parseFloat(form.costo_ora),
        sport: form.sport.split(",").map((s) => s.trim()).filter(Boolean),
        attivo: form.attivo,
        valido_dal: form.valido_dal,
        valido_fino_al: form.valido_fino_al,
        note: form.note || null,
      };

      const url = editId
        ? `${API}/dirigenza/campi/templates/${editId}`
        : `${API}/dirigenza/campi/templates`;
      const method = editId ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: await authHeader(),
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.message ?? "Errore nel salvataggio");
      }
      setShowForm(false);
      await carica();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Errore nel salvataggio");
    } finally {
      setSaving(false);
    }
  };

  const disattiva = async (id: string) => {
    if (!confirm("Disattivare questo slot? Non sarà più prenotabile.")) return;
    const res = await fetch(`${API}/dirigenza/campi/templates/${id}`, {
      method: "DELETE",
      headers: { Authorization: await authHeader() },
    });
    if (!res.ok) {
      alert("Errore nella disattivazione");
      return;
    }
    await carica();
  };

  return (
    <div className="space-y-6">
      <Link
        href="/dirigenza"
        className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
      >
        ← Torna alla dashboard
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestione Campi</h1>
          <p className="text-sm text-gray-500 mt-1">
            Definisci le fasce prenotabili: <strong>orari</strong> (= ore disponibili), numero campi e tariffa
          </p>
        </div>
        <button
          onClick={apriNuovo}
          className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 transition-colors"
        >
          + Nuovo slot
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-red-800 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-gray-500 text-sm py-8">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          Caricamento…
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3">Giorno</th>
                <th className="px-4 py-3">Orario</th>
                <th className="px-4 py-3">Campi</th>
                <th className="px-4 py-3">€/ora</th>
                <th className="px-4 py-3">Sport</th>
                <th className="px-4 py-3">Periodo</th>
                <th className="px-4 py-3">Stato</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {templates.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                    Nessun template configurato
                  </td>
                </tr>
              )}
              {templates.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{GIORNI[t.giorno_settimana]}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {t.ora_inizio.slice(0, 5)}–{t.ora_fine.slice(0, 5)}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{t.num_campi}</td>
                  <td className="px-4 py-3 text-gray-600">€{t.costo_ora}</td>
                  <td className="px-4 py-3 text-gray-600">{t.sport.join(", ")}</td>
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                    {t.valido_dal} → {t.valido_fino_al}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        t.attivo ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {t.attivo ? "Attivo" : "Disattivo"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button
                      onClick={() => apriModifica(t)}
                      className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                    >
                      Modifica
                    </button>
                    {t.attivo && (
                      <button
                        onClick={() => disattiva(t.id)}
                        className="text-red-500 hover:text-red-700 text-xs font-medium"
                      >
                        Disattiva
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Form modale */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">
                {editId ? "Modifica slot" : "Nuovo slot prenotabile"}
              </h2>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600">
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-700 mb-1">Giorno della settimana</label>
                <select
                  value={form.giorno_settimana}
                  onChange={(e) => setForm((f) => ({ ...f, giorno_settimana: Number(e.target.value) }))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                >
                  {GIORNI.map((g, i) => (
                    <option key={i} value={i}>{g}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Ora inizio</label>
                <input
                  type="time"
                  value={form.ora_inizio}
                  onChange={(e) => setForm((f) => ({ ...f, ora_inizio: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Ora fine</label>
                <input
                  type="time"
                  value={form.ora_fine}
                  onChange={(e) => setForm((f) => ({ ...f, ora_fine: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Numero campi</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={form.num_campi}
                  onChange={(e) => setForm((f) => ({ ...f, num_campi: Number(e.target.value) }))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Costo (€/ora)</label>
                <input
                  type="number"
                  step="0.50"
                  min={0}
                  value={form.costo_ora}
                  onChange={(e) => setForm((f) => ({ ...f, costo_ora: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Sport (separati da virgola)
                </label>
                <input
                  type="text"
                  placeholder="badminton,pickleball"
                  value={form.sport}
                  onChange={(e) => setForm((f) => ({ ...f, sport: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Valido dal</label>
                <input
                  type="date"
                  value={form.valido_dal}
                  onChange={(e) => setForm((f) => ({ ...f, valido_dal: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Valido fino al</label>
                <input
                  type="date"
                  value={form.valido_fino_al}
                  onChange={(e) => setForm((f) => ({ ...f, valido_fino_al: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-700 mb-1">Note (opzionale)</label>
                <input
                  type="text"
                  value={form.note}
                  onChange={(e) => setForm((f) => ({ ...f, note: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div className="col-span-2 flex items-center gap-2">
                <input
                  type="checkbox"
                  id="attivo"
                  checked={form.attivo}
                  onChange={(e) => setForm((f) => ({ ...f, attivo: e.target.checked }))}
                  className="rounded"
                />
                <label htmlFor="attivo" className="text-sm text-gray-700">Attivo (visibile ai soci)</label>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
              >
                Annulla
              </button>
              <button
                onClick={salva}
                disabled={saving}
                className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50 transition-colors"
              >
                {saving ? "Salvataggio…" : "Salva"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
