
import {
  Component,
  OnInit,
  ChangeDetectorRef,
  inject
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';

import {
  AssessmentService,
  AssessmentReport
} from '../services/assessment';

@Component({
  selector: 'app-assessment-report',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './assessment-report.html',
  styleUrl: './assessment-report.scss'
})
export class AssessmentReportPage implements OnInit {

  private readonly api = inject(AssessmentService);
  private readonly route = inject(ActivatedRoute);
  private readonly cdr = inject(ChangeDetectorRef);

  report: AssessmentReport | null = null;

  loading = true;
  errorMessage = '';

  ngOnInit(): void {

    const sessionId = Number(
      this.route.snapshot.paramMap.get('sessionId')
    );

    if (!Number.isInteger(sessionId) || sessionId <= 0) {

      this.errorMessage = 'Invalid assessment session.';
      this.loading = false;
      this.cdr.detectChanges();
      return;

    }

    this.loading = true;
    this.errorMessage = '';

    this.api.getReport(sessionId).subscribe({

      next: (data) => {

        console.log('Assessment report received:', data);

        this.report = data;
        this.loading = false;

        this.cdr.detectChanges();

      },

      error: (error) => {

        console.error('Assessment report loading failed:', error);

        this.errorMessage =
          error.error?.detail ||
          'Unable to load assessment report. Please try again.';

        this.loading = false;

        this.cdr.detectChanges();

      }

    });

  }

  get categoryEntries(): [string, string][] {

    return Object.entries(
      this.report?.report_data?.category_interpretations ?? {}
    );

  }

  categoryLabel(category: string): string {

    return category
      .replaceAll('_', ' ')
      .replace(/\b\w/g, char => char.toUpperCase());

  }

  printReport(): void {
    window.print();
  }

}
