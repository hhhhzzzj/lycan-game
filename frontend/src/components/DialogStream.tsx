import { useEffect, useRef } from 'react';
import type { Speech } from '../types/game';
import MessageBubble from './MessageBubble';

interface Props {
    messages: Speech[];
}

export default function DialogStream({ messages }: Props) {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages.length]);

    if (messages.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <span className="text-xs italic" style={{ color: 'var(--text-muted)' }}>
                    暂无发言记录...
                </span>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto flex flex-col gap-2 py-1">
            {messages.map((s, i) => (
                <MessageBubble key={i} speech={s} />
            ))}
            <div ref={bottomRef} />
        </div>
    );
}
