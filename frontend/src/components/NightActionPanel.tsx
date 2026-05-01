interface Props {
  nightInfo: string | undefined;
  currentThinking: string | null;
}

export default function NightActionPanel({ nightInfo, currentThinking }: Props) {
  return (
    <div style={{ padding: 16, border: '1px solid #444', borderRadius: 8, background: '#0a0a1e' }}>
      <h4 style={{ color: '#7b1fa2' }}>夜晚阶段</h4>
      {nightInfo && <div style={{ marginBottom: 12, fontSize: 14, color: '#ccc' }}>{nightInfo}</div>}
      {currentThinking && (
        <div style={{ padding: 12, background: '#111', borderRadius: 4, whiteSpace: 'pre-wrap', fontSize: 14, color: '#aaa' }}>
          {currentThinking}
        </div>
      )}
      {!nightInfo && !currentThinking && <p style={{ color: '#666' }}>夜晚行动进行中...</p>}
    </div>
  );
}
