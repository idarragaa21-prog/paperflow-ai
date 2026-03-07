import { api } from './api';
import type { ClinicalSheetDetail, ClinicalSheetVersionRow } from '../domain/clinical/types';

export async function fetchClinicalSheet(sheetId: string): Promise<ClinicalSheetDetail> {
  const r = await api.get(`/clinical/${sheetId}`);
  return r.data as ClinicalSheetDetail;
}

export async function fetchClinicalVersions(sheetId: string): Promise<ClinicalSheetVersionRow[]> {
  const r = await api.get(`/clinical/sheets/${sheetId}/versions`);
  return r.data as ClinicalSheetVersionRow[];
}

export async function enqueueClinicalUpdate(sheetId: string): Promise<{ job_id: string }>{
  const r = await api.post(`/clinical/sheets/${sheetId}/update`, {});
  return { job_id: String((r.data as any)?.job_id || '') };
}
