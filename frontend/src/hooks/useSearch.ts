import { useMemo, useState } from 'react';
import { api } from '../services/api';
import { useToast } from '../ui/Toast/ToastProvider';
import type { PaperSearchResult } from '../types/api';

export type DownloadInfo = {
  status: 'saved' | 'duplicate' | 'error';
  source_provider?: string | null;
  oa_url?: string | null;
  original_oa_url?: string | null;
  used_fallback?: boolean;
  error?: string | null;
};

export type SearchResponse = {
  count: number;
  results: PaperSearchResult[];
  query_translation?: string | null;
  cached: boolean;
  sources?: string[];
};

export type UseSearchReturn = {
  query: string;
  setQuery: (v: string) => void;
  maxResults: number;
  setMaxResults: (v: number) => void;
  loading: boolean;
  error: string | null;
  data: SearchResponse | null;
  setData: (d: SearchResponse | null) => void;
  downloadingKey: string | null;
  downloadResults: Record<string, DownloadInfo>;
  searchPage: number;
  setSearchPage: (v: number) => void;
  expandedAbstracts: Record<string, boolean>;
  toggleAbstract: (key: string) => void;
  selected: Record<string, boolean>;
  setSelected: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  selectedCount: number;
  canSearch: boolean;
  runSearch: (filtersPayload: Record<string, unknown> | undefined, onDone?: () => void) => Promise<void>;
  downloadOA: (r: PaperSearchResult) => Promise<void>;
  selectAllOA: () => void;
  clearSelection: () => void;
  selectedPapers: Array<{ pmid?: string; pmcid?: string; doi?: string; title: string; oa_url?: string }>;
  setError: (msg: string | null) => void;
};

export function useSearch(projectId: string | undefined): UseSearchReturn {
  const toast = useToast();

  const [query, setQuery] = useState('');
  const [maxResults, setMaxResults] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);
  const [downloadResults, setDownloadResults] = useState<Record<string, DownloadInfo>>({});
  const [searchPage, setSearchPage] = useState(0);
  const [expandedAbstracts, setExpandedAbstracts] = useState<Record<string, boolean>>({});
  const [selected, setSelected] = useState<Record<string, boolean>>({});

  const canSearch = useMemo(
    () => Boolean(projectId && query.trim().length >= 3),
    [projectId, query],
  );

  const selectedCount = useMemo(
    () => Object.values(selected).filter(Boolean).length,
    [selected],
  );

  const selectedPapers = useMemo(() => {
    if (!data) return [];
    return data.results
      .map((r, idx) => ({ r, idx }))
      .filter(({ r, idx }) => {
        const key = r.doi || r.pmid || String(idx);
        const canDl = Boolean(r.is_open_access) && Boolean(r.doi || r.pmid || r.oa_url);
        return Boolean(selected[key]) && canDl;
      })
      .map(({ r }) => ({
        pmid: r.pmid || undefined,
        pmcid: r.pmcid || undefined,
        doi: r.doi || undefined,
        title: r.title,
        oa_url: r.oa_url || undefined,
      }));
  }, [data, selected]);

  async function runSearch(
    filtersPayload: Record<string, unknown> | undefined,
    onDone?: () => void,
  ) {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        project_id: projectId,
        query: query.trim(),
        max_results: maxResults,
      };
      if (filtersPayload) payload.filters = filtersPayload;
      const r = await api.post('/search/federated', payload);
      setData(r.data as SearchResponse);
      setSelected({});
      setSearchPage(0);
      onDone?.();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  async function downloadOA(r: PaperSearchResult) {
    if (!projectId) return;
    const key = r.doi || r.pmid || r.title;
    setDownloadingKey(key);
    setError(null);
    try {
      const payload: Record<string, unknown> = { project_id: projectId, title: r.title };
      if (r.doi) payload.doi = r.doi;
      if (r.pmid) payload.pmid = r.pmid;
      if (r.oa_url) payload.oa_url = r.oa_url;

      const resp = await api.post('/papers/download', payload);
      const duplicate = Boolean(resp.data?.duplicate);
      const srcProvider: string | null = resp.data?.source_provider || null;
      const resolvedUrl: string | null = resp.data?.oa_url || null;
      const originalUrl: string | null = resp.data?.oa_url_provided ?? r.oa_url ?? null;
      // Trust the server's authoritative used_fallback flag; fall back to client-side heuristic
      // for duplicates (where the server returns null).
      const usedFallback: boolean = resp.data?.used_fallback ??
        Boolean(originalUrl && resolvedUrl && srcProvider !== 'user_provided_oa' && originalUrl !== resolvedUrl);

      setDownloadResults((prev) => ({
        ...prev,
        [key]: { status: duplicate ? 'duplicate' : 'saved', source_provider: srcProvider, oa_url: resolvedUrl, original_oa_url: originalUrl, used_fallback: usedFallback },
      }));

      const providerLabel =
        srcProvider === 'user_provided_oa' ? 'direct OA link'
        : srcProvider === 'unpaywall' ? 'Unpaywall'
        : srcProvider === 'europepmc' ? 'Europe PMC'
        : srcProvider;

      if (duplicate) {
        toast.info('Duplicate', 'Paper already exists in this project.');
      } else if (usedFallback) {
        toast.info('Downloaded (fallback)', `OA link failed. Resolved via ${providerLabel || 'resolver'}.`);
      } else {
        toast.info('Downloaded', providerLabel ? `Saved via ${providerLabel}` : 'Downloaded and saved.');
      }
    } catch (e: any) {
      const errMsg = e?.response?.data?.detail || 'Download failed';
      setDownloadResults((prev) => ({ ...prev, [key]: { status: 'error', error: errMsg } }));
      setError(errMsg);
    } finally {
      setDownloadingKey(null);
    }
  }

  function selectAllOA() {
    if (!data) return;
    const next: Record<string, boolean> = {};
    data.results.forEach((r, idx) => {
      const key = r.doi || r.pmid || String(idx);
      if (Boolean(r.is_open_access) && Boolean(r.doi || r.pmid || r.oa_url)) next[key] = true;
    });
    setSelected(next);
  }

  function toggleAbstract(key: string) {
    setExpandedAbstracts((p) => ({ ...p, [key]: !p[key] }));
  }

  return {
    query, setQuery,
    maxResults, setMaxResults,
    loading, error, setError,
    data, setData,
    downloadingKey, downloadResults,
    searchPage, setSearchPage,
    expandedAbstracts, toggleAbstract,
    selected, setSelected, selectedCount,
    canSearch, runSearch, downloadOA,
    selectAllOA, clearSelection: () => setSelected({}),
    selectedPapers,
  };
}
