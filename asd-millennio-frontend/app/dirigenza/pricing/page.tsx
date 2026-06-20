"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getKeycloak, isDirigenza } from "@/lib/auth/keycloak";
import toast from "react-hot-toast";
import {
  fetchPricingRules,
  createPricingRule,
  updatePricingRule,
  simulaPrezzo,
  type PricingRule,
  type SimulazioneResponse,
} from "@/lib/api/dirigenza";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

const TIPO_LABEL: Record<string, string> = {
  tariffa_base: "Tariffa base (€/h)",
  leva_data: "Leva data (moltiplicatore)",
  leva_scarsita: "Leva scarsità (moltiplicatore)",
  sconto_promo: "Sconto promozionale (%)",
};

const FASCIA_LABEL: Record<string, string> = {
  notte: "Notte",
  mattina: "Mattina",
  pomeriggio: "Pomeriggio",
};

export default function PricingPage() {
  const router = useRouter();
  const [rules, setRules] = useState<PricingRule[]>([]);
  const [loading, setLoading] = useState(true);

  // Simulatore
  const [simFascia, setSimFascia] = useState("mattina");
  const [simData, setSimData] = useState(new Date().toISOString().slice(0, 10));
  const [simRisultato, setSimRisultato] = useState<SimulazioneResponse | null>(null);
  const [simLoading, setSimLoading] = useState(false);

  // Nuovo sconto
  const [nuovoSconto, setNuovoSconto] = useState({ nome: "", valore: 10, fascia: "", valido_fino_a: "" });
  const [aggiungiLoading, setAggiungiLoading] = useState(false);

  useEffect(() => {
    const kc = getKeycloak();
    if (!kc.authenticated || !isDirigenza(kc)) { router.push("/"); return; }
    carica();
  }, [router]);

  const carica = async () => {
    setLoading(true);
    try {
      setRules(await fetchPricingRules());
    } catch { toast.error("Errore nel caricamento regole"); }
    finally { setLoading(false); }
  };

  const handleToggle = async (rule: PricingRule) => {
    try {
      const updated = await updatePricingRule(rule.id, { attivo: !rule.attivo });
      setRules((prev) => prev.map((r) => r.id === rule.id ? updated : r));
    } catch { toast.error("Errore nell&apos;aggiornamento"); }
  };

  const handleAggiornaMoltiplicatore = async (rule: PricingRule, nuovoValore: number) => {
    try {
      const updated = await updatePricingRule(rule.id, { valore: nuovoValore });
      setRules((prev) => prev.map((r) => r.id === rule.id ? updated : r));
      toast.success("Valore aggiornato");
    } catch { toast.error("Errore nell&apos;aggiornamento"); }
  };

  const handleSimula = async () => {
    setSimLoading(true);
    try {
      setSimRisultato(await simulaPrezzo({ fascia: simFascia, data: simData }));
    } catch { toast.error("Errore nella simulazione"); }
    finally { setSimLoading(false); }
  };

  const handleAggiungiSconto = async () => {
    if (!nuovoSconto.nome || nuovoSconto.valore <= 0) { toast.error("Nome e percentuale obbligatori"); return; }
    setAggiungiLoading(true);
    try {
      const rule = await createPricingRule({
        tipo: "sconto_promo",
        fascia: nuovoSconto.fascia || null,
        valore: nuovoSconto.valore,
        nome: nuovoSconto.nome,
        valido_fino_a: nuovoSconto.valido_fino_a || null,
      });
      setRules((prev) => [...prev, rule]);
      setNuovoSconto({ nome: "", valore: 10, fascia: "", valido_fino_a: "" });
      toast.success("Sconto creato");
    } catch { toast.error("Errore nella creazione"); }
    finally { setAggiungiLoading(false); }
  };

  const tipi = ["tariffa_base", "leva_data", "leva_scarsita", "sconto_promo"] as const;

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Gestione Pricing</h1>
        <button onClick={() => router.push("/dirigenza")} className="text-sm text-blue-600 hover:underline">
          ← Dashboard
        </button>
      </div>

      {/* ── Regole per tipo ────────────────────────────────────── */}
      {tipi.map((tipo) => {
        const rulesDelTipo = rules.filter((r) => r.tipo === tipo);
        return (
          <Card key={tipo} title={TIPO_LABEL[tipo]}>
            {loading ? (
              <p className="text-sm text-gray-400">Caricamento…</p>
            ) : rulesDelTipo.length === 0 ? (
              <p className="text-sm text-gray-400">Nessuna regola configurata</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-xs text-gray-500 text-left">
                      <th className="pb-2 pr-4">Nome</th>
                      <th className="pb-2 pr-4">Fascia</th>
                      {(tipo === "leva_data" || tipo === "leva_scarsita") && (
                        <th className="pb-2 pr-4">Soglia</th>
                      )}
                      <th className="pb-2 pr-4">Valore</th>
                      {tipo === "sconto_promo" && <th className="pb-2 pr-4">Scade il</th>}
                      <th className="pb-2">Attivo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rulesDelTipo.map((r) => (
                      <tr key={r.id} className="border-b last:border-0">
                        <td className="py-2 pr-4 font-medium">{r.nome}</td>
                        <td className="py-2 pr-4">{r.fascia ? FASCIA_LABEL[r.fascia] : "Tutte"}</td>
                        {(tipo === "leva_data" || tipo === "leva_scarsita") && (
                          <td className="py-2 pr-4 text-xs text-gray-500">
                            {r.soglia_min ?? "—"} → {r.soglia_max ?? "∞"}
                            {tipo === "leva_data" ? " giorni" : "%"}
                          </td>
                        )}
                        <td className="py-2 pr-4">
                          <ValoreEditor rule={r} tipo={tipo} onSalva={handleAggiornaMoltiplicatore} />
                        </td>
                        {tipo === "sconto_promo" && (
                          <td className="py-2 pr-4 text-xs">{r.valido_fino_a ?? "Nessuna scadenza"}</td>
                        )}
                        <td className="py-2">
                          <button
                            onClick={() => handleToggle(r)}
                            className={`relative inline-flex h-5 w-9 rounded-full transition ${r.attivo ? "bg-green-500" : "bg-gray-300"}`}
                          >
                            <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${r.attivo ? "translate-x-4" : "translate-x-0.5"}`} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Form aggiunta sconto promo */}
            {tipo === "sconto_promo" && (
              <div className="mt-4 pt-4 border-t">
                <p className="text-xs font-semibold text-gray-500 mb-3 uppercase tracking-wide">Aggiungi sconto promozionale</p>
                <div className="flex flex-wrap gap-3 items-end">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Nome</label>
                    <input
                      value={nuovoSconto.nome}
                      onChange={(e) => setNuovoSconto((p) => ({ ...p, nome: e.target.value }))}
                      placeholder="es. Black Friday"
                      className="rounded border border-gray-300 px-2 py-1.5 text-sm w-40"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Sconto %</label>
                    <input
                      type="number"
                      value={nuovoSconto.valore}
                      min={1} max={100}
                      onChange={(e) => setNuovoSconto((p) => ({ ...p, valore: Number(e.target.value) }))}
                      className="rounded border border-gray-300 px-2 py-1.5 text-sm w-20"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Fascia (opz.)</label>
                    <select
                      value={nuovoSconto.fascia}
                      onChange={(e) => setNuovoSconto((p) => ({ ...p, fascia: e.target.value }))}
                      className="rounded border border-gray-300 px-2 py-1.5 text-sm"
                    >
                      <option value="">Tutte</option>
                      <option value="notte">Notte</option>
                      <option value="mattina">Mattina</option>
                      <option value="pomeriggio">Pomeriggio</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Scade il (opz.)</label>
                    <input
                      type="date"
                      value={nuovoSconto.valido_fino_a}
                      onChange={(e) => setNuovoSconto((p) => ({ ...p, valido_fino_a: e.target.value }))}
                      className="rounded border border-gray-300 px-2 py-1.5 text-sm"
                    />
                  </div>
                  <Button size="sm" onClick={handleAggiungiSconto} loading={aggiungiLoading}>
                    Crea sconto
                  </Button>
                </div>
              </div>
            )}
          </Card>
        );
      })}

      {/* ── Simulatore prezzi ────────────────────────────────────── */}
      <Card title="Simulatore prezzi">
        <div className="flex flex-wrap gap-3 items-end mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Fascia</label>
            <select value={simFascia} onChange={(e) => setSimFascia(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1.5 text-sm">
              <option value="notte">Notte</option>
              <option value="mattina">Mattina</option>
              <option value="pomeriggio">Pomeriggio</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Data slot</label>
            <input type="date" value={simData} onChange={(e) => setSimData(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1.5 text-sm" />
          </div>
          <Button size="sm" onClick={handleSimula} loading={simLoading}>Simula</Button>
        </div>
        {simRisultato && (
          <div className="rounded-lg bg-blue-50 p-4 text-sm">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div>
                <div className="text-xs text-gray-500">Tariffa base</div>
                <div className="font-bold">€{simRisultato.tariffa_base.toFixed(2)}/h</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Giorni mancanti</div>
                <div className="font-bold">{simRisultato.giorni_mancanti}g</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Leva data</div>
                <div className="font-bold">×{simRisultato.moltiplicatore_data.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">% ore libere</div>
                <div className="font-bold">{simRisultato.pct_libere_effettiva?.toFixed(1) ?? "—"}%</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Leva scarsità</div>
                <div className="font-bold">×{simRisultato.moltiplicatore_scarsita.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Sconto promo</div>
                <div className="font-bold text-green-700">{simRisultato.sconto_promo_pct > 0 ? `-${simRisultato.sconto_promo_pct.toFixed(0)}%` : "nessuno"}</div>
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-blue-200">
              <span className="text-base font-bold text-blue-900">Prezzo finale: €{simRisultato.prezzo_ora.toFixed(2)}/ora</span>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

// ── Componente inline per editare il valore di una regola ─────────────────────

function ValoreEditor({
  rule,
  tipo,
  onSalva,
}: {
  rule: PricingRule;
  tipo: string;
  onSalva: (rule: PricingRule, valore: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(rule.valore);

  if (!editing) {
    const suffix = tipo === "tariffa_base" ? " €/h" : tipo === "sconto_promo" ? "%" : "";
    return (
      <button onClick={() => setEditing(true)} className="font-mono font-semibold hover:text-blue-600">
        {rule.valore.toFixed(tipo === "tariffa_base" ? 2 : tipo === "sconto_promo" ? 0 : 2)}{suffix}
      </button>
    );
  }

  return (
    <span className="flex items-center gap-1">
      <input
        type="number"
        value={val}
        step={tipo === "tariffa_base" ? "0.5" : tipo === "sconto_promo" ? "1" : "0.05"}
        onChange={(e) => setVal(Number(e.target.value))}
        className="w-20 rounded border border-blue-300 px-1.5 py-0.5 text-sm font-mono"
        autoFocus
      />
      <button onClick={() => { onSalva(rule, val); setEditing(false); }}
        className="text-xs text-green-700 font-semibold hover:underline">OK</button>
      <button onClick={() => { setVal(rule.valore); setEditing(false); }}
        className="text-xs text-gray-400 hover:underline">✕</button>
    </span>
  );
}
