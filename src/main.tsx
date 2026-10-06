import React from 'react';
import ReactDOM from 'react-dom/client';
import '@fontsource-variable/inter';
import Root from './app/Root';
import './styles/globals.css';
import './styles/themes.css';
import './styles/landing.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
