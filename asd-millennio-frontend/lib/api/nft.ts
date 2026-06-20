import { apiClient } from "./client";

export interface AcquistoNFTResponse {
  id: string;
  stripe_session_id: string;
  stripe_checkout_url: string;
  importo_eur: number;
  slot_count: number;
}

export interface DashboardFundraising {
  totale_raccolto_eur: number;
  obiettivo_eur: number;
  percentuale: number;
  nft_emessi_totali: number;
  nft_per_fascia: Record<string, number>;
}

export async function avviaAcquistoNFT(payload: {
  selezione: { slot_id: string; ore: number[] }[];
  acquisto_per_minore?: boolean;
  minore_id?: string;
}): Promise<AcquistoNFTResponse> {
  const { data } = await apiClient.post<AcquistoNFTResponse>("/nft/acquisto", payload);
  return data;
}

export async function fetchDashboardFundraising(): Promise<DashboardFundraising> {
  const { data } = await apiClient.get<DashboardFundraising>("/nft/dashboard");
  return data;
}

export async function verificaAccesso(tokenId: number, slotKey: string) {
  const { data } = await apiClient.get("/nft/verify", {
    params: { token_id: tokenId, slot_key: slotKey },
  });
  return data;
}
