import { useState } from 'react';

// 底部输入框。回车或点击按钮发送;空内容不发送。
export default function MessageInput({ onSend, disabled }) {
  const [value, setValue] = useState('');

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="message-input">
      <textarea
        className="message-input__field"
        value={value}
        placeholder="输入消息,Enter 发送,Shift+Enter 换行"
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        rows={1}
      />
      <button
        className="message-input__send"
        onClick={submit}
        disabled={disabled || !value.trim()}
      >
        发送
      </button>
    </div>
  );
}
