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
  AssessmentScoresResponse,
  AssessmentReport
} from '../services/assessment';

@Component({
  selector: 'app-assessment-results',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './assessment-results.html',
  styleUrl: './assessment-results.scss'
})
export class AssessmentResults implements OnInit {

  private readonly api = inject(AssessmentService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  public readonly authService = inject(AuthService);
  private readonly cdr = inject(ChangeDetectorRef);

  sessionId = 0;
  results: AssessmentScoresResponse | null = null;
  report: AssessmentReport | null = null;

  loading = true;
  reportLoading = false;
  errorMessage = '';

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

    this.loadResults();
  }

  loadResults(): void {
    this.loading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    this.api.getResults(this.sessionId).subscribe({
      next: (data: AssessmentScoresResponse) => {
        this.results = data;
        this.loading = false;
        this.cdr.detectChanges();

        // If report already exists, retrieve it without forcing regeneration.
        this.api.getReport(this.sessionId).subscribe({
          next: report => {
            this.report = report;
            this.cdr.detectChanges();
          },
          error: (error: HttpErrorResponse) => {
            // A 404 simply means the learner has not generated the report yet.
            if (error.status !== 404) {
              console.warn('Existing report lookup failed:', error);
            }
          }
        });
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage =
          error.error?.detail || 'Unable to load assessment results.';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  generateReport(): void {
    if (this.reportLoading || !this.results) return;

    this.reportLoading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    this.api.generateReport(this.sessionId).subscribe({
      next: (report: AssessmentReport) => {
        this.report = report;
        this.reportLoading = false;
        this.cdr.detectChanges();
      },
      error: (error: HttpErrorResponse) => {
        this.reportLoading = false;
        this.errorMessage =
          error.error?.detail || 'Unable to generate report.';
        this.cdr.detectChanges();
      }
    });
  }

  viewReport(): void {
    void this.router.navigate([
      '/assessments/report',
      this.sessionId
    ]);
  }

  categoryLabel(category: string): string {
    return category
      .replaceAll('_', ' ')
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  get totalScore(): number {
    return this.results?.total_score ??
      this.results?.categories.reduce((sum, item) => sum + item.score, 0) ?? 0;
  }

  get maxScore(): number {
    return this.results?.max_score ??
      this.results?.categories.reduce((sum, item) => sum + item.max_score, 0) ?? 0;
  }

  get overallPercentage(): number {
    if (this.results?.overall_percentage !== undefined) {
      return this.results.overall_percentage;
    }
    return this.maxScore > 0 ? (this.totalScore / this.maxScore) * 100 : 0;
  }

  get correctAnswers(): number {
    return Math.round(this.totalScore);
  }

  get incorrectAnswers(): number {
    const answered = this.results?.answered_count || 0;
    return Math.max(0, answered - this.correctAnswers);
  }

  get unansweredCount(): number {
    return this.results?.unanswered_count || 0;
  }

  get accuracyPercentage(): number {
    const answered = this.results?.answered_count || 0;
    if (answered <= 0) return 0;
    return Math.round((this.correctAnswers / answered) * 100);
  }

  trackCategory(_: number, item: { category: string }): string {
    return item.category;
  }

  goBack(): void {
    if (this.authService.hasRole('admin', 'teacher', 'superadmin')) {
      void this.router.navigate(['/assessment-results']);
    } else {
      void this.router.navigate(['/my-results']);
    }
  }
}
