import { describe, it, expect, beforeEach, vi } from 'vitest';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';

import { Cohorts } from './cohorts';
import { AuthService, CurrentUser, UserRole } from '../../core/services/auth.service';
import { CohortFullData, CohortService } from '../../core/services/cohort.service';
import { UserManagementService } from '../../core/services/user-management.service';
import { LearningService } from '../../core/services/learning.service';
import { LiveClassesService } from '../../core/services/live-classes.service';

describe('Cohorts (SuperAdmin-Only Teacher/Learner Mode Switcher)', () => {
  const createMinimalCohortData = (): CohortFullData => ({
    details: {
      id: 'c1',
      name: 'ASE Cohort 2026',
      code: 'ASE-26',
      department: 'Python',
      departmentId: 1,
      departmentName: 'Python',
      track: 'Python Engineering Track',
      status: 'active',
      startDate: '2026-10-01',
      endDate: '2026-12-31',
      durationWeeks: 12,
      currentWeek: 2,
      currentModule: 'FastAPI Core',
      leadTrainer: {
        name: 'Faculty Lead',
        title: 'Lead Instructor',
        email: 'faculty@example.com',
        avatar: 'FL',
        officeHours: 'Mon 16:00',
        bio: 'Backend lead',
      },
      mentors: [],
      description: 'Cohort overview',
      objectives: ['Clean Architecture'],
      meetingLink: 'https://meet.example.com/ase-live',
      slackChannel: '#ase-cohort',
      githubOrg: 'lk-onboarding',
      isLiveActive: false,
    },
    batches: [],
    activeBatchId: 'b1',
    curriculum: [],
    sessions: [],
    materials: [],
    assignments: [],
    attendance: {
      percentage: 100,
      totalSessions: 0,
      attended: 0,
      missed: 0,
      excused: 0,
      late: 0,
      minimumRequired: 75,
      checkedInToday: false,
      history: [],
    },
    attendanceMatrix: {
      dateRangeLabel: 'Nov 2026',
      days: [],
      students: [],
    },
    quizzes: [],
    announcements: [],
    members: [],
    progress: {
      overallPercentage: 0,
      modulesCompleted: 0,
      totalModules: 0,
      assignmentsSubmitted: 0,
      totalAssignments: 0,
      quizzesPassed: 0,
      totalQuizzes: 0,
      attendanceRate: 100,
      milestones: [],
      earnedBadges: [],
    },
    discussions: [],
  });

  async function mountWithRole(role: UserRole): Promise<ComponentFixture<Cohorts>> {
    const mockUser: CurrentUser = {
      id: 10,
      full_name: `${role} User`,
      email: `${role}@lk.local`,
      role,
      is_active: true,
      department_approved: true,
      selected_department_id: '1',
      selected_department_name: 'Python',
    };

    const data$ = new BehaviorSubject<CohortFullData>(createMinimalCohortData());

    await TestBed.configureTestingModule({
      imports: [Cohorts],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            getCurrentUserSnapshot: () => mockUser,
            hasRole: (...roles: UserRole[]) => roles.includes(mockUser.role),
          },
        },
        {
          provide: CohortService,
          useValue: {
            data$: data$.asObservable(),
            getCohortData: () => data$.value,
            sanitizeTrainerNames: vi.fn(),
            syncLearnersWithPlatform: vi.fn(),
          },
        },
        {
          provide: UserManagementService,
          useValue: {
            listUsers: vi.fn(async () => []),
            listTeachers: vi.fn(async () => []),
            listLearners: vi.fn(async () => []),
            getTeachers: vi.fn(() => []),
            getLearners: vi.fn(() => []),
          },
        },
        {
          provide: LearningService,
          useValue: {
            getDepartments: vi.fn(async () => [
              { id: 1, name: 'Python', description: 'Python track', is_active: true },
            ]),
            getMyDepartmentRequest: vi.fn(async () => ({
              id: 1,
              user_id: 10,
              department_id: 1,
              department_name: 'Python',
              status: 'approved',
              created_at: '2026-10-01',
              updated_at: '2026-10-01',
            })),
            getDepartmentRequests: vi.fn(async () => []),
          },
        },
        {
          provide: LiveClassesService,
          useValue: {
            getAssignableHosts: vi.fn(() => of([])),
          },
        },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(Cohorts);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(() => {
    TestBed.resetTestingModule();
  });

  it('shows the Teacher/Learner mode switcher to superadmin and permits switching modes', async () => {
    const fixture = await mountWithRole('superadmin');
    const switcher = fixture.nativeElement.querySelector('.role-mode-switcher');
    expect(switcher).not.toBeNull();
    expect(fixture.componentInstance.viewMode()).toBe('teacher');

    fixture.componentInstance.toggleViewMode('learner');
    expect(fixture.componentInstance.viewMode()).toBe('learner');

    fixture.componentInstance.toggleViewMode('teacher');
    expect(fixture.componentInstance.viewMode()).toBe('teacher');
  });

  it('hides the mode switcher from admin and ignores toggleViewMode calls', async () => {
    const fixture = await mountWithRole('admin');
    expect(fixture.nativeElement.querySelector('.role-mode-switcher')).toBeNull();
    expect(fixture.componentInstance.viewMode()).toBe('teacher');

    fixture.componentInstance.toggleViewMode('learner');
    expect(fixture.componentInstance.viewMode()).toBe('teacher');
  });

  it('hides the mode switcher from teacher and ignores toggleViewMode calls', async () => {
    const fixture = await mountWithRole('teacher');
    expect(fixture.nativeElement.querySelector('.role-mode-switcher')).toBeNull();
    expect(fixture.componentInstance.viewMode()).toBe('teacher');

    fixture.componentInstance.toggleViewMode('learner');
    expect(fixture.componentInstance.viewMode()).toBe('teacher');
  });

  it('hides the mode switcher from learner and keeps viewMode locked to learner', async () => {
    const fixture = await mountWithRole('learner');
    expect(fixture.nativeElement.querySelector('.role-mode-switcher')).toBeNull();
    expect(fixture.componentInstance.viewMode()).toBe('learner');

    fixture.componentInstance.toggleViewMode('teacher');
    expect(fixture.componentInstance.viewMode()).toBe('learner');
  });
});
