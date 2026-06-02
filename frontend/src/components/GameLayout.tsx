import { useState, useRef, useCallback } from 'react';
import type { PublicGameState } from '../types/game';
import GameBackground from './GameBackground';
import TopBar from './TopBar';
import PlayerPanel from './PlayerPanel';
import MainStage from './MainStage';
import InfoPanel from './InfoPanel';
import PostGameOverlay from './PostGameOverlay';
import { useEventLog } from '../hooks/useEventLog';
import { useAutoPlay } from '../hooks/useAutoPlay';

const API_BASE = 'http://localhost:8000';

interface Props {
    gameState: PublicGameState;
    gameId: string;
    connected: boolean;
}

export default function GameLayout({ gameState, gameId, connected }: Props) {
    const [autoPlay, setAutoPlay] = useState(false);
    const [showPostGame, setShowPostGame] = useState(false);
    const [skipping, setSkipping] = useState(false);
    const skipPhaseRef = useRef<string | null>(null);

    const { phase, day, players, current_speaker, votes, waiting } = gameState;
    const isNight = phase === 'night';
    const events = useEventLog(gameState);

    // Auto play
    useAutoPlay({ gameId, waiting: !!waiting, enabled: autoPlay, interval: 2500 });

    // Show postgame when game ends
    if (phase === 'game_over' && !showPostGame) {
        setTimeout(() => setShowPostGame(true), 600);
    }

    // Status text
    const getStatus = () => {
        if (gameState.phase_info) return gameState.phase_info;
        if (gameState.night_info) return gameState.night_info;
        if (gameState.vote_progress) return gameState.vote_progress;
        if (current_speaker) {
            const p = players.find(pl => pl.seat_id === current_speaker);
            return p ? `${p.player_name} 行动中...` : `${current_speaker}号 行动中`;
        }
        if (phase === 'night') return '🌙 夜深了，有人正在行动...';
        if (phase === 'day') return '☀ 白天讨论中';
        if (phase === 'vote' || phase === 'revote') return '🗳 投票进行中';
        return '';
    };

    const handleContinue = useCallback(async () => {
        try {
            await fetch(`${API_BASE}/game/${gameId}/continue`, { method: 'POST' });
        } catch (err) {
            console.error('Continue failed', err);
        }
    }, [gameId]);

    const handleSkip = useCallback(async () => {
        if (skipping) return;
        setSkipping(true);
        skipPhaseRef.current = phase;
        // Keep calling continue until phase changes
        const poll = async () => {
            for (let i = 0; i < 20; i++) {
                try {
                    await fetch(`${API_BASE}/game/${gameId}/continue`, { method: 'POST' });
                } catch { break; }
                // Wait a bit for WS to update
                await new Promise(r => setTimeout(r, 300));
                // Check if phase changed (we rely on next render to break)
            }
            setSkipping(false);
        };
        poll();
    }, [gameId, phase, skipping]);

    // Set body class for theme
    document.body.className = isNight ? 'night' : 'day';

    return (
        <div className="h-screen flex flex-col relative">
            <GameBackground isNight={isNight} />

            <div className="relative z-10 flex flex-col h-full">
                <TopBar
                    phase={phase}
                    day={day}
                    statusText={getStatus()}
                    connected={connected}
                    autoPlay={autoPlay}
                    onAutoPlayChange={setAutoPlay}
                />

                <main className="flex-1 flex overflow-hidden">
                    <PlayerPanel players={players} currentSpeaker={current_speaker} />
                    <MainStage gameState={gameState} onContinue={handleContinue} onSkip={handleSkip} />
                    <InfoPanel events={events} votes={votes} players={players} />
                </main>
            </div>

            <PostGameOverlay
                gameState={gameState}
                visible={showPostGame}
                onClose={() => setShowPostGame(false)}
            />
        </div>
    );
}
