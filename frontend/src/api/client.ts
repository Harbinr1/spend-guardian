import axios from 'axios';

const API_BASE = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// --- Types (matching backend Pydantic models) ---

export interface WasteFlag {
  flag_id: string;
  vendor_name: string;
  overlap_category: string;
  confidence_score: string;
  requires_human_review: boolean;
  reason: string;
  transaction_ids: string[];
  monthly_cost: number;
}

export interface Draft {
  draft_id: string;
  flag_id: string;
  recipient: string;
  subject: string;
  body: string;
  status: string;
  created_at?: string;
  sent_at?: string;
}

// --- 4 allowed API calls — this is the complete list ---

export const fetchFlags = (): Promise<{ waste_flags: WasteFlag[], warnings?: string[] }> =>
  api.get('/flags').then(res => res.data);

export const fetchDrafts = (): Promise<{ drafts: Draft[] }> =>
  api.get('/drafts').then(res => res.data);

export const createDraft = (flagId: string, recipient: string) =>
  api.post('/draft', { flag_id: flagId, recipient }).then(res => res.data);

export const approveDraft = (draftId: string) =>
  api.post('/approve', { draft_id: draftId }).then(res => res.data);

export const runSampleAudit = (): Promise<{ waste_flags: WasteFlag[], warnings?: string[] }> =>
  api.post('/audit/sample').then(res => res.data);

export const uploadCsvAudit = (file: File): Promise<{ waste_flags: WasteFlag[], warnings?: string[] }> => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/audit/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }).then(res => res.data);
};

export const fetchAuditProgress = (): Promise<{ stage: string, timestamp?: string }> =>
  api.get('/audit/progress').then(res => res.data);
