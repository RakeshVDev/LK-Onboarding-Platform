import {
  ChangeDetectorRef,
  Component,
  OnInit,
  inject,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import {
  AssessmentService,
  UserAssessmentResultItem
} from '../services/assessment';

@Component({
  selector: 'app-learner-reports',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './learner-reports.html',
  styleUrl: './learner-reports.scss'
})
export class LearnerReports implements OnInit {
  private readonly api = inject(AssessmentService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly loading = signal(true);
  readonly errorMessage = signal('');
  readonly completedReports = signal<UserAssessmentResultItem[]>([]);

  ngOnInit(): void {
    this.loadReports();
  }

  loadReports(): void {
    this.loading.set(true);
    this.errorMessage.set('');

    this.api.getMyResults().subscribe({
      next: (items) => {
        const completed = (items ?? []).filter(r => r.status === 'completed');
        this.completedReports.set(completed);
        this.loading.set(false);
        this.cdr.detectChanges();
      },
      error: (err: HttpErrorResponse) => {
        this.errorMessage.set(
          err.error?.detail || 'Unable to load diagnostic reports. Please try again.'
        );
        this.loading.set(false);
        this.cdr.detectChanges();
      }
    });
  }

  openReport(sessionId: number): void {
    void this.router.navigate(['/assessments/report', sessionId]);
  }

  goToAssessments(): void {
    void this.router.navigate(['/my-assessments']);
  }

  typeLabel(type: string): string {
    return type
      .replaceAll('_', ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }
}

