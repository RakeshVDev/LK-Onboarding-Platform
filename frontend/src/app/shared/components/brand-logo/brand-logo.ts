import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-brand-logo',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './brand-logo.html',
  styleUrl: './brand-logo.scss',
})
export class BrandLogo {
  @Input() variant: 'light' | 'dark' | 'compact' | 'print' = 'light';
  @Input() size: 'sm' | 'md' | 'lg' = 'md';
  @Input() showSubtitle = false;
  @Input() subtitle = '';
  @Input() badgeText = '';
}

