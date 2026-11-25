import {
  ChangeDetectorRef,
  Component,
  OnInit,
  computed,
  inject,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import { AuthService } from '../../../core/services/auth.service';
import {
  AssessmentService,
  AssessmentTemplate,
  AdminAssessmentResultItem,
  AdminAssessmentResultsResponse
} from '../services/assessment';

export interface JoineeDirectoryEntry {
  userId: number;
  name: string;
  email: string;
}

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
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly isSuperAdmin = computed(() => this.authService.hasRole('superadmin'));
  readonly isStaffDirectoryView = computed(() =>
    this.authService.hasRole('superadmin', 'admin', 'teacher')
  );
  readonly results = signal<AdminAssessmentResultItem[]>([]);
  readonly selectedJoinee = signal<JoineeDirectoryEntry | null>(null);
  readonly selectedJoineeResults = signal<AdminAssessmentResultItem[]>([]);
  readonly selectedJoineeLoading = signal(false);
  readonly joineeSearch = signal('');

  readonly joineeDirectory = computed<JoineeDirectoryEntry[]>(() => {
    const map = new Map<number, JoineeDirectoryEntry>();
    for (const row of this.results()) {
      if (!row.learner_user_id) continue;
      if (!map.has(row.learner_user_id)) {
        map.set(row.learner_user_id, {
          userId: row.learner_user_id,
          name: (row.learner_name || '').trim() || `Joinee #${row.learner_user_id}`,
          email: (row.learner_email || '').trim(),
        });
      }
    }
    const q = this.joineeSearch().trim().toLowerCase();
    return Array.from(map.values())
      .filter((j) => !q || j.name.toLowerCase().includes(q) || j.email.toLowerCase().includes(q))
      .sort((a, b) => a.name.localeCompare(b.name));
  });

  readonly selectedJoineeStats = computed(() => {
    const rows = this.selectedJoineeResults();
    const completed = rows.filter((r) => r.status === 'completed');
    const graded = completed.filter((r) => r.grading_status !== 'pending_review');
    const avg = graded.length
      ? Math.round((graded.reduce((acc, r) => acc + Number(r.overall_percentage || 0), 0) / graded.length) * 10) / 10
      : 0;
    return {
      total: rows.length,
      completed: completed.length,
      averageScore: avg,
    };
  });

  // Manual Teacher / Staff Grading Modal State (for PDF/ZIP/GitHub submissions)
  readonly gradingModalItem = signal<AdminAssessmentResultItem | null>(null);
  manualScoreInput = 0;
  manualMaxScoreInput = 100;
  manualFeedbackInput = '';
  readonly savingManualGrade = signal(false);
  readonly manualGradeError = signal('');

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

  openJoineeResults(joinee: JoineeDirectoryEntry): void {
    this.selectedJoinee.set(joinee);
    this.selectedJoineeResults.set([]);
    this.selectedJoineeLoading.set(true);
    this.cdr.detectChanges();

    this.api.getAdminResults({ learner_user_id: joinee.userId, include_not_started: true }).subscribe({
      next: (res) => {
        const onlyThisJoinee = (res.results || []).filter(
          (r) => r.learner_user_id === joinee.userId
        );
        this.selectedJoineeResults.set(onlyThisJoinee);
        this.selectedJoineeLoading.set(false);
        this.cdr.detectChanges();
      },
      error: () => {
        this.selectedJoineeLoading.set(false);
        this.cdr.detectChanges();
      },
    });
  }

  backToJoineeList(): void {
    this.selectedJoinee.set(null);
    this.selectedJoineeResults.set([]);
    this.cdr.detectChanges();
  }

  onJoineeSearchChange(value: string): void {
    this.joineeSearch.set(value);
  }

  viewReport(sessionId: number | null): void {
    if (!sessionId) return;
    void this.router.navigate(['/assessments/report', sessionId]);
  }

  viewScores(sessionId: number | null): void {
    if (!sessionId) return;
    void this.router.navigate(['/assessments/results', sessionId]);
  }

  downloadSubmissionZip(item: AdminAssessmentResultItem): void {
    if (!item.session_id) return;
    this.api.downloadSubmissionFile(item.session_id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = item.submission_file_name || `submission_${item.session_id}.zip`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      },
      error: (err) => {
        this.errorMessage.set(err?.error?.detail || 'Unable to download submitted archive.');
        this.cdr.detectChanges();
      }
    });
  }

  openManualGradeModal(item: AdminAssessmentResultItem): void {
    if (!item.session_id) return;
    this.gradingModalItem.set(item);
    this.manualMaxScoreInput = Number(item.max_score) > 0 ? Number(item.max_score) : 100;
    this.manualScoreInput = item.grading_status === 'manually_graded' ? Number(item.total_score || 0) : 0;
    this.manualFeedbackInput = item.trainer_feedback || '';
    this.manualGradeError.set('');
    this.cdr.detectChanges();
  }

  closeManualGradeModal(): void {
    this.gradingModalItem.set(null);
    this.manualGradeError.set('');
    this.cdr.detectChanges();
  }

  submitManualGrade(): void {
    const item = this.gradingModalItem();
    if (!item?.session_id || this.savingManualGrade()) return;
    if (this.manualMaxScoreInput <= 0 || this.manualScoreInput < 0 || this.manualScoreInput > this.manualMaxScoreInput) {
      this.manualGradeError.set(`Enter a valid score between 0 and ${this.manualMaxScoreInput}.`);
      this.cdr.detectChanges();
      return;
    }

    this.savingManualGrade.set(true);
    this.manualGradeError.set('');
    this.api.gradeProjectSubmission(item.session_id, {
      score: Number(this.manualScoreInput),
      max_score: Number(this.manualMaxScoreInput),
      feedback: this.manualFeedbackInput.trim() || undefined,
    }).subscribe({
      next: () => {
        this.savingManualGrade.set(false);
        this.gradingModalItem.set(null);
        this.loadResults();
        const activeJoinee = this.selectedJoinee();
        if (activeJoinee) {
          this.openJoineeResults(activeJoinee);
        }
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.savingManualGrade.set(false);
        this.manualGradeError.set(err?.error?.detail || 'Unable to save manual grade.');
        this.cdr.detectChanges();
      }
    });
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
