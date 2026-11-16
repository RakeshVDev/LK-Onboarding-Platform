import {
  ChangeDetectorRef,
  Component,
  OnInit,
  computed,
  inject,
  signal
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../../core/services/auth.service';
import { AssessmentStatusService } from '../../../core/services/assessment-status.service';

import {
  AssessmentService,
  AssessmentScoresResponse,
  AssessmentReport
} from '../services/assessment';
import {
  AssessmentIntelligenceResponse,
  AssessmentIntelligenceService
} from '../services/assessment-intelligence.service';
import {
  AssessmentRadarChartComponent,
  RadarChartSeries
} from '../components/assessment-radar-chart/assessment-radar-chart';

@Component({
  selector: 'app-assessment-results',
  standalone: true,
  imports: [CommonModule, AssessmentRadarChartComponent],
  templateUrl: './assessment-results.html',
  styleUrl: './assessment-results.scss'
})
export class AssessmentResults implements OnInit {

  private readonly api = inject(AssessmentService);
  private readonly intelligenceService = inject(AssessmentIntelligenceService);
  private readonly assessmentStatusService = inject(AssessmentStatusService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  public readonly authService = inject(AuthService);
  private readonly cdr = inject(ChangeDetectorRef);

  sessionId = 0;
  readonly results = signal<AssessmentScoresResponse | null>(null);
  readonly report = signal<AssessmentReport | null>(null);
  readonly intelligence = signal<AssessmentIntelligenceResponse | null>(null);

  readonly loading = signal(true);
  readonly reportLoading = signal(false);
  readonly errorMessage = signal('');
  readonly allCompleted = signal(false);

  readonly radarAxes = computed<string[]>(() => {
    const intel = this.intelligence();
    if (intel?.radar_profile?.length) {
      return intel.radar_profile.map((p) => p.axis_label);
    }
    return (this.results()?.categories ?? []).map((c) =>
      c.category.replaceAll('_', ' ').replace(/\b\w/g, (ch) => ch.toUpperCase())
    );
  });

  readonly radarSeries = computed<RadarChartSeries[]>(() => {
    const intel = this.intelligence();
    if (intel?.radar_profile?.length) {
      const series: RadarChartSeries[] = [
        {
          id: `session-${this.sessionId}`,
          label: 'Your Score',
          values: intel.radar_profile.map((p) => Number(p.candidate_score ?? 0)),
          borderColor: '#4f46e5',
          backgroundColor: 'rgba(79, 70, 229, 0.18)',
          seriesType: 'candidate',
          overallPercentage: Number(intel.overall_percentage ?? 0),
        },
      ];
      if (intel.radar_profile.some((p) => typeof p.cohort_average === 'number')) {
        series.push({
          id: 'cohort-avg',
          label: 'Cohort Average',
          values: intel.radar_profile.map((p) => Number(p.cohort_average ?? 0)),
          borderColor: '#0284c7',
          backgroundColor: 'rgba(2, 132, 199, 0.10)',
          dashed: true,
          seriesType: 'cohort_average',
        });
      }
      return series;
    }

    const cats = this.results()?.categories ?? [];
    if (cats.length > 0) {
      return [
        {
          id: `session-${this.sessionId}`,
          label: 'Your Score',
          values: cats.map((c) => Number(c.percentage ?? 0)),
          borderColor: '#4f46e5',
          backgroundColor: 'rgba(79, 70, 229, 0.18)',
          seriesType: 'candidate',
        },
      ];
    }
    return [];
  });

  ngOnInit(): void {
    this.sessionId = Number(
      this.route.snapshot.paramMap.get('sessionId')
    );

    if (!Number.isInteger(this.sessionId) || this.sessionId <= 0) {
      this.errorMessage.set('Invalid assessment session.');
      this.loading.set(false);
      this.cdr.detectChanges();
      return;
    }

    if (this.authService.hasRole('learner')) {
      void this.assessmentStatusService.getStatus(true).then(s => {
        this.allCompleted.set(s.status === 'completed' || s.all_completed === true);
        this.cdr.detectChanges();
      }).catch(() => {});
    } else {
      this.allCompleted.set(true);
    }

    this.loadResults();
  }

  loadResults(): void {
    this.loading.set(true);
    this.errorMessage.set('');

    this.api.getResults(this.sessionId).subscribe({
      next: (data: AssessmentScoresResponse) => {
        this.results.set(data);
        this.loading.set(false);
        this.cdr.detectChanges();

        // Retrieve existing report & intelligence radar preview silently if present
        this.intelligenceService.getSessionIntelligence(this.sessionId).subscribe({
          next: (intel) => {
            this.intelligence.set(intel);
            this.cdr.detectChanges();
          },
          error: () => {},
        });
        this.api.getReport(this.sessionId).subscribe({
          next: report => {
            this.report.set(report);
            this.cdr.detectChanges();
          },
          error: (error: HttpErrorResponse) => {
            if (error.status !== 404) {
              console.warn('Existing report lookup failed:', error);
            }
          }
        });
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(
          error.error?.detail || 'Unable to load assessment results.'
        );
        this.loading.set(false);
        this.cdr.detectChanges();
      }
    });
  }

  generateReport(): void {
    if (this.reportLoading() || !this.results()) return;

    this.reportLoading.set(true);
    this.errorMessage.set('');

    this.api.generateReport(this.sessionId).subscribe({
      next: (report: AssessmentReport) => {
        this.report.set(report);
        this.reportLoading.set(false);
        this.cdr.detectChanges();
      },
      error: (error: HttpErrorResponse) => {
        this.reportLoading.set(false);
        this.errorMessage.set(
          error.error?.detail || 'Unable to generate report.'
        );
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
    const res = this.results();
    return res?.total_score ??
      res?.categories.reduce((sum, item) => sum + item.score, 0) ?? 0;
  }

  get maxScore(): number {
    const res = this.results();
    return res?.max_score ??
      res?.categories.reduce((sum, item) => sum + item.max_score, 0) ?? 0;
  }

  get overallPercentage(): number {
    const res = this.results();
    if (res?.overall_percentage !== undefined) {
      return res.overall_percentage;
    }
    return this.maxScore > 0 ? (this.totalScore / this.maxScore) * 100 : 0;
  }

  get correctAnswers(): number {
    return Math.round(this.totalScore);
  }

  get incorrectAnswers(): number {
    const answered = this.results()?.answered_count || 0;
    return Math.max(0, answered - this.correctAnswers);
  }

  get unansweredCount(): number {
    return this.results()?.unanswered_count || 0;
  }

  get accuracyPercentage(): number {
    const answered = this.results()?.answered_count || 0;
    if (answered <= 0) return 0;
    return Math.round((this.correctAnswers / answered) * 100);
  }

  trackCategory(_: number, item: { category: string }): string {
    return item.category;
  }

  goBack(): void {
    if (this.authService.hasRole('admin', 'teacher', 'superadmin')) {
      void this.router.navigate(['/assessment-results']);
    } else if (!this.allCompleted()) {
      void this.router.navigate(['/my-assessments']);
    } else {
      void this.router.navigate(['/my-results']);
    }
  }
}
