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
    if (!sheetId) return;
    setStatus('loading');
    setError(null);
    try {
      const [nextSheet, nextVersions] = await Promise.all([fetchClinicalSheet(sheetId), fetchClinicalVersions(sheetId)]);
      setSheet(nextSheet);
      setVersions(nextVersions);
      setStatus('ready');
    } catch (error: unknown) {
      const message =
        typeof error === 'object' && error && 'response' in error
          ? String((error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to load sheet')
          : error instanceof Error
            ? error.message
            : 'Failed to load sheet';
      setStatus('error');
      setError(message);
    }
  }, [sheetId]);

  useEffect(() => {
    if (!sheetId) return;
    // Initial load is intentional here; refresh encapsulates the async fetch lifecycle for the sheet view.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [sheetId, refresh]);

  const toc = useMemo(() => deriveToc(sheet), [sheet]);
  const evidenceSummary = useMemo(() => deriveEvidenceSummary(sheet), [sheet]);

  const openVersion = useCallback((id: string) => navigate(`/clinical/sheets/${id}`), [navigate]);

  return { sheet, versions, status, error, toc, evidenceSummary, refresh, openVersion };
}
