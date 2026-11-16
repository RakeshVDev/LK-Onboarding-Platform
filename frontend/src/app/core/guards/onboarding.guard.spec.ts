import { describe, it, expect, beforeEach, vi } from 'vitest';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot, UrlTree, provideRouter } from '@angular/router';

import { assessmentCompletionGuard } from './assessment-completion.guard';
import { AuthService, CurrentUser } from '../services/auth.service';
import { NavigationPermissions, OnboardingService } from '../services/onboarding.service';

describe('assessmentCompletionGuard (strict onboarding route guard)', () => {
  let mockUser: CurrentUser;
  let mockPermissions: NavigationPermissions;
  let router: Router;

  const routeWithKey = (navKey?: string): ActivatedRouteSnapshot =>
    ({ data: navKey ? { navKey } : {} } as unknown as ActivatedRouteSnapshot);

  const runGuard = async (navKey?: string) =>
    TestBed.runInInjectionContext(() =>
      assessmentCompletionGuard(routeWithKey(navKey), {} as RouterStateSnapshot)
    );

  beforeEach(() => {
    mockUser = {
      id: 11,
      full_name: 'Joinee',
      email: 'joinee@lk.local',
      role: 'learner',
      is_active: true
    };
    mockPermissions = {
      role: 'learner',
      onboarding_stage: 'assessment_pending',
      all_assessments_completed: false,
      is_activated_by_admin: false,
      selected_department_id: null,
      selected_department_name: null,
      department_approved: false,
      is_unlocked: false,
      assessment_only_mode: true,
      can_select_department: false,
      redirect_to: '/my-assessments',
      allowed_items: ['assessment', 'result', 'report'],
      locked_items: ['dashboard', 'courses', 'cohorts', 'departments', 'users', 'profile'],
      nav_items: [],
      status_message: 'Pending'
    };

    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        {
          provide: AuthService,
          useValue: { getCurrentUser: vi.fn(async () => mockUser) }
        },
        {
          provide: OnboardingService,
          useValue: { getPermissions: vi.fn(async () => mockPermissions) }
        }
      ]
    });
    router = TestBed.inject(Router);
  });

  it('allows only assessment, result, and report during Stage 1 & 2 and blocks dashboard/courses/cohorts/department-selection', async () => {
    expect(await runGuard('assessment')).toBe(true);
    expect(await runGuard('result')).toBe(true);
    expect(await runGuard('report')).toBe(true);

    for (const blocked of ['dashboard', 'courses', 'cohorts', 'live_classes', 'profile', 'department_selection']) {
      const res = await runGuard(blocked);
      expect(res instanceof UrlTree).toBe(true);
      expect(router.serializeUrl(res as UrlTree)).toBe('/my-assessments');
    }

    mockPermissions.onboarding_stage = 'awaiting_activation';
    mockPermissions.all_assessments_completed = true;
    const blockedDept = await runGuard('department_selection');
    expect(router.serializeUrl(blockedDept as UrlTree)).toBe('/my-assessments');
  });

  it('allows department-selection once activated by admin while keeping courses/cohorts/dashboard locked', async () => {
    mockPermissions.onboarding_stage = 'department_selection';
    mockPermissions.all_assessments_completed = true;
    mockPermissions.is_activated_by_admin = true;
    mockPermissions.can_select_department = true;
    mockPermissions.redirect_to = '/department-selection';

    expect(await runGuard('department_selection')).toBe(true);
    expect(await runGuard('assessment')).toBe(true);
    expect(await runGuard('result')).toBe(true);
    expect(await runGuard('report')).toBe(true);

    const coursesRes = await runGuard('courses');
    expect(router.serializeUrl(coursesRes as UrlTree)).toBe('/department-selection');
  });

  it('unlocks all routes once department is approved and redirects /department-selection to /dashboard', async () => {
    mockPermissions.onboarding_stage = 'unlocked';
    mockPermissions.is_unlocked = true;
    mockPermissions.assessment_only_mode = false;
    mockPermissions.department_approved = true;
    mockPermissions.redirect_to = '/dashboard';

    expect(await runGuard('dashboard')).toBe(true);
    expect(await runGuard('courses')).toBe(true);
    expect(await runGuard('cohorts')).toBe(true);
    expect(await runGuard('live_classes')).toBe(true);

    const deptRedirect = await runGuard('department_selection');
    expect(router.serializeUrl(deptRedirect as UrlTree)).toBe('/dashboard');
  });

  it('grants staff roles direct access', async () => {
    mockUser.role = 'admin';
    expect(await runGuard('dashboard')).toBe(true);
    expect(await runGuard('users')).toBe(true);
  });
});

