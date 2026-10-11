import { mount } from 'svelte';
import App from './App.svelte';
import './design/tokens.css';
import './app.css';
import { registerSW } from 'virtual:pwa-register';

// PWA: the service worker owns the offline cache (app shell plus the last
// snapshot), nothing else. Domain facts still come from the worker and the
// published snapshot, never from the cache.
if ('serviceWorker' in navigator) registerSW({ immediate: true });

// Explicit font load before first paint AND first canvas draw:
// fonts.ready alone resolves while nothing is pending, which still races
// fallback rendering on slow networks.
async function ready() {
  try {
    await Promise.all([
      document.fonts.load('500 16px "IBM Plex Serif"'),
      document.fonts.load('600 16px "IBM Plex Serif"'),
      document.fonts.load('700 16px "IBM Plex Serif"'),
      document.fonts.load('400 16px "IBM Plex Sans"'),
      document.fonts.load('500 16px "IBM Plex Sans"'),
      document.fonts.load('600 16px "IBM Plex Sans"'),
      document.fonts.load('400 16px "JetBrains Mono"'),
      document.fonts.load('500 16px "JetBrains Mono"'),
    ]);
  } catch {
    // fonts API unavailable, render anyway
  }
}

ready().then(() => {
  mount(App, { target: document.getElementById('app')! });
});
