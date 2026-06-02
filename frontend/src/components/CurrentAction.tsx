import type { Player } from '../types/game';

interface Props {
    phase: string;
    currentSpeaker: number | null;
    currentThinking: string | null;
    currentSpeech?: string;
    nightInfo?: string;
    phaseInfo?: string;
    players: Player[];
}

export default function CurrentAction({ phase, currentSpeaker, currentThinking, currentSpeech, nightInfo, phaseInfo, players }: Props) {
    const isNight = phase === 'night';
    const speaker = players.find(p => p.seat_id === currentSpeaker);

    // Determine header
    let icon = '💬';
    let title = 'AI 思考中...';
    if (phaseInfo) {
        title = phaseInfo;
        icon = phase === 'vote' || phase === 'revote' ? '🗳' : '📢';
    } else if (nightInfo) {
        title = nightInfo;
        icon = '🌙';
    } else if (speaker) {
        if (isNight) {
            icon = speaker.role === 'werewolf' ? '🐺' : speaker.role === 'prophet' ? '👁' : speaker.role === 'witch' ? '🧪' : '🌙';
            title = `${speaker.seat_id}号 ${speaker.player_name} · ${isNight ? '夜间行动' : '发言'}`;
        } else {
            icon = '💬';
            title = `${speaker.seat_id}号 ${speaker.player_name} · 发言`;
        }
    }

    return (
        <div
            className="p-3.5 mb-2.5 rounded-md border transition-all duration-500"
            style={{
                background: isNight
                    ? 'linear-gradient(135deg, rgba(107,26,26,0.12), rgba(10,8,6,0.9))'
                    : 'linear-gradient(135deg, rgba(201,168,76,0.08), rgba(20,16,10,0.9))',
                borderColor: isNight ? 'rgba(107,26,26,0.25)' : 'rgba(201,168,76,0.2)',
            }}
        >
            {/* Header */}
            <div className="text-sm font-bold mb-2">
                <span className="mr-2">{icon}</span>{title}
            </div>

            {/* Thinking */}
            {currentThinking && (
                <div className="mb-2">
                    <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>💭 内心独白</span>
                    <p
                        className="mt-1 p-2.5 text-xs italic leading-relaxed rounded max-h-[70px] overflow-y-auto"
                        style={{
                            color: 'var(--text-muted)',
                            background: 'rgba(0,0,0,0.3)',
                            borderLeft: '2px solid var(--blood)',
                        }}
                    >
                        {currentThinking}
                    </p>
                </div>
            )}

            {/* Speech */}
            {currentSpeech && (
                <div>
                    <span className="text-[11px]" style={{ color: 'var(--text-accent)' }}>🗣 公开发言</span>
                    <p
                        className="mt-1 p-2.5 text-[13px] leading-relaxed rounded"
                        style={{
                            background: 'rgba(201,168,76,0.05)',
                            borderLeft: '2px solid var(--gold-dim)',
                        }}
                    >
                        {currentSpeech}
                    </p>
                </div>
            )}

            {/* No action state */}
            {!currentThinking && !currentSpeech && !phaseInfo && !nightInfo && (
                <div className="text-xs italic" style={{ color: 'var(--text-muted)' }}>
                    等待 AI 思考中...
                </div>
            )}
        </div>
    );
}
