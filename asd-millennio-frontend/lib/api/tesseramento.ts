import { apiClient } from "./client";
import type { Socio } from "./soci";

export interface OnboardingData {
  nome: string;
  cognome: string;
  data_nascita: string; // YYYY-MM-DD
  codice_fiscale: string;
  indirizzo?: string;
  telefono?: string;
}

export interface MinoreData {
  nome: string;
  cognome: string;
  data_nascita: string;
  codice_fiscale: string;
  indirizzo?: string;
}

export interface DocumentoResponse {
  id: string;
  tipo: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface CheckoutResponse {
  tessera_id: string;
  pagamento_id: string;
  stripe_checkout_url: string;
  importo_eur: number;
}

export interface Quota {
  id: string;
  categoria: string;
  is_minore: boolean;
  importo_eur: number;
  anno_sportivo: string;
  attivo: boolean;
  note: string | null;
}

export interface TesseramentoDaVerificare {
  tessera_id: string;
  numero_tessera: string;
  categoria: string;
  anno_sportivo: string | null;
  verifica_scadenza: string | null;
  importo_eur: number | null;
  socio: { id: string; nome: string; cognome: string; codice_fiscale: string; is_minor: boolean };
  tutore: { id: string; nome: string; cognome: string } | null;
  documenti: { id: string; tipo: string; filename: string }[];
}

// ── socio (self) ────────────────────────────────────────────────────────────

export async function creaProfilo(data: OnboardingData): Promise<Socio> {
  const { data: res } = await apiClient.post<Socio>("/soci/me", data);
  return res;
}

export async function caricaDocumento(
  tipo: "identita" | "tutela",
  file: File,
  socioId?: string,
): Promise<DocumentoResponse> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<DocumentoResponse>("/soci/me/documenti", form, {
    params: { tipo, socio_id: socioId },
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function avviaTesseramento(categoria: string): Promise<CheckoutResponse> {
  const { data } = await apiClient.post<CheckoutResponse>("/soci/me/tesseramento", { categoria });
  return data;
}

// ── minori ──────────────────────────────────────────────────────────────────

export async function aggiungiMinore(data: MinoreData): Promise<Socio> {
  const { data: res } = await apiClient.post<Socio>("/soci/me/minori", data);
  return res;
}

export async function fetchMieiMinori(): Promise<Socio[]> {
  const { data } = await apiClient.get<Socio[]>("/soci/me/minori");
  return data;
}

export async function avviaTesseramentoMinore(minoreId: string, categoria: string): Promise<CheckoutResponse> {
  const { data } = await apiClient.post<CheckoutResponse>(
    `/soci/me/minori/${minoreId}/tesseramento`,
    { categoria },
  );
  return data;
}

// ── consensi (riuso endpoint esistente) ───────────────────────────────────────

export async function firmaConsensoSocio(
  socioId: string,
  tipo: "privacy" | "trattamento_dati" | "foto_video" | "marketing",
  firmatoDa?: string,
): Promise<void> {
  await apiClient.post(`/soci/${socioId}/consensi`, {
    socio_id: socioId,
    tipo,
    testo_versione: "v1",
    firmato_da: firmatoDa,
  });
}

// ── staff: verifiche ──────────────────────────────────────────────────────────

export async function fetchVerifiche(): Promise<TesseramentoDaVerificare[]> {
  const { data } = await apiClient.get<TesseramentoDaVerificare[]>("/soci/verifiche");
  return data;
}

export async function confermaVerifica(tesseraId: string): Promise<void> {
  await apiClient.post(`/soci/verifiche/${tesseraId}/conferma`);
}

export async function rifiutaVerifica(tesseraId: string): Promise<void> {
  await apiClient.post(`/soci/verifiche/${tesseraId}/rifiuta`);
}

export async function scaricaDocumento(docId: string): Promise<void> {
  const res = await apiClient.get(`/soci/documenti/${docId}`, { responseType: "blob" });
  const url = window.URL.createObjectURL(res.data as Blob);
  window.open(url, "_blank");
  setTimeout(() => window.URL.revokeObjectURL(url), 10000);
}

// ── dirigenza: quote ──────────────────────────────────────────────────────────

export async function fetchQuote(annoSportivo?: string): Promise<Quota[]> {
  const { data } = await apiClient.get<Quota[]>("/dirigenza/quote-tessera", {
    params: annoSportivo ? { anno_sportivo: annoSportivo } : undefined,
  });
  return data;
}

export async function creaQuota(payload: {
  categoria: string;
  is_minore: boolean;
  importo_eur: number;
  anno_sportivo: string;
  note?: string;
}): Promise<Quota> {
  const { data } = await apiClient.post<Quota>("/dirigenza/quote-tessera", payload);
  return data;
}

export async function aggiornaQuota(
  id: string,
  payload: { importo_eur?: number; attivo?: boolean; note?: string },
): Promise<Quota> {
  const { data } = await apiClient.put<Quota>(`/dirigenza/quote-tessera/${id}`, payload);
  return data;
}
