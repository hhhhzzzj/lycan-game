import { useEffect, useRef } from 'react';

const API_BASE = 'http://localhost:8000';

interface Options {
    gameId: string | null;
    waiting: boolean;
    enabled: boolean;
    interval: number; // ms
}

export function useAutoPlay({ gameId, waiting, enabled, interval }: Options) {
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        if (!enabled || !gameId || !waiting) {
            if (timerRef.current) {
                clearTimeout(timerRef.current);
                timerRef.current = null;
            }
            return;
        }

        timerRef.current = setTimeout(async () => {
            try {
                await fetch(`${API_BASE}/game/${gameId}/continue`, { method: 'POST' });
            } catch {
                // ignore
            }
        }, interval);

        return () => {
            if (timerRef.current) {
                clearTimeout(timerRef.current);
                timerRef.current = null;
            }
        };
    }, [enabled, gameId, waiting, interval]);
}
