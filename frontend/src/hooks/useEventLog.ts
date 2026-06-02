import { useEffect, useRef, useState } from 'react';
import type { PublicGameState } from '../types/game';
import type { GameEvent } from '../components/EventLog';

export function useEventLog(gameState: PublicGameState | null) {
    const [events, setEvents] = useState<GameEvent[]>([]);
    const prevPhaseRef = useRef<string | null>(null);
    const prevDayRef = useRef<number>(0);
    const prevKilledRef = useRef<number[]>([]);

    useEffect(() => {
        if (!gameState) return;
        const { phase, day, killed_last_night, winner, phase_info } = gameState;
        const newEvents: GameEvent[] = [];

        // Phase change
        if (prevPhaseRef.current !== phase) {
            if (phase === 'night' && day !== prevDayRef.current) {
                newEvents.push({ text: `🌙 第${day}夜`, type: 'night' });
            } else if (phase === 'day' && prevPhaseRef.current === 'night') {
                // Check killed
                if (killed_last_night.length > 0 && JSON.stringify(killed_last_night) !== JSON.stringify(prevKilledRef.current)) {
                    const names = killed_last_night.map(s => `${s}号`).join('、');
                    newEvents.push({ text: `☠ ${names}被杀害`, type: 'night' });
                    prevKilledRef.current = [...killed_last_night];
                } else if (killed_last_night.length === 0 && prevPhaseRef.current === 'night') {
                    newEvents.push({ text: '☀ 平安夜', type: 'day' });
                }
                newEvents.push({ text: `☀ 第${day}天·讨论`, type: 'day' });
            } else if (phase === 'vote') {
                newEvents.push({ text: `🗳 第${day}天·投票`, type: 'vote' });
            } else if (phase === 'game_over' && winner) {
                newEvents.push({ text: winner === 'werewolf' ? '🐺 狼人阵营胜利' : '🏆 好人阵营胜利', type: 'info' });
            }
            prevPhaseRef.current = phase;
            prevDayRef.current = day;
        }

        // Phase info events (e.g. "X号被放逐")
        if (phase_info && phase_info.includes('放逐')) {
            newEvents.push({ text: `⚰ ${phase_info}`, type: 'vote' });
        }

        if (newEvents.length > 0) {
            setEvents(prev => [...prev, ...newEvents]);
        }
    }, [gameState?.phase, gameState?.day, gameState?.killed_last_night, gameState?.phase_info, gameState?.winner]);

    return events;
}
