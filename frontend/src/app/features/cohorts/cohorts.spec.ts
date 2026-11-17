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
    batches: [
      { id: 'b-py', name: 'Python Batch', learnerCount: 5, startDate: '2026-10-01', endDate: '2026-12-31', status: 'current', departmentName: 'Python', departmentId: 1 },
      { id: 'b-java', name: 'Java Batch', learnerCount: 5, startDate: '2026-10-01', endDate: '2026-12-31', status: 'current', departmentName: 'Java', departmentId: 2 },
      { id: 'b-common', name: 'Common Batch', learnerCount: 5, startDate: '2026-10-01', endDate: '2026-12-31', status: 'current', departmentName: 'All / Common', departmentId: 99 },
    ],
    activeBatchId: 'b-py',
    curriculum: [
      { id: 'ch-py', title: 'Python Core', sequenceOrder: 1, departmentName: 'Python', departmentId: 1, lessons: [{ id: 'l-py', title: 'FastAPI Intro', type: 'video', departmentName: 'Python', departmentId: 1 }] },
      { id: 'ch-java', title: 'Java Core', sequenceOrder: 2, departmentName: 'Java', departmentId: 2, lessons: [{ id: 'l-java', title: 'Spring Boot Intro', type: 'video', departmentName: 'Java', departmentId: 2 }] },
      { id: 'ch-common', title: 'Common Foundations', sequenceOrder: 3, departmentName: 'All / Common', departmentId: 99, lessons: [{ id: 'l-com', title: 'Git Intro', type: 'text', departmentName: 'All / Common', departmentId: 99 }] },
    ],
    sessions: [
      { id: 's-py', title: 'Python Live Class', module: 'Mod 1', trainer: 'Faculty Lead', date: 'Today', time: '10:00 AM', duration: '1h', status: 'today', location: 'Meet', meetingUrl: 'https://meet.example.com/py', topics: ['FastAPI'], departmentName: 'Python', departmentId: 1 },
      { id: 's-java', title: 'Java Live Class', module: 'Mod 1', trainer: 'Java Lead', date: 'Tomorrow', time: '11:00 AM', duration: '1h', status: 'upcoming', location: 'Meet', meetingUrl: 'https://meet.example.com/java', topics: ['Spring'], departmentName: 'Java', departmentId: 2 },
      { id: 's-common', title: 'Common Live Class', module: 'Mod 0', trainer: 'Faculty Lead', date: 'Today', time: '09:00 AM', duration: '1h', status: 'today', location: 'Meet', meetingUrl: 'https://meet.example.com/common', topics: ['Git'], departmentName: 'All / Common', departmentId: 99 },
    ],
    materials: [
      { id: 'm-py', title: 'Python Handbook', module: 'Mod 1', type: 'pdf', size: '1 MB', uploadedAt: 'Today', author: 'Faculty Lead', downloadUrl: '#', description: 'Python docs', departmentName: 'Python', departmentId: 1 },
      { id: 'm-java', title: 'Java Handbook', module: 'Mod 1', type: 'pdf', size: '1 MB', uploadedAt: 'Today', author: 'Java Lead', downloadUrl: '#', description: 'Java docs', departmentName: 'Java', departmentId: 2 },
      { id: 'm-common', title: 'Common Handbook', module: 'Mod 0', type: 'pdf', size: '1 MB', uploadedAt: 'Today', author: 'Faculty Lead', downloadUrl: '#', description: 'Common docs', departmentName: 'All / Common', departmentId: 99 },
    ],
    assignments: [
      { id: 'a-py', title: 'Python API Task', module: 'Mod 1', description: 'Build FastAPI', points: 100, dueDate: '2026-11-20', dueRelative: 'Due soon', status: 'pending', requirements: ['Tests'], departmentName: 'Python', departmentId: 1 },
      { id: 'a-java', title: 'Java API Task', module: 'Mod 1', description: 'Build Spring', points: 100, dueDate: '2026-11-20', dueRelative: 'Due soon', status: 'pending', requirements: ['Tests'], departmentName: 'Java', departmentId: 2 },
      { id: 'a-common', title: 'Common Task', module: 'Mod 0', description: 'Git flow', points: 100, dueDate: '2026-11-20', dueRelative: 'Due soon', status: 'pending', requirements: ['Tests'], departmentName: 'All / Common', departmentId: 99 },
    ],
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
    quizzes: [
      { id: 'q-py', title: 'Python Quiz', module: 'Mod 1', questionsCount: 5, durationMinutes: 10, dueDate: '2026-11-20', passingScore: 70, status: 'available', departmentName: 'Python', departmentId: 1, questions: [], submissions: [{ studentId: 1, studentName: 'Py Student', score: 90, passed: true, submittedAt: '2026-11-10' }] },
      { id: 'q-java', title: 'Java Quiz', module: 'Mod 1', questionsCount: 5, durationMinutes: 10, dueDate: '2026-11-20', passingScore: 70, status: 'available', departmentName: 'Java', departmentId: 2, questions: [], submissions: [{ studentId: 2, studentName: 'Java Student', score: 85, passed: true, submittedAt: '2026-11-10' }] },
      { id: 'q-common', title: 'Common Quiz', module: 'Mod 0', questionsCount: 5, durationMinutes: 10, dueDate: '2026-11-20', passingScore: 70, status: 'available', departmentName: 'All / Common', departmentId: 99, questions: [], submissions: [{ studentId: 3, studentName: 'Common Student', score: 80, passed: true, submittedAt: '2026-11-10' }] },
    ],
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
      assigned_department_ids: role === 'teacher' ? [1] : undefined,
      assigned_department_names: role === 'teacher' ? ['Python'] : undefined,
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

  it('scopes learner Cohort Details, Training Schedule, Learning Materials, Assignments, and Quizzes strictly to learner department and removes Cohort Members tab', async () => {
    const fixture = await mountWithRole('learner');
    const comp = fixture.componentInstance;

    expect(comp.approvedDepartmentName()).toBe('Python');
    expect(comp.overviewSessions().map(s => s.id)).toEqual(['s-py']);
    expect(comp.filteredSessions().map(s => s.id)).toEqual(['s-py']);
    expect(comp.filteredMaterials().map(m => m.id)).toEqual(['m-py']);
    expect(comp.filteredAssignments().map(a => a.id)).toEqual(['a-py']);
    expect(comp.filteredQuizzes().map(q => q.id)).toEqual(['q-py']);
    expect(comp.filteredCurriculum().map(c => c.id)).toEqual(['ch-py']);

    // Cohort Members tab is removed from learner navigation bar and blocked on setTab
    const tabButtonsText = Array.from<HTMLElement>(
      fixture.nativeElement.querySelectorAll('.cohort-tab-bar .tab-btn')
    ).map(btn => btn.textContent || '');
    expect(tabButtonsText.some(t => t.includes('Cohort Members'))).toBe(false);

    comp.setTab('members');
    expect(comp.activeTab()).toBe('overview');
  });

  it('scopes teacher Cohort Details, Training Schedule, Curriculum/Materials, Assignments, and Quizzes strictly to assigned departments', async () => {
    const fixture = await mountWithRole('teacher');
    const comp = fixture.componentInstance;

    expect(comp.teacherAssignedDepartments().map(d => d.name)).toEqual(['Python']);
    expect(comp.overviewSessions().map(s => s.id)).toEqual(['s-py']);
    expect(comp.filteredTeacherSessions().map(s => s.id)).toEqual(['s-py']);
    expect(comp.filteredMaterials().map(m => m.id)).toEqual(['m-py']);
    expect(comp.filteredCurriculum().map(c => c.id)).toEqual(['ch-py']);
    expect(comp.filteredAssignments().map(a => a.id)).toEqual(['a-py']);
    expect(comp.filteredQuizzes().map(q => q.id)).toEqual(['q-py']);
    expect(comp.allQuizSubmissions().map(s => s.quizId)).toEqual(['q-py']);
    expect(comp.filteredBatches().map(b => b.id)).toEqual(['b-py']);
  });
});
