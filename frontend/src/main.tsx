import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { useSceneStore } from './store/sceneStore';
import './index.css';

// Exposed so the offline recorder (Playwright) can inject a scene to render.
(window as unknown as { __sceneStore: typeof useSceneStore }).__sceneStore = useSceneStore;

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
