// Global Font Imports
import '@fontsource/roboto/300.css'; // Light (For table body cells)
import '@fontsource/roboto/400.css'; // Regular
import '@fontsource/roboto/500.css'; // Medium (For table headers)
// Material Symbols Icons
import 'material-symbols/outlined.css'; // Or 'material-symbols/rounded.css' / 'material-symbols/sharp.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
