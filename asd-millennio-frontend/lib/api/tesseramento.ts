import { apiClient } from "./client";
import type { Socio, Tessera } from "./soci";

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

export interface TesseraEsterna {
  id: string;
  socio_id: string;
  ente: string;
  asd_nome: string;
  asd_codice: string | null;
  numero_tessera: string;
  disciplina: string;
  data_scadenza: string;
  documento_id: string | null;
  verifica_stato: "in_verifica" | "confermata" | "rifiutata";
  verifica_scadenza: string | null;
  created_at: string;
}

export interface TesseraEsternaInput {
  ente: string;
  asd_nome: string;
  asd_codice?: string;
  numero_tessera: string;
  disciplina: string;
  data_scadenza: string;
}

export interface TesseramentoDaVerificare {
  tipo: "tesseramento" | "rinnovo_tessera_esterna";
  tessera_esterna: TesseraEsterna | null;
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

export interface Tesserato {
  tessera_id: string;
  numero_tessera: string;
  categoria: string;
  stato: string;
  anno_sportivo: string | null;
  data_scadenza: string | null;
  verifica_stato: string | null;
  certificato_medico_tipo: "non_agonistico" | "agonistico" | null;
  certificato_medico_scadenza: string | null;
  tessera_esterna_scadenza: string | null;
  socio: { id: string; nome: string; cognome: string; codice_fiscale: string; is_minor: boolean };
  tutore: { id: string; nome: string; cognome: string } | null;
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

export async function fetchMieiDocumenti(socioId?: string): Promise<DocumentoResponse[]> {
  const { data } = await apiClient.get<DocumentoResponse[]>("/soci/me/documenti", {
    params: socioId ? { socio_id: socioId } : undefined,
  });
  return data;
}

export async function caricaTesseraEsterna(
  dati: TesseraEsternaInput,
  file: File,
  socioId?: string,
): Promise<TesseraEsterna> {
  const form = new FormData();
  Object.entries(dati).forEach(([k, v]) => {
    if (v) form.append(k, v);
  });
  form.append("file", file);
  const { data } = await apiClient.post<TesseraEsterna>("/soci/me/tessere-esterne", form, {
    params: socioId ? { socio_id: socioId } : undefined,
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function fetchTessereEsterne(socioId?: string): Promise<TesseraEsterna[]> {
  const { data } = await apiClient.get<TesseraEsterna[]>("/soci/me/tessere-esterne", {
    params: socioId ? { socio_id: socioId } : undefined,
  });
  return data;
}

export async function caricaCertificatoMedico(
  tesseraId: string,
  tipo: "non_agonistico" | "agonistico",
  scadenza: string,
  file: File,
): Promise<Tessera> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<Tessera>(
    `/soci/me/tessere/${tesseraId}/certificato-medico`,
    form,
    { params: { tipo, scadenza }, headers: { "Content-Type": "multipart/form-data" } },
  );
  return data;
}

export async function avviaTesseramento(categoria: string): Promise<CheckoutResponse> {
  const { data } = await apiClient.post<CheckoutResponse>("/soci/me/tesseramento", { categoria });
  return data;
}

export async function riprendiPagamentoTessera(tesseraId: string): Promise<CheckoutResponse> {
  const { data } = await apiClient.post<CheckoutResponse>(`/soci/me/tessere/${tesseraId}/riprendi-pagamento`);
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

export async function fetchTesserati(filtri?: {
  stato?: string;
  categoria?: string;
  anno_sportivo?: string;
}): Promise<Tesserato[]> {
  const { data } = await apiClient.get<Tesserato[]>("/soci/tesserati", { params: filtri });
  return data;
}

export interface TesseramentoInSedeInput {
  socio_id?: string;
  anagrafica?: {
    nome: string;
    cognome: string;
    data_nascita: string;
    codice_fiscale: string;
    email: string;
    telefono?: string | null;
    indirizzo?: string | null;
  };
  categoria: string;
  consensi_firmati: boolean;
}

export interface TesseramentoInSedeEsito {
  socio_id: string;
  nome: string;
  cognome: string;
  tessera_id: string;
  numero_tessera: string;
  categoria: string;
  data_scadenza: string | null;
}

export async function tesseramentoInSede(input: TesseramentoInSedeInput): Promise<TesseramentoInSedeEsito> {
  const { data } = await apiClient.post<TesseramentoInSedeEsito>("/soci/tesseramento-in-sede", input);
  return data;
}

export interface EsitoImportRiga {
  riga: number;
  cognome: string;
  nome: string;
  esito: "nuovo" | "esistente" | "errore";
  messaggio: string | null;
  numero_tessera: string | null;
}

export interface ImportTesserati {
  importato: boolean;
  righe: EsitoImportRiga[];
  nuovi: number;
  esistenti: number;
  errori: number;
}

export async function importaTesserati(
  file: File,
  categoria: string,
  opzioni: { conferma: boolean; consensiFirmati: boolean },
): Promise<ImportTesserati> {
  const form = new FormData();
  form.append("file", file);
  form.append("categoria", categoria);
  form.append("conferma", String(opzioni.conferma));
  form.append("consensi_firmati", String(opzioni.consensiFirmati));
  const { data } = await apiClient.post<ImportTesserati>("/soci/tesseramento-in-sede/import", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function confermaVerifica(tesseraId: string): Promise<void> {
  await apiClient.post(`/soci/verifiche/${tesseraId}/conferma`);
}

export async function rifiutaVerifica(tesseraId: string): Promise<void> {
  await apiClient.post(`/soci/verifiche/${tesseraId}/rifiuta`);
}

export async function esitoTesseraEsterna(tesseraEsternaId: string, esito: "conferma" | "rifiuta"): Promise<void> {
  await apiClient.post(`/soci/verifiche/tessere-esterne/${tesseraEsternaId}/${esito}`);
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
