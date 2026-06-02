import { motion, AnimatePresence } from 'framer-motion';
import type { PublicGameState } from '../types/game';

interface Props {
    gameState: PublicGameState;
    visible: boolean;
    onClose: () => void;
}

const roleLabel = (role: string) => {
    switch (role) {
        case 'werewolf': return '狼人';
        case 'prophet': return '预言家';
        case 'witch': return '女巫';
        default: return '村民';
    }
};

const roleColor = (role: string) => {
    switch (role) {
        case 'werewolf': return '#e55';
        case 'prophet': return '#6af';
        case 'witch': return '#c6f';
        default: return 'var(--text-muted)';
    }
};

export default function PostGameOverlay({ gameState, visible, onClose }: Props) {
    const { winner, players } = gameState;
    const isWolfWin = winner === 'werewolf';

    return (
        <AnimatePresence>
            {visible && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 z-50 flex items-center justify-center"
                    style={{ background: 'rgba(0,0,0,0.88)', backdropFilter: 'blur(4px)' }}
                >
                    <motion.div
                        initial={{ scale: 0.95, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.95, opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="w-[580px] max-h-[80vh] overflow-y-auto p-8 rounded-lg border"
                        style={{
                            background: 'linear-gradient(135deg, rgba(30,24,18,0.98), rgba(15,12,8,0.98))',
                            borderColor: 'var(--gold-dim)',
                        }}
                    >
                        {/* Title */}
                        <h2 className="text-center text-[22px] mb-5" style={{ fontFamily: 'var(--font-title)', color: 'var(--gold)' }}>
                            ⚔ 战报卷轴
                        </h2>

                        {/* Result */}
                        <div
                            className="text-center text-base font-bold p-3 rounded-md mb-5"
                            style={{
                                background: isWolfWin ? 'rgba(107,26,26,0.3)' : 'rgba(76,175,80,0.12)',
                                color: isWolfWin ? 'var(--blood-glow)' : '#6fcf6f',
                            }}
                        >
                            {isWolfWin ? '🐺 狼人阵营胜利！' : '🏆 好人阵营胜利！'}
                        </div>

                        {/* Roles table */}
                        <table className="w-full text-xs mb-5" style={{ borderCollapse: 'collapse' }}>
                            <thead>
                                <tr>
                                    <th className="text-left p-1.5 border-b" style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}>座位</th>
                                    <th className="text-left p-1.5 border-b" style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}>玩家</th>
                                    <th className="text-left p-1.5 border-b" style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}>角色</th>
                                    <th className="text-left p-1.5 border-b" style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}>模型</th>
                                    <th className="text-left p-1.5 border-b" style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}>结局</th>
                                </tr>
                            </thead>
                            <tbody>
                                {players.map(p => (
                                    <tr key={p.seat_id}>
                                        <td className="p-1.5 border-b" style={{ borderColor: 'rgba(255,255,255,0.04)' }}>{p.seat_id}号</td>
                                        <td className="p-1.5 border-b" style={{ borderColor: 'rgba(255,255,255,0.04)' }}>{p.player_name}</td>
                                        <td className="p-1.5 border-b" style={{ borderColor: 'rgba(255,255,255,0.04)', color: roleColor(p.role) }}>{roleLabel(p.role)}</td>
                                        <td className="p-1.5 border-b" style={{ borderColor: 'rgba(255,255,255,0.04)' }}>{p.model_name}</td>
                                        <td className="p-1.5 border-b" style={{ borderColor: 'rgba(255,255,255,0.04)', color: p.is_alive ? '#6fcf6f' : 'var(--blood-glow)' }}>
                                            {p.is_alive ? '存活' : '死亡'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>

                        {/* Actions */}
                        <div className="flex gap-3 justify-center">
                            <button
                                onClick={() => location.reload()}
                                className="px-6 py-2 text-sm font-bold rounded cursor-pointer"
                                style={{
                                    background: 'linear-gradient(135deg, var(--blood), #8b2020)',
                                    color: 'var(--text-primary)',
                                    border: '1px solid rgba(201,168,76,0.2)',
                                    fontFamily: 'var(--font-body)',
                                }}
                            >
                                重开一局
                            </button>
                            <button
                                onClick={onClose}
                                className="px-5 py-2 text-xs rounded cursor-pointer"
                                style={{
                                    background: 'transparent',
                                    color: 'var(--text-muted)',
                                    border: '1px solid var(--border)',
                                    fontFamily: 'var(--font-body)',
                                }}
                            >
                                关闭
                            </button>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
