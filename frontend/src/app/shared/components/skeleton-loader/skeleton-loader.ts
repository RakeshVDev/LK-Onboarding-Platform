import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-skeleton-loader',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="skeleton-stack" [attr.aria-label]="ariaLabel">
      @for (row of rowsArray; track row) {
        <div
          class="skeleton-bar"
          [style.height.px]="heightPx"
          [style.width.%]="row % 2 === 0 ? 100 : 84">
        </div>
      }
    </div>
  `,
  styles: [
    `
      .skeleton-stack {
        display: flex;
        flex-direction: column;
        gap: 12px;
        width: 100%;
      }
      .skeleton-bar {
        border-radius: 12px;
        background: linear-gradient(
          90deg,
          #e2e8f0 0%,
          #f1f5f9 45%,
          #e2e8f0 100%
        );
        background-size: 220% 100%;
        animation: csm-shimmer 1.4s ease-in-out infinite;
      }
      @keyframes csm-shimmer {
        0% {
          background-position: 200% 0;
        }
        100% {
          background-position: -200% 0;
        }
      }
    `,
  ],
})
export class SkeletonLoader {
  @Input() rows = 3;
  @Input() heightPx = 52;
  @Input() ariaLabel = 'Loading content...';

  get rowsArray(): number[] {
    return Array.from({ length: Math.max(1, this.rows) }, (_, idx) => idx);
  }
}

