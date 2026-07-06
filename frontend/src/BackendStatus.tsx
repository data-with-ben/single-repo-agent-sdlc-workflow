import { useEffect, useState } from 'react';
import { apiFetch } from './api';

type Status = 'loading' | 'ok' | 'unavailable';

function BackendStatus() {
  const [status, setStatus] = useState<Status>('loading');

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const response = await apiFetch('/health');
        if (!response.ok) throw new Error('Backend returned an error');
        await response.json();
        if (!cancelled) setStatus('ok');
      } catch {
        if (!cancelled) setStatus('unavailable');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  if (status === 'loading') return <p className="text-muted">Checking backend status...</p>;
  if (status === 'ok') return <p className="text-success">Backend: ok</p>;
  return <p className="text-danger">Backend unavailable</p>;
}

export default BackendStatus;
