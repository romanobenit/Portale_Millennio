import { apiClient } from "./client";

export interface SlotDisponibilita {
  slot_id: string;
  data: string;           // YYYY-MM-DD
  fascia: "notte" | "mattina" | "pomeriggio";
  ora_inizio: string;     // HH:MM:SS
  ora_fine: string;
  ore_totali: number;
  ore_vendute: number[];  // es. [0,1,2] = quelle ore già vendute
  ore_in_lock: number[];  // ore in lock da altri utenti
  ore_libere: number[];   // ore ancora selezionabili
  stato: "libero" | "parziale" | "esaurito" | "bloccato";
  prezzo_ora: number;
  moltiplicatore_data: number;
  moltiplicatore_scarsita: number;
  sconto_promo_pct: number;
}

export interface OreSelezione {
  slot_id: string;
  ore: number[];
}

export interface DettaglioSlot {
  slot_id: string;
  fascia: string;
  data: string;
  ore_selezionate: number[];
  n_ore: number;
  tariffa_base: number;
  moltiplicatore_data: number;
  moltiplicatore_scarsita: number;
  sconto_promo_pct: number;
  prezzo_ora: number;
  costo_slot: number;
}

export interface RiepilogoSelezione {
  selezione: OreSelezione[];
  ore_notte: number;
  ore_mattina: number;
  ore_pomeriggio: number;
  costo_totale: number;
  dettaglio: DettaglioSlot[];
}

export async function fetchDisponibilita(params: {
  data_inizio?: string;
  data_fine?: string;
}): Promise<SlotDisponibilita[]> {
  const { data } = await apiClient.get<SlotDisponibilita[]>("/calendario/disponibilita", { params });
  return data;
}

export async function lockSelezione(selezione: OreSelezione[]): Promise<RiepilogoSelezione> {
  const { data } = await apiClient.post<RiepilogoSelezione>("/calendario/lock", { selezione });
  return data;
}
