import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/globals.css'
import App from './App.tsx'

console.log('main.tsx: Starting application...');
const rootElement = document.getElementById('root');
console.log('main.tsx: Root element:', rootElement);

if (rootElement) {
  console.log('main.tsx: Creating React root...');
  const root = createRoot(rootElement);
  console.log('main.tsx: Rendering App...');
  root.render(
    <StrictMode>
      <App />
    </StrictMode>
  );
  console.log('main.tsx: Render call completed');
} else {
  console.error('main.tsx: Root element not found!');
}
