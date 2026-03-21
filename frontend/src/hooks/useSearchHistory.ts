import { useCallback, useEffect, useState } from 'react';
import { api } from '../services/api';
import type { SearchRecord, PaperSearchResult } from '../types/api';

type SearchResponse = {
  count: number;
  results: PaperSearchResult[];
  query_translation?: string | null;
  cached: boolean;
  sources?: string[];
};

export type UseSearchHistoryReturn = {
  searchHistory: SearchRecord[];
  historyLoading: boolean;
  showHistory: boolean;
  setShowHistory: (v: boolean) => void;
  loadHistory: () => Promise<void>;
  reloadPastSearch: (searchId: string, pastQuery: string) => Promise<void>;
};

type Options = {
  projectId: string | undefined;
  onResults: (data: SearchResponse, query: string) => void;
  setLoading: (v: boolean) => void;
  setError: (msg: string | null) => void;
};

export function useSearchHistory({
  projectId,
  onResults,
  setLoading,
  setError,
}: Options): UseSearchHistoryReturn {
  const [searchHistory, setSearchHistory] = useState<SearchRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const loadHistory = useCallback(async () => {
    if (!projectId) return;
    setHistoryLoading(true);
    try {
      const r = await api.get(`/search/projects/${projectId}/searches`);
      setSearchHistory(r.data as SearchRecord[]);
    } catch {
      // non-blocking
    } finally {
      setHistoryLoading(false);
    }
  }, [projectId]);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  async function reloadPastSearch(searchId: string, pastQuery: string) {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const r = await api.get(`/search/${searchId}/results`);
      const results = r.data as PaperSearchResult[];
      onResults(
        { count: results.length, results, query_translation: null, cached: false, sources: [] },
        pastQuery,
      );
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load search results');
    } finally {
      setLoading(false);
    }
  }

  return {
    searchHistory,
    historyLoading,
    showHistory,
    setShowHistory,
    loadHistory,
    reloadPastSearch,
  };
}
