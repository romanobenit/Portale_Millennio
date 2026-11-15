import { apiClient } from "./client";

export type Sport =
  | "kung_fu"
  | "pallavolo"
  | "badminton"
  | "pickleball"
  | "tornei_pickleball"
  | "basket_serale"
  | "calcio_a_5";
export type Fonte = "meta_ads" | "organico" | "torneo" | "passaggio_struttura" | "passaparola" | "altro";
export type Canale = "whatsapp" | "email" | "instagram";
export type Stato = "lead" | "prova_prenotata" | "prova_svolta" | "iscritto" | "pagato" | "perso";
export type Abbonamento = "mensile" | "annuale";

// Le tendine del brief, nello stesso ordine
export const SPORT: [Sport, string][] = [
  ["kung_fu", "Wushu/Kung Fu"],
  ["pallavolo", "Pallavolo"],
  ["badminton", "Badminton"],
  ["pickleball", "Pickleball"],
  ["tornei_pickleball", "Tornei Pickleball"],
  ["basket_serale", "Turno basket serale"],
  ["calcio_a_5", "Calcio a 5"],
];
export const FONTI: [Fonte, string][] = [
  ["meta_ads", "Meta Ads"],
  ["organico", "Organico"],
  ["torneo", "Torneo"],
  ["passaggio_struttura", "Passaggio in struttura"],
  ["passaparola", "Passaparola"],
  ["altro", "Altro"],
];
export const CANALI: [Canale, string][] = [
  ["whatsapp", "WhatsApp"],
  ["email", "Email"],
  ["instagram", "Instagram"],
];
export const STATI: [Stato, string][] = [
  ["lead", "Lead"],
  ["prova_prenotata", "Prova prenotata"],
  ["prova_svolta", "Prova svolta"],
  ["iscritto", "Iscritto"],
  ["pagato", "Pagato"],
  ["perso", "Perso"],
];
export const ABBONAMENTI: [Abbonamento, string][] = [
  ["mensile", "Mensile"],
  ["annuale", "Annuale"],
];

const mappa = <K extends string>(coppie: [K, string][]) => Object.fromEntries(coppie) as Record<K, string>;
export const ETICHETTA_SPORT = mappa(SPORT);
export const ETICHETTA_FONTE = mappa(FONTI);
export const ETICHETTA_CANALE = mappa(CANALI);
export const ETICHETTA_STATO = mappa(STATI);
export const ETICHETTA_ABBONAMENTO = mappa(ABBONAMENTI);

export interface MeTracker {
  id: string;
  nome: string;
  ruolo: string;
  dirigenza: boolean;
}

export interface Membro {
  id: string;
  nome: string;
  ruolo: string;
}

export interface Contatto {
  id: string;
  data_contatto: string;
  sport: Sport;
  fonte: Fonte;
  nome: string;
  canale: Canale | null;
  recapito: string | null;
  stato: Stato;
  data_prova: string | null;
  tipo_abbonamento: Abbonamento | null;
  importo_eur: string | null;
  responsabile_id: string | null;
  responsabile_nome: string | null;
  prossimo_followup: string | null;
  note: string | null;
  is_test: boolean;
  created_at: string;
  updated_at: string;
}

export interface ContattoDettaglio extends Contatto {
  storico: { stato: Stato; cambiato_at: string; cambiato_da: string | null }[];
}

export interface ContattoInput {
  data_contatto: string;
  sport: Sport;
  fonte: Fonte;
  nome: string;
  canale: Canale | null;
  recapito: string | null;
  stato: Stato;
  data_prova: string | null;
  tipo_abbonamento: Abbonamento | null;
  importo_eur: number | null;
  responsabile_id: string | null;
  prossimo_followup: string | null;
  note: string | null;
  is_test: boolean;
}

export interface ListaContatti {
  contatti: Contatto[];
  totale: number;
  page: number;
  limit: number;
}

export interface FiltriContatti {
  q?: string;
  sport?: Sport | "";
  fonte?: Fonte | "";
  stato?: Stato | "";
  responsabile_id?: string;
  test?: boolean;
  page?: number;
  limit?: number;
}

export interface RigaRiepilogo {
  sport: Sport | "totale";
  lead: number;
  prove_prenotate: number;
  prove_svolte: number;
  iscritti: number;
  paganti: number;
  persi: number;
  conversione_pct: string | null;
  incassato_eur: string;
  impegnato_eur: string;
  costo_istruttore_eur: string | null; // null nella vista per fonte
  margine_eur: string | null;
}

export interface Riepilogo {
  fonte: Fonte | null;
  dal: string | null;
  al: string | null;
  solo_test: boolean;
  righe: RigaRiepilogo[];
  totale: RigaRiepilogo;
}

export interface CostoIstruttore {
  id: string;
  sport: Sport;
  valido_dal: string;
  costo_mensile_eur: string;
}

/** Toglie i parametri vuoti, così la query resta pulita. */
function pulisci<T extends object>(params: T): Partial<T> {
  return Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v !== undefined && v !== null)) as Partial<T>;
}

export async function fetchMeTracker(): Promise<MeTracker> {
  const { data } = await apiClient.get<MeTracker>("/tracker/me");
  return data;
}

export async function fetchMembri(): Promise<Membro[]> {
  const { data } = await apiClient.get<Membro[]>("/tracker/membri");
  return data;
}

export async function fetchContatti(filtri: FiltriContatti): Promise<ListaContatti> {
  const { data } = await apiClient.get<ListaContatti>("/tracker/contatti", { params: pulisci(filtri) });
  return data;
}

export async function fetchContatto(id: string): Promise<ContattoDettaglio> {
  const { data } = await apiClient.get<ContattoDettaglio>(`/tracker/contatti/${id}`);
  return data;
}

export async function cercaDoppioni(nome: string, escludiId?: string): Promise<Contatto[]> {
  const { data } = await apiClient.get<Contatto[]>("/tracker/contatti/doppioni", {
    params: pulisci({ nome, escludi_id: escludiId }),
  });
  return data;
}

export async function creaContatto(input: ContattoInput): Promise<Contatto> {
  const { data } = await apiClient.post<Contatto>("/tracker/contatti", input);
  return data;
}

export async function aggiornaContatto(id: string, input: Partial<ContattoInput>): Promise<Contatto> {
  const { data } = await apiClient.patch<Contatto>(`/tracker/contatti/${id}`, input);
  return data;
}

/** Solo dirigenza, solo se l'interessato chiede di essere rimosso. */
export async function cancellaContatto(id: string): Promise<void> {
  await apiClient.delete(`/tracker/contatti/${id}`);
}

/** Solo dirigenza: contatti passati a "perso" entro `finoAl`. Senza conferma restituisce solo quanti sono. */
export async function cancellaPersi(
  finoAl: string,
  conferma: boolean,
): Promise<{ fino_al: string; contatti: number; cancellati: boolean }> {
  const { data } = await apiClient.post("/tracker/persi/cancella", { fino_al: finoAl, conferma });
  return data;
}

export async function fetchMieiFollowup(): Promise<Contatto[]> {
  const { data } = await apiClient.get<Contatto[]>("/tracker/follow-up");
  return data;
}

export async function fetchRiepilogo(params: {
  fonte?: Fonte;
  dal?: string;
  al?: string;
  test?: boolean;
}): Promise<Riepilogo> {
  const { data } = await apiClient.get<Riepilogo>("/tracker/riepilogo", { params: pulisci(params) });
  return data;
}

export async function fetchCostiIstruttore(): Promise<CostoIstruttore[]> {
  const { data } = await apiClient.get<CostoIstruttore[]>("/tracker/costi-istruttore");
  return data;
}

export async function impostaCostoIstruttore(input: {
  sport: Sport;
  valido_dal: string;
  costo_mensile_eur: number;
}): Promise<CostoIstruttore> {
  const { data } = await apiClient.post<CostoIstruttore>("/tracker/costi-istruttore", input);
  return data;
}

export async function eliminaCostoIstruttore(id: string): Promise<void> {
  await apiClient.delete(`/tracker/costi-istruttore/${id}`);
}

// ── formattazione ────────────────────────────────────────────────────────────

export function formattaData(iso: string | null): string {
  return iso ? new Date(`${iso}T00:00:00`).toLocaleDateString("it-IT") : "—";
}

export function oggiIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Parole che fanno pensare a dati di salute: nelle note non vanno scritti. */
const PAROLE_SALUTE =
  /certificat|infortun|patolog|malatti|operat[oa]|operazion|frattur|diabet|cardi|asma|allergi|gravidanz|disabil|terapi|farmac|medic/i;

export function sembraDatoDiSalute(testo: string): boolean {
  return PAROLE_SALUTE.test(testo);
}
