import {
  ChangeDetectorRef,
  Component,
  OnInit,
  inject
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../../core/services/auth.service';

import {
  AssessmentService,
  AssessmentReport,
  CategoryScore
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
  private readonly router = inject(Router);
  public readonly authService = inject(AuthService);
  private readonly cdr = inject(ChangeDetectorRef);

  report: AssessmentReport | null = null;
  loading = true;
  errorMessage = '';
  sessionId = 0;

  ngOnInit(): void {
    this.sessionId = Number(
      this.route.snapshot.paramMap.get('sessionId')
    );

    if (!Number.isInteger(this.sessionId) || this.sessionId <= 0) {
      this.errorMessage = 'Invalid assessment session.';
      this.loading = false;
      this.cdr.detectChanges();
      return;
    }

    this.loadReport();
  }

  loadReport(): void {
    this.loading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    this.api.getReport(this.sessionId).subscribe({
      next: (data: AssessmentReport) => {
        this.report = data;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error: HttpErrorResponse) => {
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

  get categoryScores(): CategoryScore[] {
    return this.report?.report_data?.category_scores ?? [];
  }

  get strengths(): string[] {
    return this.report?.report_data?.strengths ?? [];
  }

  get developmentAreas(): string[] {
    return this.report?.report_data?.development_areas ?? [];
  }

  get recommendations(): string[] {
    return this.report?.report_data?.recommendations ?? [];
  }

  categoryLabel(category: string): string {
    return category
      .replaceAll('_', ' ')
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  printReport(): void {
    window.print();
  }

  goBack(): void {
    if (this.authService.hasRole('admin', 'teacher', 'superadmin')) {
      void this.router.navigate(['/assessment-results']);
    } else {
      void this.router.navigate(['/my-results']);
    }
  }
}
