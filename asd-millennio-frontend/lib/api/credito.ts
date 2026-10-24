import { apiClient } from "./client";

export type TipoMovimento =
  | "accredito"
  | "storno"
  | "ricarica_sede"
  | "ricarica_online"
  | "pagamento_evento"
  | "rimborso_evento";

export interface MovimentoCredito {
  id: string;
  tipo: TipoMovimento;
  importo_eur: string; // Decimal con segno: positivo entra, negativo esce
  saldo_dopo_eur: string;
  causale: string | null;
  prenotazione_evento_id: string | null;
  created_at: string;
}

export interface MioCredito {
  saldo_eur: string;
  movimenti: MovimentoCredito[];
  ricarica_online_attiva: boolean;
  ricarica_min_eur: number;
  ricarica_max_eur: number;
  saldo_max_eur: number;
}

export interface SaldoSocio {
  socio_id: string;
  nome: string;
  cognome: string;
  codice_fiscale: string;
  saldo_eur: string;
}

export interface SchedaCreditoSocio extends SaldoSocio {
  movimenti: MovimentoCredito[];
}

export interface RiepilogoCredito {
  credito_in_circolo_eur: string;
  soci_con_saldo: number;
  ultimi_30gg: { tipo: TipoMovimento; movimenti: number; totale_eur: string }[];
  ricarica_online_attiva: boolean;
}

export const ETICHETTA_MOVIMENTO: Record<TipoMovimento, string> = {
  accredito: "Accredito",
  storno: "Storno",
  ricarica_sede: "Ricarica in sede",
  ricarica_online: "Ricarica online",
  pagamento_evento: "Ingresso evento",
  rimborso_evento: "Rimborso ingresso",
};

export function formattaEuro(eur: string | number, conSegno = false): string {
  const n = Number(eur);
  const testo = `€ ${Math.abs(n).toFixed(2).replace(".", ",")}`;
  if (!conSegno) return n < 0 ? `-${testo}` : testo;
  return n > 0 ? `+${testo}` : n < 0 ? `-${testo}` : testo;
}

// ─── Socio ────────────────────────────────────────────────────────────────

export async function fetchMioCredito(): Promise<MioCredito> {
  const { data } = await apiClient.get<MioCredito>("/credito/me");
  return data;
}

export async function avviaRicaricaOnline(importoEur: number): Promise<string> {
  const { data } = await apiClient.post<{ stripe_checkout_url: string }>("/credito/ricarica", {
    importo_eur: importoEur,
  });
  return data.stripe_checkout_url;
}

// ─── Dirigenza ────────────────────────────────────────────────────────────

export async function fetchRiepilogoCredito(): Promise<RiepilogoCredito> {
  const { data } = await apiClient.get<RiepilogoCredito>("/dirigenza/credito/riepilogo");
  return data;
}

export async function cercaSaldiSoci(q: string): Promise<SaldoSocio[]> {
  const { data } = await apiClient.get<SaldoSocio[]>("/dirigenza/credito/soci", { params: { q } });
  return data;
}

export async function fetchSchedaCredito(socioId: string): Promise<SchedaCreditoSocio> {
  const { data } = await apiClient.get<SchedaCreditoSocio>(`/dirigenza/credito/soci/${socioId}`);
  return data;
}

export async function registraMovimento(
  socioId: string,
  input: { tipo: "accredito" | "storno" | "ricarica_sede"; importo_eur: number; causale?: string | null },
): Promise<SchedaCreditoSocio> {
  const { data } = await apiClient.post<SchedaCreditoSocio>(`/dirigenza/credito/soci/${socioId}/movimenti`, input);
  return data;
}
