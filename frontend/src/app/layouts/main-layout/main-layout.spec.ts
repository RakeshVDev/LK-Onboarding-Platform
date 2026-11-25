import { describe, it, expect, beforeEach, vi } from 'vitest';
import { provideZonelessChangeDetection, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { MainLayout } from './main-layout';
import { AuthService, CurrentUser } from '../../core/services/auth.service';
import { AssessmentStatusService } from '../../core/services/assessment-status.service';
import { NavigationPermissions, OnboardingService } from '../../core/services/onboarding.service';

describe('MainLayout (Strict Dynamic Sidebar Navigation)', () => {
  let permissionsSig = signal<NavigationPermissions | null>(null);
  let statusSig = signal<any>(null);
  let learnerUser: CurrentUser;

  const createMockPermissions = (isUnlocked: boolean): NavigationPermissions => ({
    role: 'learner',
    onboarding_stage: isUnlocked ? 'unlocked' : 'assessment_pending',
    all_assessments_completed: isUnlocked,
    is_activated_by_admin: isUnlocked,
    selected_department_id: isUnlocked ? '3' : null,
    selected_department_name: isUnlocked ? 'Python' : null,
    department_approved: isUnlocked,
    is_unlocked: isUnlocked,
    assessment_only_mode: !isUnlocked,
    can_select_department: false,
    redirect_to: isUnlocked ? '/dashboard' : '/my-assessments',
    allowed_items: isUnlocked
      ? ['dashboard', 'courses', 'cohorts', 'assessment', 'result', 'report', 'profile']
      : ['assessment', 'result', 'report'],
    locked_items: isUnlocked ? [] : ['dashboard', 'courses', 'cohorts', 'profile'],
    nav_items: [],
    status_message: isUnlocked ? 'Approved department: Python.' : 'Complete all assessments.'
  });

  async function mountLayout(isUnlocked: boolean): Promise<ComponentFixture<MainLayout>> {
    learnerUser = {
      id: 7,
      full_name: 'Joinee One',
      email: 'joinee@lk.local',
      role: 'learner',
      is_active: true,
      department_approved: isUnlocked
    };
    const perms = createMockPermissions(isUnlocked);
    permissionsSig.set(perms);

    TestBed.configureTestingModule({
      imports: [MainLayout],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([
          { path: 'my-assessments', children: [] },
          { path: 'dashboard', children: [] },
        ]),
        {
          provide: AuthService,
          useValue: {
            getCurrentUserSnapshot: () => learnerUser,
            getCurrentUser: async () => learnerUser,
            hasRole: (...roles: string[]) => roles.includes(learnerUser.role),
            logout: vi.fn()
          }
        },
        {
          provide: AssessmentStatusService,
          useValue: {
            statusState: statusSig.asReadonly(),
            getStatus: vi.fn(async () => ({ status: 'not_started', session_id: null, pending_count: 2 })),
            clearCache: vi.fn()
          }
        },
        {
          provide: OnboardingService,
          useValue: {
            permissionsState: permissionsSig.asReadonly(),
            getPermissions: vi.fn(async () => perms),
            clearCache: vi.fn()
          }
        }
      ]
    });

    const fixture = TestBed.createComponent(MainLayout);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(() => {
    permissionsSig = signal<NavigationPermissions | null>(null);
    statusSig = signal<any>({ status: 'not_started', pending_count: 2 });
  });

  it('strictly renders ONLY Assessment, Result, and Report sidebar items for pending joinee', async () => {
    const fixture = await mountLayout(false);
    const navLinks = Array.from(
      fixture.nativeElement.querySelectorAll('.nav-groups nav.navigation a')
    ) as HTMLAnchorElement[];

    const labels = navLinks.map(a =>
      (a.querySelector('span')?.textContent || '').trim()
    );
    expect(labels).toEqual(['Assessment', 'Result', 'Report']);
    expect(fixture.nativeElement.textContent).not.toContain('Courses');
    expect(fixture.nativeElement.textContent).not.toContain('Cohorts');
    expect(fixture.nativeElement.textContent).not.toContain('Live Classes');
    const logoImgs = fixture.nativeElement.querySelectorAll('img.csm-logo-img');
    expect(logoImgs.length).toBeGreaterThanOrEqual(1);
  });

  it('unlocks Dashboard, Courses, and Cohorts once admin approves department while keeping Live Classes removed from sidebar', async () => {
    const fixture = await mountLayout(true);
    const navLinks = Array.from(
      fixture.nativeElement.querySelectorAll('.nav-groups nav.navigation a')
    ) as HTMLAnchorElement[];

    const labels = navLinks.map(a =>
      (a.querySelector('span')?.textContent || '').trim()
    );
    expect(labels).toContain('Dashboard');
    expect(labels).toContain('Courses');
    expect(labels).toContain('Cohorts');
    expect(labels).not.toContain('Live Classes');
    expect(labels).toContain('Assessment');
    expect(labels).toContain('Result');
    expect(labels).toContain('Report');
  });
});

