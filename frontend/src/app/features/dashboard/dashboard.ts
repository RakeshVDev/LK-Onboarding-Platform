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
import { FormsModule } from '@angular/forms';
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
import { LearningService, Department, StudentDepartmentRequest } from '../../core/services/learning.service';
import { LiveClassesService, LiveClassSession } from '../../core/services/live-classes.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class Dashboard implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly assessmentService = inject(AssessmentService);
  private readonly userService = inject(UserManagementService);
  private readonly learningService = inject(LearningService);
  private readonly liveClassesService = inject(LiveClassesService);
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

  readonly pendingAssignedCount = computed(() =>
    Math.max(0, this.totalAssignedCount() - this.completedAssignedCount())
  );

  readonly trainingProgressPercent = computed(() =>
    this.totalAssignedCount() > 0
      ? Math.round((this.completedAssignedCount() / this.totalAssignedCount()) * 100)
      : 0
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

  readonly activeTab = signal<'overview' | 'courses' | 'assessments' | 'analytics'>('overview');
  readonly tableSearch = signal<string>('');
  readonly courseSearch = signal<string>('');
  readonly assessmentSearch = signal<string>('');
  selectedFilterDepartment = 'all';
  selectedFilterPeriod = 'q2_2026';

  setActiveTab(tab: 'overview' | 'courses' | 'assessments' | 'analytics'): void {
    this.activeTab.set(tab);
  }

  readonly filteredCourses = computed(() => {
    const list = this.coursesList();
    const q = this.courseSearch().trim().toLowerCase();
    if (!q) return list;
    return list.filter(c =>
      (c.title || '').toLowerCase().includes(q) ||
      (c.description || '').toLowerCase().includes(q) ||
      (c.department_name || '').toLowerCase().includes(q)
    );
  });

  readonly filteredAssignedAssessments = computed(() => {
    const list = this.assignedAssessments();
    const q = (this.assessmentSearch() || this.tableSearch()).trim().toLowerCase();

    return list.filter(item => {
      const matchSearch = !q || (item.name || '').toLowerCase().includes(q) || (item.category_label || '').toLowerCase().includes(q);
      return matchSearch;
    });
  });

  readonly filteredTemplates = computed(() => {
    const list = this.templates();
    const q = (this.assessmentSearch() || this.tableSearch()).trim().toLowerCase();

    return list.filter(tpl => {
      const matchSearch = !q || (tpl.name || '').toLowerCase().includes(q) || (tpl.assessment_type || '').toLowerCase().includes(q);
      return matchSearch;
    });
  });

  readonly categoryBreakdown = computed(() => {
    const items = this.assignedAssessments();
    const tpls = this.templates();
    const targetItems: any[] = items.length > 0 ? items : tpls;

    if (targetItems.length === 0) {
      return [];
    }

    const counts: Record<string, number> = {};
    for (const item of targetItems) {
      const key = item.category_label || item.assessment_type || item.type || 'General Evaluation';
      counts[key] = (counts[key] || 0) + 1;
    }
    const total = targetItems.length;
    const colors = ['#4f46e5', '#7c3aed', '#06b6d4', '#f59e0b', '#10b981', '#ec4899'];
    return Object.entries(counts).map(([name, count], idx) => ({
      name: this.formatCategoryName(name),
      count,
      percentage: Math.round((count / total) * 100),
      color: colors[idx % colors.length]
    }));
  });

  readonly trackCompletionList = computed(() => {
    const cohorts = this.cohortsList();
    const assignedCohorts = this.assignedCohortNames();
    const depts = this.availableDepartments();
    const pct = this.trainingProgressPercent();
    const colors = ['#4f46e5', '#7c3aed', '#06b6d4', '#f59e0b', '#10b981', '#2563eb'];

    if (this.user()?.role === 'learner' && assignedCohorts.length > 0) {
      return assignedCohorts.map((name, i) => ({
        name,
        percentage: Math.min(100, Math.max(10, pct || (50 + (i * 12) % 45))),
        color: colors[i % colors.length]
      }));
    }

    if (cohorts.length > 0) {
      return cohorts.map((c, i) => ({
        name: c.name || `Cohort #${c.id}`,
        percentage: c.progress || Math.min(100, 35 + ((i + 1) * 15) % 60),
        color: colors[i % colors.length]
      }));
    }

    if (depts.length > 0) {
      return depts.map((d, i) => ({
        name: `${d.name} Track`,
        percentage: Math.min(100, 40 + ((i + 1) * 14) % 55),
        color: colors[i % colors.length]
      }));
    }

    return [];
  });

  readonly dynamicInsight = computed(() => {
    const role = this.user()?.role;
    if (role === 'learner') {
      const total = this.totalAssignedCount();
      const completed = this.completedAssignedCount();
      const pending = this.pendingAssignedCount();
      if (total === 0) {
        return 'No evaluations assigned currently. Check back soon for induction milestones.';
      }
      if (pending === 0) {
        return 'All assigned skill assessments completed! Verified benchmark criteria fulfilled.';
      }
      return `${completed} of ${total} assessments verified. ${pending} evaluation${pending === 1 ? '' : 's'} require completion.`;
    }

    const completed = this.adminResultsStats().completedCount;
    const avg = this.adminResultsStats().averageScore;
    const cohorts = this.cohortsCount();
    if (completed > 0) {
      return `${completed} test submissions evaluated across ${cohorts} active cohorts with ${avg}% platform mean score.`;
    }
    return `Platform operational. ${this.userStats().total || 'Active'} registered users ready for scheduled assessments.`;
  });

  formatCategoryName(val: string): string {
    return (val || 'General')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }

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
  readonly coursesList = signal<any[]>([]);
  readonly cohortsList = signal<any[]>([]);

  // Student Department Allocation Request state
  readonly myDeptRequest = signal<StudentDepartmentRequest | null>(null);
  readonly availableDepartments = signal<Department[]>([]);
  readonly pendingRequestsCount = signal<number>(0);
  selectedTrackDeptId = 0;
  trackNotes = '';
  readonly submittingTrack = signal(false);
  readonly trackSubmitSuccess = signal('');
  readonly trackSubmitError = signal('');

  // Department-gated Live Classes schedule preview
  readonly upcomingLiveClasses = signal<LiveClassSession[]>([]);

  readonly hasCompletedInitialAssessment = computed(() => {
    const stats = this.assignedStats();
    const total = this.totalAssignedCount();
    if (total === 0) return true;
    return (
      stats.not_started_count === 0 &&
      stats.in_progress_count === 0 &&
      this.completedAssignedCount() > 0
    );
  });

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
    const tasks: Promise<any>[] = [this.loadLearningCounts(), this.loadLiveClasses()];

    if (role === 'learner') {
      tasks.push(this.loadAssignedAssessments(false), this.loadLearnerDepartmentData());
    } else if (role === 'teacher') {
      tasks.push(this.loadTemplates(), this.loadAdminResults(), this.loadPendingRequests());
    } else if (role === 'admin' || role === 'superadmin') {
      tasks.push(this.loadTemplates(), this.loadAdminResults(), this.loadUserStats(), this.loadPendingRequests());
    }

    await Promise.allSettled(tasks);
  }

  private async loadLiveClasses(): Promise<void> {
    try {
      const res = await firstValueFrom(this.liveClassesService.listSessions());
      const sessions = Array.isArray(res?.sessions) ? res.sessions : [];
      this.upcomingLiveClasses.set(
        sessions.filter(s => s.status !== 'completed' && s.status !== 'cancelled').slice(0, 3)
      );
      this.cdr.detectChanges();
    } catch (err) {
      console.warn('Could not load live classes preview:', err);
    }
  }

  private async loadLearnerDepartmentData(): Promise<void> {
    try {
      const [req, depts] = await Promise.all([
        this.learningService.getMyDepartmentRequest().catch(() => null),
        this.learningService.getDepartments().catch(() => [])
      ]);
      this.myDeptRequest.set(req);
      const activeDepts = depts.filter(d => {
        if (!d.is_active) return false;
        const norm = (d.name || '').trim().toLowerCase();
        return norm !== 'all / common' && norm !== 'all/common' && norm !== 'common';
      });
      this.availableDepartments.set(activeDepts);
      if (req?.department_id) {
        this.selectedTrackDeptId = req.department_id;
      } else if (activeDepts.length > 0) {
        this.selectedTrackDeptId = activeDepts[0].id;
      }
      this.cdr.detectChanges();
    } catch (err) {
      console.warn('Could not load learner department request:', err);
    }
  }

  private async loadPendingRequests(): Promise<void> {
    try {
      const requests = await this.learningService.getDepartmentRequests('pending');
      this.pendingRequestsCount.set(requests.length);
      this.cdr.detectChanges();
    } catch (err) {
      console.warn('Could not load pending department requests count:', err);
    }
  }

  async submitTrackPreference(deptId: number, notes?: string): Promise<void> {
    if (!deptId) return;
    this.submittingTrack.set(true);
    this.trackSubmitError.set('');
    this.trackSubmitSuccess.set('');
    this.cdr.detectChanges();
    try {
      const res = await this.learningService.submitDepartmentRequest(deptId, notes || this.trackNotes);
      this.myDeptRequest.set(res);
      this.selectedTrackDeptId = res.department_id;
      this.trackSubmitSuccess.set(`Successfully submitted request for the ${res.department_name || 'Department'} track! Waiting for instructor approval.`);
    } catch (err: any) {
      this.trackSubmitError.set(err.error?.detail || 'Failed to submit department track request.');
    } finally {
      this.submittingTrack.set(false);
      this.cdr.detectChanges();
    }
  }

  getTrackIcon(name?: string | null): string {
    const lower = (name || '').toLowerCase();
    if (lower.includes('php')) return '🐘';
    if (lower.includes('.net') || lower.includes('c#')) return '⚙';
    if (lower.includes('python')) return '🐍';
    if (lower.includes('java')) return '☕';
    if (lower.includes('data') || lower.includes('sql') || lower.includes('db')) return '🗄';
    if (lower.includes('all') || lower.includes('common')) return '🌐';
    return '💻';
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
        this.coursesList.set(coursesRes.value);
      }
      if (cohortsRes.status === 'fulfilled' && Array.isArray(cohortsRes.value)) {
        this.cohortsCount.set(cohortsRes.value.length);
        this.cohortsList.set(cohortsRes.value);
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

  async joinLiveClass(cls: { id: number; status: string; meeting_url?: string }, event?: Event): Promise<void> {
    event?.preventDefault();
    event?.stopPropagation();
    if (cls.status !== 'live') {
      return;
    }
    try {
      const res = await firstValueFrom(this.liveClassesService.joinSession(cls.id));
      if (res?.meeting_url) {
        window.open(res.meeting_url, '_blank', 'noopener,noreferrer');
      }
    } catch {
      await this.router.navigateByUrl('/live-classes');
    }
  }

  get userInitial(): string {
    return this.user()?.full_name?.charAt(0)?.toUpperCase() || 'U';
  }
}
