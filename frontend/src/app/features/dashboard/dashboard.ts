import {
  Component,
  OnInit,
  DestroyRef,
  ChangeDetectorRef,
  signal,
  computed,
  effect,
  inject
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { firstValueFrom, interval } from 'rxjs';

import { AuthService, CurrentUser, UserRole } from '../../core/services/auth.service';
import {
  AssessmentService,
  AssessmentTemplate,
  AssessmentAssignmentStatus,
  StudentAssignedAssessmentItem,
  StudentAssignedStats
} from '../assessments/services/assessment';
import { UserManagementService, ManagedUser } from '../../core/services/user-management.service';
import { LearningService } from '../../core/services/learning.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class Dashboard implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly assessmentService = inject(AssessmentService);
  private readonly userService = inject(UserManagementService);
  private readonly learningService = inject(LearningService);
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly user = signal<CurrentUser | null>(null);
  readonly loading = signal(true);
  readonly syncingAssessments = signal(false);
  readonly errorMessage = signal('');

  // Dynamic learner assigned assessments, notifications, stats & cohorts
  readonly assignedAssessments = signal<StudentAssignedAssessmentItem[]>([]);
  readonly notifications = signal<StudentAssignedAssessmentItem[]>([]);
  readonly assignedStats = signal<StudentAssignedStats>({
    total_assigned: 0,
    not_started_count: 0,
    in_progress_count: 0,
    completed_count: 0,
    expired_count: 0,
    average_score: 0
  });
  readonly assignedCohortNames = signal<string[]>([]);
  readonly lastSyncedAt = signal<string | null>(null);
  readonly nowTickMs = signal<number>(Date.now());
  private lastSyncLocalMs = Date.now();
  private lastTimeoutRefreshMs = 0;
  private initializedLearnerSync = false;

  readonly templates = signal<AssessmentTemplate[]>([]);

  readonly completedAssignedCount = computed(() =>
    this.assignedAssessments().filter(item => item.status === 'COMPLETED').length
  );

  readonly totalAssignedCount = computed(() =>
    this.assignedAssessments().length
  );

  readonly hasInProgressAssessment = computed(() =>
    this.assignedAssessments().some(item => item.status === 'IN_PROGRESS')
  );

  readonly learnerAverageScore = computed(() => {
    const completed = this.assignedAssessments().filter(
      item => item.status === 'COMPLETED' && item.overall_percentage !== null && item.overall_percentage !== undefined
    );
    if (completed.length === 0) return 0;
    const sum = completed.reduce((acc, curr) => acc + (curr.overall_percentage || 0), 0);
    return Math.round(sum / completed.length);
  });

  readonly assignedCohortLabel = computed(() => {
    const names = this.assignedCohortNames();
    if (names.length > 0) {
      return names.join(', ');
    }
    return 'All Assigned Batches';
  });

  // Admin & Teacher telemetry data
  readonly adminResultsStats = signal<{
    totalAssessments: number;
    completedCount: number;
    averageScore: number;
    uniqueLearners: number;
  }>({
    totalAssessments: 0,
    completedCount: 0,
    averageScore: 0,
    uniqueLearners: 0
  });

  // Admin user metrics
  readonly userStats = signal<{
    total: number;
    learners: number;
    teachers: number;
    admins: number;
  }>({
    total: 0,
    learners: 0,
    teachers: 0,
    admins: 0
  });

  // Dynamic learning entities counts from backend
  readonly coursesCount = signal<number>(0);
  readonly cohortsCount = signal<number>(0);
  readonly departmentsCount = signal<number>(0);

  // Time-based greeting
  readonly greeting = computed(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  });

  readonly todayFormatted = computed(() => {
    return new Date().toLocaleDateString('en-US', {
      weekday: 'long',
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  });

  // Dynamic onboarding progress calculation based on all assigned assessments
  readonly onboardingProgress = computed(() => {
    let score = 25; // 25% for verified account creation
    const total = this.totalAssignedCount();
    const completed = this.completedAssignedCount();
    if (total > 0) {
      score += Math.min(50, Math.round((completed / total) * 50));
    } else {
      score += 50;
    }
    if (this.coursesCount() > 0) {
      score += 25;
    }
    return Math.min(100, score);
  });

  private readonly syncReaction = effect(() => {
    const version = this.assessmentService.syncVersion();
    if (version > 0 && this.initializedLearnerSync && this.user()?.role === 'learner') {
      void this.loadAssignedAssessments(true);
    }
  });

  async ngOnInit(): Promise<void> {
    try {
      const currentUser = await this.authService.getCurrentUser();

      if (!currentUser.is_active) {
        this.authService.logout();
        await this.router.navigateByUrl('/login');
        return;
      }

      this.user.set(currentUser);
      await this.loadRoleSpecificData(currentUser.role);

      if (currentUser.role === 'learner') {
        this.initializedLearnerSync = true;
        this.setupLearnerLiveSync();
      }
    } catch (err) {
      console.error('Dashboard load error:', err);
      this.errorMessage.set('Unable to load your dashboard. Please sign in again.');
      this.authService.logout();
      await this.router.navigateByUrl('/login');
    } finally {
      this.loading.set(false);
      this.cdr.detectChanges();
    }
  }

  private setupLearnerLiveSync(): void {
    // Lightweight 30-second background polling while tab is visible
    interval(30000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (!document.hidden && this.user()?.role === 'learner') {
          void this.loadAssignedAssessments(true);
        }
      });

    // Live 1-second timer tick only when at least one session is IN_PROGRESS
    interval(1000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (!this.hasInProgressAssessment()) {
          return;
        }
        const now = Date.now();
        this.nowTickMs.set(now);

        // If any active countdown hit 0, ask backend to refresh lifecycle status (debounced 10s)
        const justTimedOut = this.assignedAssessments().some(
          item => item.status === 'IN_PROGRESS' && this.getLiveRemainingSeconds(item) === 0
        );
        if (justTimedOut && now - this.lastTimeoutRefreshMs > 10000) {
          this.lastTimeoutRefreshMs = now;
          void this.loadAssignedAssessments(true);
        }
        this.cdr.detectChanges();
      });

    // Instant refresh when user returns to browser tab or window focus
    const onVisibilityOrFocus = (): void => {
      if (!document.hidden && this.user()?.role === 'learner') {
        void this.loadAssignedAssessments(true);
      }
    };
    document.addEventListener('visibilitychange', onVisibilityOrFocus);
    window.addEventListener('focus', onVisibilityOrFocus);

    this.destroyRef.onDestroy(() => {
      document.removeEventListener('visibilitychange', onVisibilityOrFocus);
      window.removeEventListener('focus', onVisibilityOrFocus);
    });
  }

  private async loadRoleSpecificData(role: UserRole): Promise<void> {
    const tasks: Promise<any>[] = [this.loadLearningCounts()];

    if (role === 'learner') {
      tasks.push(this.loadAssignedAssessments(false));
    } else if (role === 'teacher') {
      tasks.push(this.loadTemplates(), this.loadAdminResults());
    } else if (role === 'admin' || role === 'superadmin') {
      tasks.push(this.loadTemplates(), this.loadAdminResults(), this.loadUserStats());
    }

    await Promise.allSettled(tasks);
  }

  async refreshLearnerAssessments(): Promise<void> {
    if (this.user()?.role !== 'learner') return;
    await this.loadAssignedAssessments(true);
  }

  private async loadAssignedAssessments(silent: boolean): Promise<void> {
    if (!silent) {
      this.syncingAssessments.set(true);
    }
    try {
      const data = await firstValueFrom(this.assessmentService.getMyAssignedAssessments());
      const uniqueAssessments = this.deduplicateByTemplateId(data.assessments || []);
      const uniqueNotifications = this.deduplicateByTemplateId(data.notifications || []);

      this.assignedAssessments.set(uniqueAssessments);
      this.notifications.set(uniqueNotifications);
      this.assignedStats.set(data.stats || {
        total_assigned: uniqueAssessments.length,
        not_started_count: uniqueAssessments.filter(a => a.status === 'NOT_STARTED').length,
        in_progress_count: uniqueAssessments.filter(a => a.status === 'IN_PROGRESS').length,
        completed_count: uniqueAssessments.filter(a => a.status === 'COMPLETED').length,
        expired_count: uniqueAssessments.filter(a => a.status === 'EXPIRED').length,
        average_score: 0
      });
      this.assignedCohortNames.set(Array.isArray(data.cohort_names) ? data.cohort_names : []);
      this.lastSyncedAt.set(data.synced_at || new Date().toISOString());
      this.lastSyncLocalMs = Date.now();
      this.nowTickMs.set(this.lastSyncLocalMs);
    } catch (err) {
      console.warn('Could not load assigned learner assessments:', err);
    } finally {
      this.syncingAssessments.set(false);
      this.cdr.detectChanges();
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

  private async loadLearningCounts(): Promise<void> {
    try {
      const [coursesRes, cohortsRes, deptsRes] = await Promise.allSettled([
        this.learningService.getCourses(),
        this.learningService.getCohorts(),
        this.learningService.getDepartments()
      ]);

      if (coursesRes.status === 'fulfilled' && Array.isArray(coursesRes.value)) {
        this.coursesCount.set(coursesRes.value.length);
      }
      if (cohortsRes.status === 'fulfilled' && Array.isArray(cohortsRes.value)) {
        this.cohortsCount.set(cohortsRes.value.length);
      }
      if (deptsRes.status === 'fulfilled' && Array.isArray(deptsRes.value)) {
        this.departmentsCount.set(deptsRes.value.length);
      }
    } catch (err) {
      console.warn('Could not load learning counts:', err);
    }
  }

  private async loadTemplates(): Promise<void> {
    try {
      const templates = await firstValueFrom(this.assessmentService.getTemplates());
      this.templates.set(templates || []);
    } catch (err) {
      console.warn('Could not load templates on dashboard:', err);
    }
  }

  private async loadAdminResults(): Promise<void> {
    try {
      const data = await firstValueFrom(this.assessmentService.getAdminResults());
      if (data) {
        this.adminResultsStats.set({
          totalAssessments: data.total_assessments || 0,
          completedCount: data.completed_count || 0,
          averageScore: Math.round(data.average_score || 0),
          uniqueLearners: data.unique_learners || 0
        });
      }
    } catch (err) {
      console.warn('Could not load admin assessment results on dashboard:', err);
    }
  }

  private async loadUserStats(): Promise<void> {
    try {
      const users: ManagedUser[] = await this.userService.listUsers();
      if (Array.isArray(users)) {
        const learners = users.filter(u => u.role === 'learner').length;
        const teachers = users.filter(u => u.role === 'teacher').length;
        const admins = users.filter(u => u.role === 'admin' || u.role === 'superadmin').length;
        this.userStats.set({
          total: users.length,
          learners,
          teachers,
          admins
        });
      }
    } catch (err) {
      console.warn('Could not load user stats on dashboard:', err);
    }
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

  getAssessmentIcon(type?: string): string {
    switch (type) {
      case 'logical_reasoning': return '⚡';
      case 'technical': return '💻';
      case 'english_grammar': return '✍';
      case 'programming': return '⌘';
      case 'psychometric': return '✦';
      default: return '▤';
    }
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

  getRoleLabel(role?: string): string {
    switch (role) {
      case 'superadmin': return 'Super Administrator';
      case 'admin': return 'Administrator';
      case 'teacher': return 'Instructor / Faculty';
      case 'learner': return 'New Joinee / Learner';
      default: return 'User';
    }
  }

  get userInitial(): string {
    return this.user()?.full_name?.charAt(0)?.toUpperCase() || 'U';
  }
}
