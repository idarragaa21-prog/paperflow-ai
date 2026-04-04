import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { ClinicalSheetDetail, ClinicalSheetVersionRow, EvidenceSummary, TocItem } from '../types';
import { deriveEvidenceSummary, deriveToc } from '../selectors';
import { fetchClinicalSheet, fetchClinicalVersions } from '../../../services/clinical';

export type UseClinicalSheetStatus = 'idle' | 'loading' | 'ready' | 'error';

export function useClinicalSheet(sheetId: string | undefined): {
  sheet: ClinicalSheetDetail | null;
  versions: ClinicalSheetVersionRow[];
  status: UseClinicalSheetStatus;
  error: string | null;
  toc: TocItem[];
  evidenceSummary: EvidenceSummary;
  refresh: () => Promise<void>;
  openVersion: (id: string) => void;
} {
  const navigate = useNavigate();
  const [sheet, setSheet] = useState<ClinicalSheetDetail | null>(null);
  const [versions, setVersions] = useState<ClinicalSheetVersionRow[]>([]);
  const [status, setStatus] = useState<UseClinicalSheetStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!sheetId) {
      setSheet(null);
      setVersions([]);
      setStatus('idle');
      setError(null);
      return;
    }
    setStatus((s) => (s === 'idle' ? 'loading' : s));
    setError(null);
    try {
      const [s, v] = await Promise.all([fetchClinicalSheet(sheetId), fetchClinicalVersions(sheetId)]);
      setSheet(s);
      setVersions(v);
      setStatus('ready');
    } catch (e: any) {
      setStatus('error');
      setError(e?.response?.data?.detail || e?.message || 'Failed to load sheet');
    }
  }, [sheetId]);


  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (sheet?.input_params?.status === 'generating') {
      const timer = setTimeout(() => {
        void refresh();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [sheet, refresh]);


  const toc = useMemo(() => deriveToc(sheet), [sheet]);
  const evidenceSummary = useMemo(() => deriveEvidenceSummary(sheet), [sheet]);

  const openVersion = useCallback((id: string) => navigate(`/clinical/sheets/${id}`), [navigate]);

  return { sheet, versions, status, error, toc, evidenceSummary, refresh, openVersion };
}
