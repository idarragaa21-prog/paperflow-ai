import { useState } from 'react';

export type SearchFilters = {
  yearFrom: string;
  yearTo: string;
  oaOnly: boolean;
  journalFilter: string;
  sourceFilter: string;
};

export type UseSearchFiltersReturn = SearchFilters & {
  setYearFrom: (v: string) => void;
  setYearTo: (v: string) => void;
  setOaOnly: (v: boolean) => void;
  setJournalFilter: (v: string) => void;
  setSourceFilter: (v: string) => void;
  showFilters: boolean;
  toggleFilters: () => void;
  buildPayload: () => Record<string, unknown> | undefined;
};

export function useSearchFilters(): UseSearchFiltersReturn {
  const [yearFrom, setYearFrom] = useState('');
  const [yearTo, setYearTo] = useState('');
  const [oaOnly, setOaOnly] = useState(false);
  const [journalFilter, setJournalFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  function buildPayload(): Record<string, unknown> | undefined {
    const f: Record<string, unknown> = {};
    const yf = parseInt(yearFrom, 10);
    const yt = parseInt(yearTo, 10);
    if (!isNaN(yf) && yf > 1900) f.year_from = yf;
    if (!isNaN(yt) && yt > 1900) f.year_to = yt;
    if (oaOnly) f.open_access_only = true;
    if (journalFilter.trim()) f.journal = journalFilter.trim();
    if (sourceFilter) f.source = sourceFilter;
    return Object.keys(f).length > 0 ? f : undefined;
  }

  return {
    yearFrom, setYearFrom,
    yearTo, setYearTo,
    oaOnly, setOaOnly,
    journalFilter, setJournalFilter,
    sourceFilter, setSourceFilter,
    showFilters,
    toggleFilters: () => setShowFilters((p) => !p),
    buildPayload,
  };
}
