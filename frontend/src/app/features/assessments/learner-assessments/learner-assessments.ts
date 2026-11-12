import {
  Component,
  OnInit,
  DestroyRef,
  ChangeDetectorRef,
  inject,
  signal,
  computed,
  effect
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { interval } from 'rxjs';

import {
  AssessmentService,
  AssessmentAssignmentStatus,
  StudentAssignedAssessmentItem
} from '../services/assessment';

@Component({
  selector: 'app-learner-assessments',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './learner-assessments.html',
  styleUrl: './learner-assessments.scss'
})
export class LearnerAssessments implements OnInit {

  private readonly api = inject(AssessmentService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly assessments = signal<StudentAssignedAssessmentItem[]>([]);
  readonly cohortNames = signal<string[]>([]);
  readonly lastSyncedAt = signal<string | null>(null);
  readonly loading = signal(true);
  readonly syncing = signal(false);
  readonly errorMessage = signal('');
  readonly nowTickMs = signal(Date.now());

  readonly hasInProgressAssessment = computed(() =>
    this.assessments().some(item => item.status === 'IN_PROGRESS')
  );

  startingId: number | null = null;
  selectedInstructionItem: StudentAssignedAssessmentItem | null = null;
  showConfirmStartDialog = false;

  private lastSyncLocalMs = Date.now();
  private lastTimeoutRefreshMs = 0;
  private queryAutoOpenHandled = false;
  private initializedSync = false;

  private readonly syncReaction = effect(() => {
    const version = this.api.syncVersion();
    if (version > 0 && this.initializedSync) {
      this.loadAssessments(true);
    }
  });

  ngOnInit(): void {
    this.loadAssessments(false);
    this.initializedSync = true;
    this.setupLiveSync();
  }

  private setupLiveSync(): void {
    // 30-second lightweight background polling while visible
    interval(30000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (!document.hidden) {
          this.loadAssessments(true);
        }
      });

    // 1-second local countdown tick for IN_PROGRESS attempts
    interval(1000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (!this.hasInProgressAssessment()) {
          return;
        }
        const now = Date.now();
        this.nowTickMs.set(now);

        const justTimedOut = this.assessments().some(
          item => item.status === 'IN_PROGRESS' && this.getLiveRemainingSeconds(item) === 0
        );
        if (justTimedOut && now - this.lastTimeoutRefreshMs > 10000) {
          this.lastTimeoutRefreshMs = now;
          this.loadAssessments(true);
        }
        this.cdr.detectChanges();
      });

    const onVisibilityOrFocus = (): void => {
      if (!document.hidden) {
        this.loadAssessments(true);
      }
    };
    document.addEventListener('visibilitychange', onVisibilityOrFocus);
    window.addEventListener('focus', onVisibilityOrFocus);

    this.destroyRef.onDestroy(() => {
      document.removeEventListener('visibilitychange', onVisibilityOrFocus);
      window.removeEventListener('focus', onVisibilityOrFocus);
    });
  }

  loadAssessments(silent: boolean = false): void {
    if (silent) {
      this.syncing.set(true);
    } else {
      this.loading.set(true);
      this.errorMessage.set('');
    }

    this.api.getMyAssignedAssessments().subscribe({
      next: (data) => {
        const items = this.deduplicateByTemplateId(data?.assessments || []);
        this.assessments.set(items);
        this.cohortNames.set(Array.isArray(data?.cohort_names) ? data.cohort_names : []);
        this.lastSyncedAt.set(data?.synced_at || new Date().toISOString());
        this.lastSyncLocalMs = Date.now();
        this.nowTickMs.set(this.lastSyncLocalMs);

        if (!this.queryAutoOpenHandled) {
          this.queryAutoOpenHandled = true;
          this.handleInitialQueryParams(items);
        }

        this.loading.set(false);
        this.syncing.set(false);
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Assessment loading error:', error);
        if (!silent) {
          this.errorMessage.set(
            error.error?.detail ||
            'Unable to load assigned assessments. Please try again.'
          );
        }
        this.loading.set(false);
        this.syncing.set(false);
        this.cdr.detectChanges();
      }
    });
  }

  private handleInitialQueryParams(items: StudentAssignedAssessmentItem[]): void {
    const startTemplateIdParam = this.route.snapshot.queryParamMap.get('startTemplateId');
    if (startTemplateIdParam) {
      const targetId = Number(startTemplateIdParam);
      const matchedById = items.find(item => item.template_id === targetId);
      if (matchedById && matchedById.status === 'NOT_STARTED' && matchedById.can_start) {
        this.openInstructions(matchedById);
      } else if (matchedById && matchedById.status === 'IN_PROGRESS' && matchedById.session_id) {
        void this.router.navigate(['/assessments/take', matchedById.session_id]);
      }
      return;
    }

    const startType =
      this.route.snapshot.queryParamMap.get('start') ||
      this.route.snapshot.queryParamMap.get('type');
    if (startType) {
      const matched = items.find(
        item =>
          (item.assessment_type === startType ||
            item.name.toLowerCase().includes(startType.toLowerCase())) &&
          item.status === 'NOT_STARTED' &&
          item.can_start
      );
      if (matched) {
        this.openInstructions(matched);
      }
    }
  }

  private deduplicateByTemplateId(items: StudentAssignedAssessmentItem[]): StudentAssignedAssessmentItem[] {
    const seen = new Set<number>();
    const result: StudentAssignedAssessmentItem[] = [];
    for (const item of items) {
      if (!seen.has(item.template_id)) {
        seen.add(item.template_id);
        result.push(item);
      }
    }
    return result;
  }

  openInstructions(item: StudentAssignedAssessmentItem): void {
    if (item.status !== 'NOT_STARTED' || !item.can_start) {
      return;
    }
    this.selectedInstructionItem = item;
    this.showConfirmStartDialog = false;
    this.cdr.detectChanges();
  }

  closeInstructions(): void {
    this.selectedInstructionItem = null;
    this.showConfirmStartDialog = false;
    this.cdr.detectChanges();
  }

  requestStart(): void {
    this.showConfirmStartDialog = true;
    this.cdr.detectChanges();
  }

  cancelStart(): void {
    this.showConfirmStartDialog = false;
    this.cdr.detectChanges();
  }

  confirmAndStart(): void {
    if (!this.selectedInstructionItem) return;
    const item = this.selectedInstructionItem;
    this.showConfirmStartDialog = false;
    this.startAssessment(item);
  }

  getDurationMinutes(item: StudentAssignedAssessmentItem): number {
    if (item.duration_minutes && item.duration_minutes > 0) {
      return item.duration_minutes;
    }
    return (item.assessment_type === 'logical_reasoning' || item.assessment_type === 'programming') ? 30 : 15;
  }

  getLiveRemainingSeconds(item: StudentAssignedAssessmentItem): number {
    if (item.remaining_seconds === null || item.remaining_seconds === undefined) {
      return 0;
    }
    const elapsedSec = Math.max(0, Math.floor((this.nowTickMs() - this.lastSyncLocalMs) / 1000));
    return Math.max(0, item.remaining_seconds - elapsedSec);
  }

  formatRemainingTime(totalSeconds: number): string {
    const safe = Math.max(0, Math.floor(totalSeconds));
    const hrs = Math.floor(safe / 3600);
    const mins = Math.floor((safe % 3600) / 60);
    const secs = safe % 60;
    if (hrs > 0) {
      return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }

  getStatusBadgeLabel(status: AssessmentAssignmentStatus | string): string {
    switch (status) {
      case 'NOT_STARTED': return 'Pending';
      case 'IN_PROGRESS': return 'In Progress';
      case 'COMPLETED': return 'Completed';
      case 'EXPIRED': return 'Expired';
      default: return status;
    }
  }

  startAssessment(item: StudentAssignedAssessmentItem): void {
    if (item.status === 'COMPLETED') {
      this.errorMessage.set(`You have already completed the ${item.name}. Only one attempt is permitted.`);
      this.cdr.detectChanges();
      return;
    }

    if (item.status === 'EXPIRED') {
      this.errorMessage.set(`The submission deadline for ${item.name} has expired.`);
      this.cdr.detectChanges();
      return;
    }

    if (item.status === 'IN_PROGRESS' && item.session_id) {
      void this.router.navigate(['/assessments/take', item.session_id]);
      return;
    }

    this.startingId = item.template_id;
    this.errorMessage.set('');

    this.api.startAssessment(item.template_id, false).subscribe({
      next: (session) => {
        this.startingId = null;
        this.selectedInstructionItem = null;
        this.showConfirmStartDialog = false;
        this.cdr.detectChanges();

        void this.router.navigate(
          ['/assessments/take', session.session_id],
          {
            state: {
              sessionId: session.session_id,
              questions: session.questions,
              startedAt: session.started_at,
              expiresAt: session.expires_at,
              durationMinutes: session.duration_minutes || this.getDurationMinutes(item),
              remainingSeconds: session.remaining_seconds,
              templateName: session.template_name || item.name,
              assessmentType: session.assessment_type || item.assessment_type,
            }
          }
        );
      },
      error: (error) => {
        console.error('Assessment start error:', error);
        this.startingId = null;
        this.selectedInstructionItem = null;
        this.showConfirmStartDialog = false;

        const detail = error.error?.detail || '';
        this.errorMessage.set(detail || 'Unable to start assessment. Please try again.');
        this.loadAssessments(true);
        this.cdr.detectChanges();
      }
    });
  }
}
