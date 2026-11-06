export type ConsultType = 'directa' | 'indirecta';

export interface RecordInput {
  record_date: string;
  consult_type: ConsultType;
  full_name: string;
  address: string | null;
  dni: string | null;
  kinship: string | null;
  consultation: string;
  referral: string | null;
}

export interface ListeningRecord extends RecordInput {
  id: number;
  created_at: string;
}
