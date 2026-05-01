interface Props {
  currentSpeaker: number | null;
  currentThinking: string | null;
  currentSpeech: string | null;
}

export default function SpeechPanel({ currentSpeaker, currentThinking, currentSpeech }: Props) {
  if (currentSpeaker === null) {
    return <div style={{ padding: 16, border: '1px solid #444', borderRadius: 8 }}><p>等待游戏开始...</p></div>;
  }

  return (
    <div style={{ padding: 16, border: '1px solid #444', borderRadius: 8 }}>
      <h3>当前发言：{currentSpeaker}号玩家</h3>
      {currentThinking && (
        <div style={{ marginBottom: 16 }}>
          <h4 style={{ color: '#888' }}>思考过程</h4>
          <div style={{ padding: 12, background: '#111', borderRadius: 4, whiteSpace: 'pre-wrap', fontSize: 14, color: '#aaa', maxHeight: 200, overflowY: 'auto' }}>
            {currentThinking}
          </div>
        </div>
      )}
      {currentSpeech && (
        <div>
          <h4 style={{ color: '#888' }}>发言内容</h4>
          <div style={{ padding: 12, background: '#1a1a2e', borderRadius: 4, fontSize: 16, color: '#fff', border: '1px solid gold' }}>
            {currentSpeech}
          </div>
        </div>
      )}
    </div>
  );
}
