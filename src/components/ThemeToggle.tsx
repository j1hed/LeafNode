import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

type Theme = 'dark' | 'light';

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.dataset.theme === 'light' ? 'light' : 'dark'
  );

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'light' ? '#f6f5ee' : '#09110f');
    try {
      localStorage.setItem('leafnode-theme', theme);
    } catch {
      // Appearance still works when browser storage is unavailable.
    }
  }, [theme]);

  const nextTheme = theme === 'dark' ? 'light' : 'dark';
  const label = 'Switch to ' + nextTheme + ' mode';

  return (
    <button className="theme-toggle" type="button" onClick={() => setTheme(nextTheme)} aria-label={label} title={label}>
      <span className="theme-toggle-symbol" aria-hidden="true">
        {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
      </span>
      <span className="theme-toggle-label">{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
    </button>
  );
}
