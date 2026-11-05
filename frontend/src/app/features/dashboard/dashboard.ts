import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import { AuthService, CurrentUser, UserRole } from '../../core/services/auth.service';
import {
  AssessmentService,
  AssessmentTemplate,
  UserAssessmentResultItem
} from '../assessments/services/assessment';
import { UserManagementService, ManagedUser } from '../../core/services/user-management.service';
import { LearningService } from '../../core/services/learning.service';

interface QuickAction {
  title: string;
  description: string;
  icon: string;
  route: string;
  badge?: string;
  accent: 'blue' | 'indigo' | 'emerald' | 'amber' | 'purple';
}

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

  readonly user = signal<CurrentUser | null>(null);
  readonly loading = signal(true);
  readonly errorMessage = signal('');

  // Learner data
  readonly templates = signal<AssessmentTemplate[]>([]);
  readonly learnerResults = signal<UserAssessmentResultItem[]>([]);

  // Filtered completed results
  readonly completedLearnerResults = computed(() => {
    return this.learnerResults().filter(r => r.status === 'completed');
  });

  // Accurate true performance average across all completed assessments
  readonly learnerAverageScore = computed(() => {
    const completed = this.completedLearnerResults();
    if (completed.length === 0) return 0;
    const sum = completed.reduce((acc, curr) => acc + (curr.overall_percentage || 0), 0);
    return Math.round(sum / completed.length);
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

  // Onboarding progress calculation for learners
  readonly onboardingProgress = computed(() => {
    let score = 25; // 25% for verified account creation
    const completed = this.completedLearnerResults();
    // 50% for completed assessments (up to 4 assessments, each 12.5%)
    score += Math.min(50, Math.round((completed.length / 4) * 50));
    // 25% for course curriculum assignment
    if (this.coursesCount() > 0) {
      score += 25;
    }
    return Math.min(100, score);
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

      // Load role-specific data in parallel
      await this.loadRoleSpecificData(currentUser.role);

    } catch (err) {
      console.error('Dashboard load error:', err);
      this.errorMessage.set('Unable to load your dashboard. Please sign in again.');
      this.authService.logout();
      await this.router.navigateByUrl('/login');
    } finally {
      this.loading.set(false);
    }
  }

  private async loadRoleSpecificData(role: UserRole): Promise<void> {
    // 1. Fetch real learning entity counts dynamically
    await this.loadLearningCounts();

    // 2. Role-specific calls
    if (role === 'learner') {
      await Promise.allSettled([
        this.loadTemplates(),
        this.loadLearnerResults()
      ]);
    } else if (role === 'teacher') {
      await Promise.allSettled([
        this.loadTemplates(),
        this.loadAdminResults()
      ]);
    } else if (role === 'admin' || role === 'superadmin') {
      await Promise.allSettled([
        this.loadTemplates(),
        this.loadAdminResults(),
        this.loadUserStats()
      ]);
    }
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

  private async loadLearnerResults(): Promise<void> {
    try {
      const results = await firstValueFrom(this.assessmentService.getMyResults());
      this.learnerResults.set(results || []);
    } catch (err) {
      console.warn('Could not load learner results on dashboard:', err);
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

  // Learner test status helper
  getCompletedTest(type: string): UserAssessmentResultItem | undefined {
    const cleanType = type.toLowerCase().replace(/[^a-z0-9]/g, '');
    return this.learnerResults().find(r => {
      if (r.status !== 'completed') return false;
      const rType = (r.assessment_type || '').toLowerCase().replace(/[^a-z0-9]/g, '');
      const rName = (r.template_name || '').toLowerCase();
      if (rType === cleanType) return true;
      if (type === 'logical_reasoning' && (rName.includes('logical') || rType.includes('logical'))) return true;
      if (type === 'english_grammar' && (rName.includes('english') || rName.includes('grammar') || rType.includes('grammar') || rType.includes('english'))) return true;
      if (type === 'technical' && (rName.includes('technical') || rType.includes('technical'))) return true;
      if (type === 'programming' && (rName.includes('programming') || rType.includes('programming'))) return true;
      if (type === 'psychometric' && (rName.includes('psychometric') || rType.includes('psychometric') || rName.includes('assessment-2') || rName.includes('assessment 2'))) return true;
      return false;
    });
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
