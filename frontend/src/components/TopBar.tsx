interface Props {
    phase: string;
    day: number;
    statusText: string;
    connected: boolean;
    autoPlay: boolean;
    onAutoPlayChange: (v: boolean) => void;
}

export default function TopBar({ phase, day, statusText, connected, autoPlay, onAutoPlayChange }: Props) {
    const isNight = phase === 'night';
    const badgeText = phase === 'game_init' ? '等待开始'
        : phase === 'game_over' ? '结束'
            : phase === 'vote' || phase === 'revote' ? '投票'
                : isNight ? `第${day}夜` : `第${day}天`;

    return (
        <header
            className="h-12 flex items-center px-5 gap-4 border-b"
            style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}
        >
            <div className="flex items-center gap-3">
                <span className="font-[var(--font-title)] text-[15px] tracking-widest" style={{ color: 'var(--gold)', fontFamily: 'var(--font-title)' }}>
                    ☽ AI 狼人杀
                </span>
                <span
                    className="px-2.5 py-0.5 text-[11px] rounded font-bold"
                    style={{
                        background: isNight ? 'var(--blood)' : 'var(--gold-dim)',
                        color: '#eee',
                    }}
                >
                    {badgeText}
                </span>
            </div>

            <div className="flex-1 text-center text-xs tracking-wide" style={{ color: 'var(--text-muted)' }}>
                {statusText}
            </div>

            <div className="flex items-center gap-2.5">
                <span
                    className="w-[7px] h-[7px] rounded-full"
                    style={{
                        background: connected ? '#4caf50' : '#c62828',
                        boxShadow: connected ? '0 0 4px #4caf50' : 'none',
                    }}
                />
                <label className="flex items-center gap-1 text-[11px] cursor-pointer" style={{ color: 'var(--text-muted)' }}>
                    <input
                        type="checkbox"
                        checked={autoPlay}
                        onChange={e => onAutoPlayChange(e.target.checked)}
                        className="accent-[var(--gold)]"
                    />
                    自动播放
                </label>
            </div>
        </header>
    );
}
