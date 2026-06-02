import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import GameBackground from './GameBackground';

const API_BASE = 'http://localhost:8000';

interface PlayerDisplay {
    seat_id: number;
    player_name: string;
    model_name: string;
    provider: string;
}

interface Props {
    onGameStarted: (gameId: string) => void;
}

export default function WelcomePage({ onGameStarted }: Props) {
    const [players, setPlayers] = useState<PlayerDisplay[]>([]);
    const [loading, setLoading] = useState(true);
    const [starting, setStarting] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        fetch(`${API_BASE}/game/config`)
            .then(r => { if (!r.ok) throw new Error('加载配置失败'); return r.json(); })
            .then(d => setPlayers(d.players))
            .catch(e => setError(e.message))
            .finally(() => setLoading(false));
    }, []);

    const handleStart = async () => {
        setStarting(true);
        setError('');
        try {
            const res = await fetch(`${API_BASE}/game/start`, { method: 'POST' });
            if (!res.ok) { const e = await res.json(); throw new Error(e.detail || '启动失败'); }
            const data = await res.json();
            onGameStarted(data.game_id);
        } catch (e) {
            setError(e instanceof Error ? e.message : '未知错误');
        } finally {
            setStarting(false);
        }
    };

    return (
        <div className="h-screen flex items-center justify-center relative">
            <GameBackground isNight={true} />

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8 }}
                className="relative z-10 text-center max-w-[600px] px-6"
            >
                {/* Title */}
                <motion.h1
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 1, delay: 0.2 }}
                    className="text-4xl font-black tracking-widest mb-4"
                    style={{ fontFamily: 'var(--font-title)', color: 'var(--gold)', textShadow: '0 0 20px rgba(201,168,76,0.3)' }}
                >
                    AI 狼人杀
                </motion.h1>

                {/* Narrative */}
                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.6 }}
                    className="text-sm leading-relaxed mb-8"
                    style={{ color: 'var(--text-muted)' }}
                >
                    黑暗降临，六位命运之人齐聚诅咒之村。<br />
                    狼人潜伏其中，月光下的阴谋即将展开...<br />
                    作为观察者，你将见证 AI 之间的智慧博弈。
                </motion.p>

                {/* Player cards */}
                {loading ? (
                    <div className="text-xs" style={{ color: 'var(--text-muted)' }}>加载中...</div>
                ) : (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.9 }}
                        className="grid grid-cols-3 gap-3 mb-8"
                    >
                        {players.map(p => (
                            <div
                                key={p.seat_id}
                                className="p-3 rounded border text-center"
                                style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}
                            >
                                <div className="text-lg font-bold" style={{ color: 'var(--text-accent)' }}>{p.seat_id}号</div>
                                <div className="text-xs font-bold mt-1">{p.player_name}</div>
                                <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{p.model_name}</div>
                            </div>
                        ))}
                    </motion.div>
                )}

                {error && <div className="text-xs mb-4" style={{ color: 'var(--blood-glow)' }}>{error}</div>}

                {/* Start button */}
                <motion.button
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1.2 }}
                    onClick={handleStart}
                    disabled={starting || players.length === 0}
                    className="px-10 py-3 text-base font-bold rounded cursor-pointer transition-all duration-200 hover:-translate-y-0.5 disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{
                        background: 'linear-gradient(135deg, var(--blood), #8b2020)',
                        color: 'var(--text-primary)',
                        border: '1px solid rgba(201,168,76,0.3)',
                        fontFamily: 'var(--font-body)',
                        boxShadow: '0 4px 20px rgba(107,26,26,0.4)',
                    }}
                >
                    {starting ? '召唤中...' : '⚔ 开始游戏'}
                </motion.button>
            </motion.div>
        </div>
    );
}
