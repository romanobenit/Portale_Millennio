import { apiClient } from "./client";

export type Formato = "singolo" | "doppio";
export type StatoPartita = "in_attesa_conferma" | "confermata" | "contestata" | "annullata";

export interface GiocatoreBreve {
  socio_id: string;
  nome: string;
  squadra: "a" | "b";
  rating_prima: number | null;
  rating_dopo: number | null;
}

export interface Partita {
  id: string;
  formato: Formato;
  data: string; // YYYY-MM-DD
  punteggi: [number, number][];
  vincitore: "a" | "b";
  stato: StatoPartita;
  torneo: string | null;
  inserita_da_dirigenza: boolean;
  note: string | null;
  giocatori: GiocatoreBreve[];
  created_at: string;
  da_confermare: boolean;
}

export interface RigaClassifica {
  posizione: number;
  socio_id: string;
  nome: string;
  rating: number;
  rating_max: number;
  partite: number;
  vittorie: number;
  provvisorio: boolean;
  dupr: number | null;
}

export interface StatisticheFormato {
  formato: Formato;
  rating: number | null;
  rating_max: number | null;
  posizione: number | null;
  partite: number;
  vittorie: number;
  provvisorio: boolean;
  obiettivo: number | null;
  andamento: { data: string; rating: number }[];
}

export interface ProfiloAtleta {
  visibile_in_classifica: boolean;
  obiettivo_singolo: number | null;
  obiettivo_doppio: number | null;
  obiettivo_partite_mese: number | null;
  dupr_id: string | null;
  dupr_singolo: number | null;
  dupr_doppio: number | null;
}

export interface MioPickleball {
  profilo: ProfiloAtleta;
  singolo: StatisticheFormato;
  doppio: StatisticheFormato;
  partite_questo_mese: number;
  serie_vittorie: number;
  compagno_frequente: string | null;
  avversario_frequente: string | null;
  da_confermare: Partita[];
  in_attesa_altri: Partita[];
  recenti: Partita[];
}

export interface GiocatoreRicerca {
  socio_id: string;
  nome: string;
  rating_singolo: number | null;
  rating_doppio: number | null;
}

export interface PartitaInput {
  formato: Formato;
  data: string;
  compagno_id?: string | null;
  avversari_ids: string[];
  punteggi: number[][];
}

export interface PartitaDirigenzaInput {
  formato: Formato;
  data: string;
  squadra_a: string[];
  squadra_b: string[];
  punteggi: number[][];
  torneo?: string | null;
  note?: string | null;
}

export interface DashboardPickleball {
  giocatori_attivi_30gg: number;
  partite_30gg: number;
  partite_totali: number;
  da_risolvere: number;
  in_attesa_conferma: number;
  per_settimana: { settimana: string; partite: number }[];
  top_singolo: RigaClassifica[];
  top_doppio: RigaClassifica[];
}

// ─── Socio ────────────────────────────────────────────────────────────────

export async function fetchMioPickleball(): Promise<MioPickleball> {
  const { data } = await apiClient.get<MioPickleball>("/pickleball/me");
  return data;
}

export async function fetchClassifica(formato: Formato): Promise<RigaClassifica[]> {
  const { data } = await apiClient.get<RigaClassifica[]>("/pickleball/classifica", { params: { formato } });
  return data;
}

export async function aggiornaProfiloAtleta(input: Partial<ProfiloAtleta>): Promise<ProfiloAtleta> {
  const { data } = await apiClient.put<ProfiloAtleta>("/pickleball/me/profilo", input);
  return data;
}

export async function cercaGiocatori(q: string): Promise<GiocatoreRicerca[]> {
  const { data } = await apiClient.get<GiocatoreRicerca[]>("/pickleball/giocatori", { params: { q } });
  return data;
}

export async function registraPartita(input: PartitaInput): Promise<Partita> {
  const { data } = await apiClient.post<Partita>("/pickleball/partite", input);
  return data;
}

export async function confermaPartita(id: string): Promise<void> {
  await apiClient.post(`/pickleball/partite/${id}/conferma`);
}

export async function contestaPartita(id: string, motivo: string): Promise<void> {
  await apiClient.post(`/pickleball/partite/${id}/contesta`, { motivo });
}

export async function ritiraPartita(id: string): Promise<void> {
  await apiClient.delete(`/pickleball/partite/${id}`);
}

// ─── Dirigenza ────────────────────────────────────────────────────────────

export async function fetchDashboardPickleball(): Promise<DashboardPickleball> {
  const { data } = await apiClient.get<DashboardPickleball>("/dirigenza/pickleball/dashboard");
  return data;
}

export async function fetchClassificaCompleta(formato: Formato): Promise<RigaClassifica[]> {
  const { data } = await apiClient.get<RigaClassifica[]>("/dirigenza/pickleball/classifica", { params: { formato } });
  return data;
}

export async function fetchPartiteDirigenza(stato?: StatoPartita): Promise<Partita[]> {
  const { data } = await apiClient.get<Partita[]>("/dirigenza/pickleball/partite", {
    params: stato ? { stato } : {},
  });
  return data;
}

export async function cercaGiocatoriDirigenza(q: string): Promise<GiocatoreRicerca[]> {
  const { data } = await apiClient.get<GiocatoreRicerca[]>("/dirigenza/pickleball/giocatori", { params: { q } });
  return data;
}

export async function registraPartitaDirigenza(input: PartitaDirigenzaInput): Promise<Partita> {
  const { data } = await apiClient.post<Partita>("/dirigenza/pickleball/partite", input);
  return data;
}

export async function risolviPartita(id: string, esito: "conferma" | "annulla"): Promise<void> {
  await apiClient.post(`/dirigenza/pickleball/partite/${id}/${esito}`);
}

// ─── Formattazione ────────────────────────────────────────────────────────

export function formattaPunteggi(p: Partita, dalLatoDi?: "a" | "b"): string {
  return p.punteggi.map(([a, b]) => (dalLatoDi === "b" ? `${b}-${a}` : `${a}-${b}`)).join(", ");
}

export function nomiSquadra(p: Partita, squadra: "a" | "b"): string {
  return p.giocatori.filter((g) => g.squadra === squadra).map((g) => g.nome).join(" / ");
}

export function formattaData(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("it-IT", { day: "numeric", month: "short", year: "numeric" });
}

/** Legge "11-7, 9-11, 11-8" (o "11 7; 9 11") in [[11,7],[9,11],[11,8]]; null se non valido. */
export function leggiPunteggi(testo: string): number[][] | null {
  const game = testo.split(/[,;]+/).map((g) => g.trim()).filter(Boolean);
  if (game.length === 0 || game.length > 5) return null;
  const out: number[][] = [];
  for (const g of game) {
    const m = g.match(/^(\d{1,2})\s*[-–:\s]\s*(\d{1,2})$/);
    if (!m) return null;
    out.push([Number(m[1]), Number(m[2])]);
  }
  return out;
}
