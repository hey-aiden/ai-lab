// 左侧会话列表。跟随当前模态显示对应的会话,支持切换与新建。
export default function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onCreate,
}) {
  return (
    <aside className="conversation-sidebar">
      <button className="new-chat-btn" onClick={onCreate}>
        + 新建对话
      </button>

      <div className="conversation-list">
        {conversations.length === 0 && (
          <p className="conversation-list__empty">暂无会话</p>
        )}
        {conversations.map((c) => (
          <button
            key={c.id}
            className={`conversation-item${c.id === activeId ? ' is-active' : ''}`}
            onClick={() => onSelect(c.id)}
          >
            <span className="conversation-item__title">{c.title}</span>
            <span className="conversation-item__meta">{c.messages.length} 条消息</span>
          </button>
        ))}
      </div>
    </aside>
  );
}
