import { apiClient } from "./client";

export interface Socio {
  id: string;
  nome: string;
  cognome: string;
  data_nascita: string;
  codice_fiscale: string;
  email: string;
  telefono: string | null;
  foto_url: string | null;
  is_minor: boolean;
  tutore_id: string | null;
  sport: string[];
  created_at: string;
  updated_at: string;
}

export interface Tessera {
  id: string;
  socio_id: string;
  numero_tessera: string;
  sport: string;
  stato: string;
  verifica_stato: string | null;
  data_emissione: string | null;
  data_scadenza: string | null;
  anno_sportivo: string | null;
  pdf_url: string | null;
}

export interface Consenso {
  id: string;
  socio_id: string;
  tipo: "privacy" | "trattamento_dati" | "foto_video" | "marketing";
  testo_versione: string | null;
  firmato_da: string | null;
  timestamp_firma: string | null;
  revocato_at: string | null;
}

export async function fetchMe(): Promise<Socio> {
  const { data } = await apiClient.get<Socio>("/soci/me");
  return data;
}

export async function fetchSoci(page = 1, limit = 20) {
  const { data } = await apiClient.get("/soci", { params: { page, limit } });
  return data;
}

export async function creaSocio(payload: Partial<Socio>) {
  const { data } = await apiClient.post<Socio>("/soci", payload);
  return data;
}

export async function fetchTessereSocio(socioId: string, stato?: string): Promise<Tessera[]> {
  const { data } = await apiClient.get<Tessera[]>(`/soci/${socioId}/tessere`, {
    params: stato ? { stato } : undefined,
  });
  return data;
}

export async function fetchConsensiSocio(socioId: string): Promise<Consenso[]> {
  const { data } = await apiClient.get<Consenso[]>(`/soci/${socioId}/consensi`);
  return data;
}

export async function firmaConsenso(
  socioId: string,
  payload: { tipo: Consenso["tipo"]; testo_versione: string; firmato_da?: string }
): Promise<Consenso> {
  const { data } = await apiClient.post<Consenso>(`/soci/${socioId}/consensi`, {
    socio_id: socioId,
    ...payload,
  });
  return data;
}

export async function revocaConsenso(socioId: string, consensoId: string): Promise<void> {
  await apiClient.delete(`/soci/${socioId}/consensi/${consensoId}`);
}

export async function fetchMinoriSocio(socioId: string): Promise<Socio[]> {
  const { data } = await apiClient.get<Socio[]>(`/soci/${socioId}/minori`);
  return data;
}

export async function eliminaSocio(socioId: string): Promise<void> {
  await apiClient.delete(`/soci/${socioId}`);
}
