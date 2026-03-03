import { useState, useEffect } from 'react';
import axios from 'axios';

export interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  isColdStart: boolean;
  refetch: () => void;
}

export function useApi<T>(url: string | null, deps: unknown[] = []): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isColdStart, setIsColdStart] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!url) return;
    let cancelled = false;
    const coldStartTimer = setTimeout(() => {
      if (!cancelled) setIsColdStart(true);
    }, 5000);

    setLoading(true);
    setError(null);

    axios
      .get<T>(url, { timeout: 60000 })
      .then((res) => {
        if (!cancelled) {
          setData(res.data);
          setIsColdStart(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message ?? 'Unknown error');
          setIsColdStart(false);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
        clearTimeout(coldStartTimer);
      });

    return () => {
      cancelled = true;
      clearTimeout(coldStartTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, tick, ...deps]);

  return { data, loading, error, isColdStart, refetch: () => setTick((t) => t + 1) };
}
