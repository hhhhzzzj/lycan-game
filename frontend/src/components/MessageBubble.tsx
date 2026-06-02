import { motion } from 'framer-motion';
import type { Speech } from '../types/game';

interface Props {
    speech: Speech;
}

export default function MessageBubble({ speech }: Props) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="p-2.5 px-3.5 rounded border"
            style={{
                background: 'var(--bg-card)',
                borderColor: 'var(--border)',
                borderLeft: '3px solid var(--gold-dim)',
            }}
        >
            {/* Header */}
            <div className="flex items-center gap-2 mb-1">
                <span
                    className="px-1.5 py-px text-[10px] font-bold rounded"
                    style={{ background: 'var(--blood)', color: '#ddd' }}
                >
                    {speech.seat_id}号
                </span>
                <span className="text-xs font-bold" style={{ color: 'var(--text-accent)' }}>
                    {speech.player_name}
                </span>
            </div>

            {/* Content */}
            <div className="text-[13px] leading-relaxed">{speech.content}</div>

            {/* Folded thinking */}
            {speech.thinking && (
                <details className="mt-1.5">
                    <summary
                        className="text-[11px] cursor-pointer px-1.5 py-0.5 rounded inline-block"
                        style={{ color: 'var(--text-muted)', background: 'rgba(0,0,0,0.2)' }}
                    >
                        💭 思考过程
                    </summary>
                    <div
                        className="mt-1 p-2 text-[11px] italic rounded"
                        style={{
                            color: 'var(--text-muted)',
                            background: 'rgba(0,0,0,0.3)',
                            borderLeft: '2px solid rgba(201,168,76,0.2)',
                        }}
                    >
                        {speech.thinking}
                    </div>
                </details>
            )}
        </motion.div>
    );
}
