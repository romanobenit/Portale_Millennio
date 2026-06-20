import { apiClient } from "./client";

export interface PricingRule {
  id: string;
  tipo: "tariffa_base" | "leva_data" | "leva_scarsita" | "sconto_promo";
  fascia: "notte" | "mattina" | "pomeriggio" | null;
  soglia_min: number | null;
  soglia_max: number | null;
  valore: number;
  attivo: boolean;
  nome: string;
  valido_fino_a: string | null;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface PricingRuleCreate {
  tipo: string;
  fascia?: string | null;
  soglia_min?: number | null;
  soglia_max?: number | null;
  valore: number;
  attivo?: boolean;
  nome: string;
  valido_fino_a?: string | null;
  note?: string | null;
}

export interface SimulazioneRequest {
  fascia: string;
  data: string;
  pct_libere_override?: number | null;
}

export interface SimulazioneResponse {
  fascia: string;
  data: string;
  tariffa_base: number;
  moltiplicatore_data: number;
  moltiplicatore_scarsita: number;
  sconto_promo_pct: number;
  prezzo_ora: number;
  giorni_mancanti: number;
  pct_libere_effettiva: number | null;
}

export interface OrePerFascia {
  notte: number;
  mattina: number;
  pomeriggio: number;
}

export interface DashboardFundraising {
  totale_raccolto_eur: number;
  obiettivo_eur: number;
  percentuale: number;
  nft_emessi_totali: number;
  periodo_inizio: string;
  periodo_fine: string;
  ore_vendute: OrePerFascia;
  ore_disponibili: OrePerFascia;
  ore_totali_periodo: OrePerFascia;
  pct_riempimento: Record<string, number>;
  incassi_30gg: { data: string; importo: number }[];
  top_5_vendite: { data: string; fascia: string; ore: number; importo: number; token_id: number | null }[];
}

export interface RendicontoAnnuale {
  anno: number;
  periodo_inizio: string;
  periodo_fine: string;
  fasce: { fascia: string; ore_vendute: number; ore_totali_stagione: number; ricavi_lordi: number }[];
  totale_ricavi: number;
  totale_nft: number;
  generato_il: string;
}

export async function fetchPricingRules(): Promise<PricingRule[]> {
  const { data } = await apiClient.get<PricingRule[]>("/dirigenza/pricing-rules");
  return data;
}

export async function createPricingRule(payload: PricingRuleCreate): Promise<PricingRule> {
  const { data } = await apiClient.post<PricingRule>("/dirigenza/pricing-rules", payload);
  return data;
}

export async function updatePricingRule(id: string, payload: Partial<PricingRuleCreate>): Promise<PricingRule> {
  const { data } = await apiClient.put<PricingRule>(`/dirigenza/pricing-rules/${id}`, payload);
  return data;
}

export async function deletePricingRule(id: string): Promise<PricingRule> {
  const { data } = await apiClient.delete<PricingRule>(`/dirigenza/pricing-rules/${id}`);
  return data;
}

export async function simulaPrezzo(req: SimulazioneRequest): Promise<SimulazioneResponse> {
  const { data } = await apiClient.post<SimulazioneResponse>("/dirigenza/pricing-simulate", req);
  return data;
}

export async function fetchDashboardFundraising(): Promise<DashboardFundraising> {
  const { data } = await apiClient.get<DashboardFundraising>("/dirigenza/fundraising");
  return data;
}

export async function fetchRendiconto(anno: number): Promise<RendicontoAnnuale> {
  const { data } = await apiClient.get<RendicontoAnnuale>("/dirigenza/rendiconto", { params: { anno } });
  return data;
}
