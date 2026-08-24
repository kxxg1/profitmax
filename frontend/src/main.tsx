// Global Font Imports
import '@fontsource/roboto/300.css'; // Light (For table body cells)
import '@fontsource/roboto/400.css'; // Regular
import '@fontsource/roboto/500.css'; // Medium (For table headers)

// Material Symbols Icons
import 'material-symbols/outlined.css';

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';

import App from './App';
import './index.css';

// Register AG Grid Community modules once at application root
ModuleRegistry.registerModules([AllCommunityModule]);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);