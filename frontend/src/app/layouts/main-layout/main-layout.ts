import { Component, OnInit, HostListener, inject, ElementRef, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
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

interface CommandItem {
  id: string;
  label: string;
  description: string;
  group: string;
  route?: string;
  action?: () => void;
  keywords: string;
}

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterOutlet, RouterLink, RouterLinkActive, BrandLogo],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss'
})
export class MainLayout implements OnInit {
  sidebarOpen = false;
  profileMenuOpen = false;
  user: CurrentUser | null = null;

  commandPaletteOpen = signal(false);
  commandQuery = signal('');
  commandActiveIndex = signal(0);

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

  get filteredCommands(): CommandItem[] {
    const items: CommandItem[] = [];

    if (!this.isAssessmentOnlyMode) {
      items.push({
        id: 'dashboard',
        label: 'Executive Dashboard',
        description: 'Overview metrics, analytics & telemetry',
        group: 'Navigation',
        route: '/dashboard',
        keywords: 'home overview stats analytics kpi'
      });

      items.push(
        {
          id: 'courses',
          label: 'Course Vaults',
          description: 'Department curricula, syllabus & permanent resources',
          group: 'Academic & Learning',
          route: '/courses',
          keywords: 'vault curriculum syllabus materials study'
        },
        {
          id: 'cohorts',
          label: 'Cohorts & Batches',
          description: 'Manage active batches, timetables & assignments',
          group: 'Academic & Learning',
          route: '/cohorts',
          keywords: 'batches schedule timetable attendance quizzes'
        },
        {
          id: 'live-classes',
          label: 'Live Classes',
          description: 'Department live streams & scheduled video workshops',
          group: 'Academic & Learning',
          route: '/live-classes',
          keywords: 'video meeting stream session workshop'
        }
      );

      if (this.authService.hasRole('superadmin', 'admin', 'teacher')) {
        items.push({
          id: 'departments',
          label: 'Departments & Tracks',
          description: 'Engineering tracks & joinee allocation requests',
          group: 'Academic & Learning',
          route: '/departments',
          keywords: 'tracks specialization requests approve'
        });
      }
    }

    if (this.isLearner) {
      items.push(
        {
          id: 'my-assessments',
          label: 'My Assessments',
          description: 'Assigned evaluations & exam center',
          group: 'Evaluation Suite',
          route: '/my-assessments',
          keywords: 'exam test take quiz assigned'
        },
        {
          id: 'my-results',
          label: 'My Results',
          description: 'Scores, performance breakdown & history',
          group: 'Evaluation Suite',
          route: '/my-results',
          keywords: 'score grade history marks'
        },
        {
          id: 'my-reports',
          label: 'Official Reports',
          description: 'Developmental report cards & radar charts',
          group: 'Evaluation Suite',
          route: '/my-reports',
          keywords: 'report card certificate radar'
        }
      );
      if (this.canSelectDepartment) {
        items.push({
          id: 'dept-select',
          label: 'Department Selection',
          description: 'Choose your engineering specialization track',
          group: 'Onboarding',
          route: '/department-selection',
          keywords: 'onboarding select track department'
        });
      }
    }

    if (this.authService.hasRole('admin', 'teacher', 'superadmin')) {
      items.push(
        {
          id: 'assessments',
          label: 'Assessment Management',
          description: 'Author tests, question banks & preview exams',
          group: 'Evaluation Suite',
          route: '/assessments',
          keywords: 'create template questions exam bank'
        },
        {
          id: 'assessment-results',
          label: 'Learner Results',
          description: 'Review candidate submissions, proctoring & history',
          group: 'Evaluation Suite',
          route: '/assessment-results',
          keywords: 'submissions scores grades proctoring'
        }
      );
    }

    if (this.authService.hasRole('superadmin', 'admin')) {
      items.push({
        id: 'users',
        label: 'User Management',
        description: 'Provision accounts, roles & teacher tracks',
        group: 'Administration',
        route: '/users',
        keywords: 'accounts roles admins teachers learners'
      });
    }

    if (!this.isAssessmentOnlyMode) {
      items.push({
        id: 'profile',
        label: 'My Profile & Security',
        description: 'Account details, password & permissions',
        group: 'Account',
        route: '/profile',
        keywords: 'account settings password security'
      });
    }

    items.push({
      id: 'toggle-theme',
      label: this.themeService.isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode',
      description: 'Toggle application appearance theme instantly',
      group: 'Preferences',
      action: () => this.themeService.toggleTheme(),
      keywords: 'theme dark light appearance mode color'
    });

    const q = this.commandQuery().trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q) ||
        item.group.toLowerCase().includes(q) ||
        item.keywords.includes(q)
    );
  }

  openCommandPalette(): void {
    this.profileMenuOpen = false;
    this.commandQuery.set('');
    this.commandActiveIndex.set(0);
    this.commandPaletteOpen.set(true);
    setTimeout(() => {
      const input = this.elementRef.nativeElement.querySelector('.cmd-search-input') as HTMLInputElement | null;
      input?.focus();
    }, 20);
  }

  closeCommandPalette(): void {
    this.commandPaletteOpen.set(false);
    this.commandQuery.set('');
  }

  onCommandQueryChange(val: string): void {
    this.commandQuery.set(val);
    this.commandActiveIndex.set(0);
  }

  executeCommand(cmd: CommandItem): void {
    this.closeCommandPalette();
    this.sidebarOpen = false;
    if (cmd.action) {
      cmd.action();
    } else if (cmd.route) {
      void this.router.navigate([cmd.route]);
    }
  }

  onCommandKeydown(event: KeyboardEvent): void {
    const list = this.filteredCommands;
    if (!list.length) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.commandActiveIndex.set((this.commandActiveIndex() + 1) % list.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.commandActiveIndex.set((this.commandActiveIndex() - 1 + list.length) % list.length);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const target = list[this.commandActiveIndex()] || list[0];
      if (target) this.executeCommand(target);
    }
  }

  @HostListener('document:keydown', ['$event'])
  onGlobalKeydown(event: KeyboardEvent): void {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      if (this.commandPaletteOpen()) {
        this.closeCommandPalette();
      } else {
        this.openCommandPalette();
      }
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.profileMenuOpen = false;
    this.sidebarOpen = false;
    this.closeCommandPalette();
  }
}
