import { describe, it, expect } from 'vitest';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { BrandLogo } from './brand-logo';

describe('BrandLogo', () => {
  it('renders official CSM logo image and default subtitle', async () => {
    TestBed.configureTestingModule({
      imports: [BrandLogo],
      providers: [provideZonelessChangeDetection()],
    });

    const fixture = TestBed.createComponent(BrandLogo);
    fixture.detectChanges();
    await fixture.whenStable();

    const root = fixture.nativeElement as HTMLElement;
    const img = root.querySelector('img.csm-logo-img') as HTMLImageElement | null;
    expect(img).toBeTruthy();
    expect(img?.getAttribute('src')).toBe('/assets/images/csm-logo.png');
    expect(img?.getAttribute('alt')).toBe('CSM Logo');
    expect(root.textContent).toContain('ASE Assessment Tool');
  });

  it('supports variant, size, badgeText, and compact subtitle toggle', async () => {
    TestBed.configureTestingModule({
      imports: [BrandLogo],
      providers: [provideZonelessChangeDetection()],
    });

    const fixture = TestBed.createComponent(BrandLogo);
    fixture.componentInstance.variant = 'dark';
    fixture.componentInstance.size = 'lg';
    fixture.componentInstance.badgeText = 'ENTERPRISE';
    fixture.componentInstance.subtitle = 'Official Report';
    fixture.detectChanges();
    await fixture.whenStable();

    const wrapper = fixture.nativeElement.querySelector('.csm-brand') as HTMLElement;
    expect(wrapper.getAttribute('data-variant')).toBe('dark');
    expect(wrapper.getAttribute('data-size')).toBe('lg');
    expect(fixture.nativeElement.textContent).toContain('ENTERPRISE');
    expect(fixture.nativeElement.textContent).toContain('Official Report');
  });
});

