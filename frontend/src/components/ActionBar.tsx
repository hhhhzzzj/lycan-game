interface Props {
    waiting: boolean;
    phase: string;
    onContinue: () => void;
    onSkip: () => void;
}

export default function ActionBar({ waiting, phase, onContinue, onSkip }: Props) {
    const showSkip = phase !== 'vote' && phase !== 'revote' && phase !== 'game_over' && phase !== 'game_init';

    return (
        <div
            className="flex items-center gap-3 pt-3 mt-2 border-t"
            style={{ borderColor: 'var(--border)' }}
        >
            <button
                onClick={onContinue}
                disabled={!waiting}
                className="px-7 py-2.5 text-sm font-bold rounded cursor-pointer transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none hover:enabled:-translate-y-px"
                style={{
                    background: 'linear-gradient(135deg, var(--blood), #8b2020)',
                    color: 'var(--text-primary)',
                    border: '1px solid rgba(201,168,76,0.2)',
                    fontFamily: 'var(--font-body)',
                }}
            >
                {waiting ? '继续 →' : 'AI 思考中...'}
            </button>

            {showSkip && (
                <button
                    onClick={onSkip}
                    className="px-4 py-2 text-xs rounded cursor-pointer transition-all duration-200 hover:text-[var(--text-accent)] hover:border-[var(--gold)]"
                    style={{
                        background: 'transparent',
                        color: 'var(--text-muted)',
                        border: '1px solid var(--border)',
                        fontFamily: 'var(--font-body)',
                    }}
                >
                    快进 ⏩
                </button>
            )}

            <span className="ml-auto text-[11px]" style={{ color: 'var(--text-muted)' }}>
                {phase === 'game_over' ? '游戏结束' : waiting ? '等待操作' : '处理中'}
            </span>
        </div>
    );
}
