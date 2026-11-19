import { CommonModule } from '@angular/common';
import { Component, Input, inject, computed } from '@angular/core';
import { ThemeService } from '../../../core/services/theme.service';

@Component({
  selector: 'app-brand-logo',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './brand-logo.html',
  styleUrl: './brand-logo.scss',
})
export class BrandLogo {
  private readonly themeService = inject(ThemeService, { optional: true });

  @Input() variant: 'light' | 'dark' | 'compact' | 'print' = 'light';
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() showSubtitle = false;
  @Input() subtitle = '';
  @Input() badgeText = '';

  readonly isDarkMode = computed(() => {
    return this.variant === 'dark' || this.themeService?.currentTheme() === 'dark';
  });
}

