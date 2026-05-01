import { useEffect, useRef } from 'react';
import type { Speech } from '../types/game';

interface Props {
  speechHistory: Speech[];
}

export default function HistoryPanel({ speechHistory }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [speechHistory.length]);

  if (speechHistory.length === 0) {
    return (
      <div style={{ padding: 16, border: '1px solid #444', borderRadius: 8 }}>
        <h4>发言历史</h4>
        <p style={{ color: '#666' }}>暂无发言</p>
      </div>
    );
  }

  return (
    <div style={{ padding: 16, border: '1px solid #444', borderRadius: 8 }}>
      <h4>发言历史</h4>
      <div style={{ maxHeight: 400, overflowY: 'auto' }}>
        {speechHistory.map((s, idx) => (
          <div key={idx} style={{ marginBottom: 12, padding: 8, background: '#1a1a2e', borderRadius: 6 }}>
            <div style={{ fontSize: 13, color: '#888' }}>[{s.seat_id}号 {s.player_name}]</div>
            <div style={{ marginTop: 4, fontSize: 14, color: '#ddd' }}>{s.content}</div>
            <details style={{ marginTop: 6 }}>
              <summary style={{ fontSize: 12, color: '#666', cursor: 'pointer' }}>查看思考过程</summary>
              <div style={{ marginTop: 4, padding: 8, background: '#111', borderRadius: 4, fontSize: 13, color: '#999', whiteSpace: 'pre-wrap' }}>
                {s.thinking}
              </div>
            </details>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
