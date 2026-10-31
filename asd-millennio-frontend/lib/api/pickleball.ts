import { apiClient } from "./client";

export type Formato = "singolo" | "doppio";
export type StatoPartita = "in_attesa_conferma" | "confermata" | "contestata" | "annullata";

export interface GiocatoreBreve {
  socio_id: string | null;
  ospite_id: string | null;
  ospite: boolean;
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
  torneo_id: string | null;
  categoria: string | null;
  fase: string | null;
  walkover: boolean;
  fuori_classifica: string | null; // "walkover" | "limite amichevoli"
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
  inattivo: boolean;
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
  socio_id: string; // per gli ospiti (ricerca dirigenza) è l'id dell'ospite
  ospite?: boolean;
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

export interface FiltriClassifica {
  sesso?: "M" | "F";
  eta_min?: number;
}

export async function fetchClassifica(formato: Formato, filtri: FiltriClassifica = {}): Promise<RigaClassifica[]> {
  const { data } = await apiClient.get<RigaClassifica[]>("/pickleball/classifica", { params: { formato, ...filtri } });
  return data;
}

export async function fetchCircuito(anno?: string, categoria?: string): Promise<Circuito> {
  const { data } = await apiClient.get<Circuito>("/pickleball/circuito", { params: { anno, categoria } });
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

export async function fetchClassificaCompleta(
  formato: Formato,
  filtri: FiltriClassifica = {},
): Promise<RigaClassifica[]> {
  const { data } = await apiClient.get<RigaClassifica[]>("/dirigenza/pickleball/classifica", {
    params: { formato, ...filtri },
  });
  return data;
}

export async function fetchCircuitoCompleto(anno?: string, categoria?: string): Promise<Circuito> {
  const { data } = await apiClient.get<Circuito>("/dirigenza/pickleball/circuito", { params: { anno, categoria } });
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

// ─── Tornei, ospiti, impostazioni (dirigenza) ─────────────────────────────

export type Livello = "sociale" | "open" | "federale";
export type Piazzamento = "vincitore" | "finalista" | "semifinalista" | "fase_finale" | "partecipazione" | "nessuno";

export const ETICHETTA_PIAZZAMENTO: Record<Piazzamento, string> = {
  vincitore: "Vincitore",
  finalista: "Finalista",
  semifinalista: "Semifinalista",
  fase_finale: "Fase finale",
  partecipazione: "Partecipazione",
  nessuno: "Nessun punto",
};

export const ETICHETTA_FASE: Record<string, string> = {
  girone: "Girone",
  ottavi: "Ottavi",
  quarti: "Quarti",
  semifinale: "Semifinale",
  finale: "Finale",
  altro: "Altro",
};

export interface Torneo {
  id: string;
  nome: string;
  data: string;
  luogo: string | null;
  livello: Livello;
  anno_sportivo: string;
  concluso: boolean;
  url_esterno: string | null;
  note: string | null;
  partite: number;
  categorie: string[];
}

export interface PiazzamentoTorneo {
  giocatore_id: string;
  nome: string;
  ospite: boolean;
  categoria: string;
  piazzamento: Piazzamento;
  punti: number;
  manuale: boolean;
}

export interface TorneoDettaglio {
  torneo: Torneo;
  partite: Partita[];
  piazzamenti: PiazzamentoTorneo[];
}

export interface TorneoInput {
  nome: string;
  data: string;
  luogo?: string | null;
  livello: Livello;
  url_esterno?: string | null;
  note?: string | null;
}

export interface RigaImport {
  riga: number;
  categoria: string;
  fase: string;
  squadra_a: { nome: string; tipo: "socio" | "ospite" | "nuovo_ospite" }[];
  squadra_b: { nome: string; tipo: "socio" | "ospite" | "nuovo_ospite" }[];
  punteggio: string;
  vincitore: string | null;
  walkover: boolean;
  esito: "ok" | "errore" | "saltata" | "gia_importata";
  messaggio: string | null;
}

export interface ImportRisultati {
  righe: RigaImport[];
  da_importare: number;
  errori: number;
  saltate: number;
  gia_importate: number;
  nuovi_ospiti: string[];
  importate: number;
}

export interface Ospite {
  id: string;
  nome: string;
  cognome: string;
  club: string | null;
  email: string | null;
  sesso: "M" | "F" | null;
  anno_nascita: number | null;
  invitato_at: string | null;
  partite: number;
  rating_singolo: number | null;
  rating_doppio: number | null;
}

export interface ConfigPickleball {
  peso_torneo: number;
  amichevoli_max_settimana: number;
  giorni_inattivita: number;
  migliori_risultati: number;
  punti: Record<Exclude<Piazzamento, "nessuno">, number>;
  livelli: Record<Livello, number>;
}

export interface RigaCircuito {
  posizione: number;
  giocatore_id: string;
  nome: string;
  ospite: boolean;
  punti: number;
  tornei: number;
  risultati: { torneo_id: string; torneo: string; data: string; piazzamento: Piazzamento; punti: number; conta: boolean }[];
}

export interface Circuito {
  anno_sportivo: string | null;
  categoria: string | null;
  anni: string[];
  categorie: string[];
  migliori_risultati: number;
  righe: RigaCircuito[];
}

export async function fetchTornei(): Promise<Torneo[]> {
  const { data } = await apiClient.get<Torneo[]>("/dirigenza/pickleball/tornei");
  return data;
}

export async function creaTorneo(input: TorneoInput): Promise<Torneo> {
  const { data } = await apiClient.post<Torneo>("/dirigenza/pickleball/tornei", input);
  return data;
}

export async function aggiornaTorneo(id: string, input: Partial<TorneoInput> & { concluso?: boolean }): Promise<Torneo> {
  const { data } = await apiClient.put<Torneo>(`/dirigenza/pickleball/tornei/${id}`, input);
  return data;
}

export async function eliminaTorneo(id: string): Promise<void> {
  await apiClient.delete(`/dirigenza/pickleball/tornei/${id}`);
}

export async function fetchTorneo(id: string): Promise<TorneoDettaglio> {
  const { data } = await apiClient.get<TorneoDettaglio>(`/dirigenza/pickleball/tornei/${id}`);
  return data;
}

export async function importaRisultati(id: string, file: File, conferma: boolean): Promise<ImportRisultati> {
  const form = new FormData();
  form.append("file", file);
  form.append("conferma", String(conferma));
  const { data } = await apiClient.post<ImportRisultati>(`/dirigenza/pickleball/tornei/${id}/import`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function ricalcolaPiazzamenti(id: string): Promise<PiazzamentoTorneo[]> {
  const { data } = await apiClient.post<PiazzamentoTorneo[]>(`/dirigenza/pickleball/tornei/${id}/piazzamenti/ricalcola`);
  return data;
}

export async function impostaPiazzamento(
  id: string,
  input: { categoria: string; giocatore_id: string; piazzamento: Piazzamento },
): Promise<PiazzamentoTorneo[]> {
  const { data } = await apiClient.put<PiazzamentoTorneo[]>(`/dirigenza/pickleball/tornei/${id}/piazzamenti`, input);
  return data;
}

export async function fetchOspiti(): Promise<Ospite[]> {
  const { data } = await apiClient.get<Ospite[]>("/dirigenza/pickleball/ospiti");
  return data;
}

export async function aggiornaOspite(
  id: string,
  input: Partial<Pick<Ospite, "nome" | "cognome" | "club" | "email" | "sesso" | "anno_nascita">>,
): Promise<Ospite> {
  const { data } = await apiClient.put<Ospite>(`/dirigenza/pickleball/ospiti/${id}`, input);
  return data;
}

export async function eliminaOspite(id: string): Promise<void> {
  await apiClient.delete(`/dirigenza/pickleball/ospiti/${id}`);
}

export async function invitaOspite(id: string): Promise<Ospite> {
  const { data } = await apiClient.post<Ospite>(`/dirigenza/pickleball/ospiti/${id}/invita`);
  return data;
}

export async function collegaOspite(id: string, socioId: string): Promise<void> {
  await apiClient.post(`/dirigenza/pickleball/ospiti/${id}/collega`, { socio_id: socioId });
}

export async function fetchConfigPickleball(): Promise<ConfigPickleball> {
  const { data } = await apiClient.get<ConfigPickleball>("/dirigenza/pickleball/config");
  return data;
}

export async function salvaConfigPickleball(input: ConfigPickleball): Promise<ConfigPickleball> {
  const { data } = await apiClient.put<ConfigPickleball>("/dirigenza/pickleball/config", input);
  return data;
}

// ─── Formattazione ────────────────────────────────────────────────────────

export function formattaPunteggi(p: Partita, dalLatoDi?: "a" | "b"): string {
  if (p.walkover) return "a tavolino";
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
