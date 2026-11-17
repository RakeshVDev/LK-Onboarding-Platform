import { Component, OnInit, HostListener, inject, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet
} from '@angular/router';
import { AuthService, CurrentUser } from '../../core/services/auth.service';
import { AssessmentStatusService } from '../../core/services/assessment-status.service';
import { OnboardingService } from '../../core/services/onboarding.service';
import { ThemeService } from '../../core/services/theme.service';
import { BrandLogo } from '../../shared/components/brand-logo/brand-logo';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive, BrandLogo],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss'
})
export class MainLayout implements OnInit {
  sidebarOpen = false;
  profileMenuOpen = false;
  user: CurrentUser | null = null;

  public readonly authService = inject(AuthService);
  public readonly assessmentStatusService = inject(AssessmentStatusService);
  public readonly onboardingService = inject(OnboardingService);
  public readonly themeService = inject(ThemeService);
  private readonly router = inject(Router);
  private readonly elementRef = inject(ElementRef);

  async ngOnInit(): Promise<void> {
    this.user = this.authService.getCurrentUserSnapshot();
    if (!this.user) {
      try {
        this.user = await this.authService.getCurrentUser();
      } catch {
        // Auth guard will handle unauthorized redirection if needed
      }
    }
    if (this.isLearner) {
      await Promise.allSettled([
        this.assessmentStatusService.getStatus(),
        this.onboardingService.getPermissions()
      ]);
    }
  }

  get isLearner(): boolean {
    return (
      (this.user?.role || '').toLowerCase() === 'learner' ||
      this.authService.hasRole('learner')
    );
  }

  get currentSectionName(): string {
    const url = this.router.url;
    if (url.includes('dashboard')) return 'Dashboard';
    if (url.includes('users')) return 'User Management';
    if (url.includes('cohorts')) return 'Cohorts & Batches';
    if (url.includes('courses')) return 'Courses';
    if (url.includes('live-classes')) return 'Live Classes';
    if (url.includes('departments')) return 'Departments';
    if (url.includes('assessments')) return 'Assessment Suite';
    if (url.includes('results')) return 'Results';
    if (url.includes('reports')) return 'Reports';
    if (url.includes('profile')) return 'My Profile';
    return 'Overview';
  }

  get currentSectionGroup(): string {
    const url = this.router.url;
    if (url.includes('dashboard')) return 'Workspace';
    if (url.includes('courses') || url.includes('cohorts') || url.includes('live-classes') || url.includes('departments')) {
      return 'Academic & Learning';
    }
    if (url.includes('assessments') || url.includes('results') || url.includes('reports') || url.includes('my-')) {
      return 'Evaluation Suite';
    }
    if (url.includes('users')) return 'Administration';
    if (url.includes('profile')) return 'Account';
    return 'Workspace';
  }

  get isAssessmentOnlyMode(): boolean {
    if (!this.isLearner) return false;
    const perms = this.onboardingService.permissionsState();
    if (perms) {
      return !perms.is_unlocked;
    }
    return !Boolean(this.user?.department_approved);
  }

  get isNavLocked(): boolean {
    return this.isAssessmentOnlyMode;
  }

  get isOnboardingUnlocked(): boolean {
    return !this.isAssessmentOnlyMode;
  }

  get onboardingStage(): string {
    return (
      this.onboardingService.permissionsState()?.onboarding_stage ||
      this.user?.onboarding_stage ||
      'assessment_pending'
    );
  }

  get onboardingStatusMessage(): string {
    return (
      this.onboardingService.permissionsState()?.status_message ||
      'Complete all assigned assessments to unlock onboarding progression.'
    );
  }

  get canSelectDepartment(): boolean {
    if (!this.isLearner) return false;
    const perms = this.onboardingService.permissionsState();
    if (perms) {
      return perms.can_select_department;
    }
    return Boolean(this.user?.is_activated_by_admin && !this.user?.department_approved);
  }

  get approvedDepartmentName(): string | null {
    const perms = this.onboardingService.permissionsState();
    return perms?.selected_department_name || this.user?.selected_department_name || null;
  }

  get homeRoute(): string {
    if (!this.isLearner || this.isOnboardingUnlocked) {
      return '/dashboard';
    }
    return this.canSelectDepartment ? '/department-selection' : '/my-assessments';
  }

  get assessmentProgressText(): string {
    const s = this.assessmentStatusService.statusState();
    if (!s || !s.total_assigned) return 'all assigned tests';
    return `${s.completed_count ?? 0}/${s.total_assigned} completed`;
  }

  get pendingAssessmentsCount(): number {
    return this.assessmentStatusService.statusState()?.pending_count ?? 0;
  }

  onNavClick(event: Event, locked: boolean): void {
    if (locked) {
      event.preventDefault();
      event.stopPropagation();
      this.sidebarOpen = false;
      this.profileMenuOpen = false;
      void this.router.navigate([this.homeRoute]);
      return;
    }
    this.sidebarOpen = false;
    this.profileMenuOpen = false;
  }

  toggleProfileMenu(event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.profileMenuOpen = !this.profileMenuOpen;
  }

  closeProfileMenu(): void {
    this.profileMenuOpen = false;
  }

  get userInitial(): string {
    return this.user?.full_name?.charAt(0)?.toUpperCase() || 'U';
  }

  get roleDisplayName(): string {
    switch (this.user?.role) {
      case 'superadmin': return 'Super Admin';
      case 'admin': return 'Administrator';
      case 'teacher': return 'Academic Faculty';
      case 'learner': return 'New Joinee';
      default: return 'User';
    }
  }

  logout(): void {
    this.profileMenuOpen = false;
    this.sidebarOpen = false;
    this.assessmentStatusService.clearCache();
    this.onboardingService.clearCache();
    this.authService.logout();
    void this.router.navigateByUrl('/login');
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (this.profileMenuOpen) {
      const target = event.target as HTMLElement;
      const topbarProfile = this.elementRef.nativeElement.querySelector('.topbar-profile-container');
      if (topbarProfile && !topbarProfile.contains(target)) {
        this.profileMenuOpen = false;
      }
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.profileMenuOpen = false;
    this.sidebarOpen = false;
  }
}
