// 中央消息历史。展示当前会话的全部消息,区分 user / assistant。
export default function MessageList({ messages }) {
  if (messages.length === 0) {
    return (
      <div className="message-list message-list--empty">
        <p className="message-list__hint">开始一段新对话吧</p>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((m) => (
        <div key={m.id} className={`message message--${m.role}`}>
          <div className="message__role" aria-hidden="true">
            {m.role === 'user' ? '你' : 'AI'}
          </div>
          <div className="message__bubble">{m.content}</div>
        </div>
      ))}
    </div>
  );
}
