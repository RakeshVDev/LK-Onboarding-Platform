import { Injectable, signal, PLATFORM_ID, inject, computed } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export type ThemeMode = 'light' | 'dark' | 'system';
export type ActiveTheme = 'light' | 'dark';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private readonly platformId = inject(PLATFORM_ID);
  
  readonly themeMode = signal<ThemeMode>('system');
  readonly currentTheme = signal<ActiveTheme>('light');

  get isDark(): boolean {
    return this.currentTheme() === 'dark';
  }

  private mediaQueryListener?: (e: MediaQueryListEvent) => void;

  constructor() {
    if (isPlatformBrowser(this.platformId)) {
      const savedMode = localStorage.getItem('ase_theme_mode') as ThemeMode | null;
      const legacyTheme = localStorage.getItem('ase_theme') as ActiveTheme | null;
      
      const initialMode: ThemeMode = savedMode || (legacyTheme ? legacyTheme : 'system');
      this.themeMode.set(initialMode);
      this.resolveAndApplyTheme(initialMode);

      if (window.matchMedia) {
        const mql = window.matchMedia('(prefers-color-scheme: dark)');
        this.mediaQueryListener = (e: MediaQueryListEvent) => {
          if (this.themeMode() === 'system') {
            this.applyTheme(e.matches ? 'dark' : 'light');
          }
        };
        mql.addEventListener('change', this.mediaQueryListener);
      }
    }
  }

  toggleTheme(): void {
    const next: ActiveTheme = this.currentTheme() === 'dark' ? 'light' : 'dark';
    this.setTheme(next);
  }

  setTheme(mode: ThemeMode): void {
    this.themeMode.set(mode);
    if (isPlatformBrowser(this.platformId)) {
      try {
        localStorage.setItem('ase_theme_mode', mode);
      } catch (err) {
        console.warn('Could not persist theme mode', err);
      }
      this.resolveAndApplyTheme(mode);
    }
  }

  private resolveAndApplyTheme(mode: ThemeMode): void {
    let resolved: ActiveTheme = 'light';
    if (mode === 'dark') {
      resolved = 'dark';
    } else if (mode === 'light') {
      resolved = 'light';
    } else {
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        resolved = 'dark';
      } else {
        resolved = 'light';
      }
    }
    this.applyTheme(resolved);
  }

  private applyTheme(theme: ActiveTheme): void {
    this.currentTheme.set(theme);
    if (isPlatformBrowser(this.platformId)) {
      try {
        localStorage.setItem('ase_theme', theme);
      } catch (err) {
        console.warn('Could not persist theme', err);
      }
      const root = document.documentElement;
      root.setAttribute('data-theme', theme);
      document.body?.setAttribute('data-theme', theme);
      if (theme === 'dark') {
        root.classList.add('dark');
        document.body?.classList.add('dark', 'dark-theme');
        document.body?.classList.remove('light-theme');
      } else {
        root.classList.remove('dark');
        document.body?.classList.remove('dark', 'dark-theme');
        document.body?.classList.add('light-theme');
      }
    }
  }
}
