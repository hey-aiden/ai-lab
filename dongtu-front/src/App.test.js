import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

test('renders chat page with modality tabs', () => {
  render(
    <MemoryRouter initialEntries={['/chat/text']}>
      <App />
    </MemoryRouter>
  );
  expect(screen.getByText(/文本对话/i)).toBeInTheDocument();
  expect(screen.getByText(/文生图/i)).toBeInTheDocument();
  expect(screen.getByText(/语音/i)).toBeInTheDocument();
});
