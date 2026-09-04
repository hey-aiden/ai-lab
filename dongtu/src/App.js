import { Routes, Route, Navigate } from 'react-router-dom';
import ChatPage from './pages/ChatPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/chat/text" replace />} />
      <Route path="/chat" element={<Navigate to="/chat/text" replace />} />
      <Route path="/chat/:modalityId" element={<ChatPage />} />
      <Route path="*" element={<Navigate to="/chat/text" replace />} />
    </Routes>
  );
}

export default App;
