import {
  ChangeDetectorRef,
  Component,
  OnInit,
  inject,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import {
  AssessmentService,
  AssessmentTemplate,
  AdminAssessmentResultItem,
  AdminAssessmentResultsResponse
} from '../services/assessment';

@Component({
  selector: 'app-admin-results',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule
  ],
  templateUrl: './admin-results.html',
  styleUrl: './admin-results.scss'
})
export class AdminResults implements OnInit {
  private readonly api = inject(AssessmentService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly results = signal<AdminAssessmentResultItem[]>([]);
  templates: AssessmentTemplate[] = [];

  readonly loading = signal(true);
  readonly errorMessage = signal('');

  // Filter state
  searchQuery = '';
  selectedTemplateId: number | null = null;
  selectedStatus = 'all';
  includeNotStarted = true;

  // Summary stats
  totalAssessments = 0;
  attendedCount = 0;
  completedCount = 0;
  inProgressCount = 0;
  expiredCount = 0;
  notStartedCount = 0;
  averageScore = 0;
  uniqueLearners = 0;

  ngOnInit(): void {
    this.loadTemplates();
    this.loadResults();
  }

  loadTemplates(): void {
    this.api.getTemplates().subscribe({
      next: (data) => {
        this.templates = Array.isArray(data) ? data : [];
        this.cdr.detectChanges();
      },
      error: (err) => console.warn('Could not load templates for filter:', err)
    });
  }

  loadResults(): void {
    this.loading.set(true);
    this.errorMessage.set('');

    const params: {
      template_id?: number;
      status?: string;
      search?: string;
      include_not_started?: boolean;
    } = {
      include_not_started: this.includeNotStarted || this.selectedStatus === 'not_started'
    };

    if (this.selectedTemplateId) {
      params.template_id = this.selectedTemplateId;
    }
    if (this.selectedStatus && this.selectedStatus !== 'all') {
      params.status = this.selectedStatus;
    }
    if (this.searchQuery.trim()) {
      params.search = this.searchQuery.trim();
    }

    this.api.getAdminResults(params).subscribe({
      next: (data: AdminAssessmentResultsResponse) => {
        this.results.set(data.results || []);
        this.totalAssessments = data.total_assessments;
        this.completedCount = data.completed_count;
        this.inProgressCount = data.in_progress_count ?? 0;
        this.expiredCount = data.expired_count ?? 0;
        this.notStartedCount = data.not_started_count ?? 0;
        this.attendedCount = data.attended_count ?? (this.completedCount + this.inProgressCount + this.expiredCount);
        this.averageScore = data.average_score;
        this.uniqueLearners = data.unique_learners;
        this.loading.set(false);
        this.cdr.detectChanges();
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(
          error.error?.detail || 'Unable to load learner assessment results.'
        );
        this.loading.set(false);
        this.cdr.detectChanges();
      }
    });
  }

  onFilterChange(): void {
    if (this.selectedStatus === 'not_started') {
      this.includeNotStarted = true;
    }
    this.loadResults();
  }

  clearFilters(): void {
    this.searchQuery = '';
    this.selectedTemplateId = null;
    this.selectedStatus = 'all';
    this.includeNotStarted = true;
    this.loadResults();
  }

  readonly historyLearner = signal<{ userId: number; name: string; email?: string | null } | null>(null);
  readonly historyResults = signal<AdminAssessmentResultItem[]>([]);
  readonly historyLoading = signal<boolean>(false);

  openLearnerHistory(learnerUserId: number, name?: string | null, email?: string | null): void {
    this.historyLearner.set({
      userId: learnerUserId,
      name: name || `Learner #${learnerUserId}`,
      email
    });
    this.historyResults.set([]);
    this.historyLoading.set(true);
    this.api.getAdminResults({ learner_user_id: learnerUserId, include_not_started: false }).subscribe({
      next: res => {
        this.historyResults.set(res.results || []);
        this.historyLoading.set(false);
        this.cdr.detectChanges();
      },
      error: () => {
        this.historyLoading.set(false);
        this.cdr.detectChanges();
      }
    });
  }

  closeLearnerHistory(): void {
    this.historyLearner.set(null);
    this.historyResults.set([]);
  }

  viewReport(sessionId: number | null): void {
    if (!sessionId) return;
    void this.router.navigate(['/assessments/report', sessionId]);
  }

  viewScores(sessionId: number | null): void {
    if (!sessionId) return;
    void this.router.navigate(['/assessments/results', sessionId]);
  }

  statusLabel(status: string): string {
    switch (status) {
      case 'completed': return 'Completed';
      case 'in_progress': return 'In Progress';
      case 'expired': return 'Expired';
      case 'not_started': return 'Not Attended';
      default: return status;
    }
  }

  typeLabel(type: string): string {
    switch (type) {
      case 'psychometric': return 'Psychometric';
      case 'technical': return 'Technical';
      case 'english_grammar': return 'English Grammar';
      default: return type.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
    }
  }

  getUserInitials(name?: string): string {
    if (!name) return 'U';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return parts[0].substring(0, 2).toUpperCase();
  }

  getGrade(percentage: number): { label: string; class: string } {
    if (percentage >= 85) return { label: 'Exceptional', class: 'grade-exceptional' };
    if (percentage >= 70) return { label: 'Proficient', class: 'grade-proficient' };
    if (percentage >= 50) return { label: 'Developing', class: 'grade-developing' };
    return { label: 'Needs Focus', class: 'grade-focus' };
  }
}
