import { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  MODALITIES,
  DEFAULT_MODALITY_ID,
  INITIAL_CONVERSATIONS,
  createEmptyConversation,
  createMessage,
  PLACEHOLDER_REPLY,
} from '../data/modalities';
import ModalityTabs from '../components/ModalityTabs';
import ConversationSidebar from '../components/ConversationSidebar';
import MessageList from '../components/MessageList';
import MessageInput from '../components/MessageInput';
import './ChatPage.css';

// 每个模态默认选中的会话(取各自第一条)
function buildInitialActive() {
  const map = {};
  for (const [modalityId, { conversations }] of Object.entries(INITIAL_CONVERSATIONS)) {
    map[modalityId] = conversations[0]?.id ?? null;
  }
  return map;
}

export default function ChatPage() {
  const { modalityId } = useParams();

  // 模态由 URL 驱动;非法/缺失时回退到第一个
  const activeModality = MODALITIES.some((m) => m.id === modalityId)
    ? modalityId
    : DEFAULT_MODALITY_ID;

  // 按模态分桶的会话数据;当前选中会话每个模态各自记住
  const [conversationsByModality, setConversationsByModality] = useState(INITIAL_CONVERSATIONS);
  const [activeByModality, setActiveByModality] = useState(buildInitialActive);

  const conversations = conversationsByModality[activeModality].conversations;
  const activeConversationId = activeByModality[activeModality];
  const activeConversation = conversations.find((c) => c.id === activeConversationId);

  const handleSelect = (id) => {
    setActiveByModality((prev) => ({ ...prev, [activeModality]: id }));
  };

  const handleCreate = () => {
    const conv = createEmptyConversation();
    setConversationsByModality((prev) => ({
      ...prev,
      [activeModality]: { conversations: [conv, ...prev[activeModality].conversations] },
    }));
    setActiveByModality((prev) => ({ ...prev, [activeModality]: conv.id }));
  };

  const handleSend = (text) => {
    // 无会话时先新建一个,再追加消息
    let convId = activeConversationId;
    if (!convId) {
      const conv = createEmptyConversation();
      convId = conv.id;
      setConversationsByModality((prev) => ({
        ...prev,
        [activeModality]: { conversations: [conv, ...prev[activeModality].conversations] },
      }));
      setActiveByModality((prev) => ({ ...prev, [activeModality]: conv.id }));
    }

    const userMsg = createMessage('user', text, activeModality);
    const reply = createMessage('assistant', PLACEHOLDER_REPLY[activeModality], activeModality);

    setConversationsByModality((prev) => ({
      ...prev,
      [activeModality]: {
        conversations: prev[activeModality].conversations.map((c) => {
          if (c.id !== convId) return c;
          const isFirst = c.messages.length === 0;
          const title = isFirst
            ? text.length > 18
              ? `${text.slice(0, 18)}…`
              : text
            : c.title;
          return { ...c, title, messages: [...c.messages, userMsg, reply] };
        }),
      },
    }));
  };

  return (
    <div className="chat-page">
      <header className="chat-header">
        <span className="chat-header__brand">AI Lab</span>
        <ModalityTabs activeId={activeModality} />
      </header>

      <div className="chat-body">
        <ConversationSidebar
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={handleSelect}
          onCreate={handleCreate}
        />

        <main className="chat-main">
          <MessageList messages={activeConversation?.messages ?? []} />
          <MessageInput onSend={handleSend} />
        </main>
      </div>
    </div>
  );
}
