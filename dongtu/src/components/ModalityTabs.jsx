import { Link } from 'react-router-dom';
import { MODALITIES } from '../data/modalities';

// 顶部模态 tab。点击切换到对应模态,底下的会话列表与消息历史随之切换。
export default function ModalityTabs({ activeId }) {
  return (
    <nav className="modality-tabs" role="tablist" aria-label="模态切换">
      {MODALITIES.map((m) => (
        <Link
          key={m.id}
          to={`/chat/${m.id}`}
          role="tab"
          aria-selected={m.id === activeId}
          className={`modality-tab${m.id === activeId ? ' is-active' : ''}`}
        >
          <span className="modality-tab__icon" aria-hidden="true">
            {m.icon}
          </span>
          <span className="modality-tab__label">{m.label}</span>
        </Link>
      ))}
    </nav>
  );
}
