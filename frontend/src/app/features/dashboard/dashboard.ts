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
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  readonly user = signal<CurrentUser | null>(null);
  readonly loading = signal(true);
  readonly errorMessage = signal('');

  // Learner data
  readonly templates = signal<AssessmentTemplate[]>([]);
  readonly learnerResults = signal<UserAssessmentResultItem[]>([]);

  // Admin & Teacher data
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

  readonly coursesCount = signal<number>(4);
  readonly cohortsCount = signal<number>(2);
  readonly departmentsCount = signal<number>(3);

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
    const results = this.learnerResults();
    if (results.length > 0) score += 25; // At least one assessment
    if (results.length >= 4) score += 25; // All 4 assessments
    score += 25; // Course track assignment
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
    return this.learnerResults().find(r => r.assessment_type === type && r.status === 'completed');
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
