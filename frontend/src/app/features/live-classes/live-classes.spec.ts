import { describe, it, expect, beforeEach, vi } from 'vitest';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { LiveClassesPage } from './live-classes';
import { AuthService } from '../../core/services/auth.service';
import { LearningService } from '../../core/services/learning.service';
import { LiveClassListResponse, LiveClassesService } from '../../core/services/live-classes.service';

describe('LiveClassesPage (Department-Gated Live Video Classes)', () => {
  let mockListResponse: LiveClassListResponse;
  let isStaffUser = false;
  let currentRole: 'superadmin' | 'admin' | 'teacher' | 'learner' = 'learner';
  let currentUserStub: { id: number; full_name: string; email: string; role: string } | null = null;
  let assignableHostsList: Array<{ id: number; full_name: string; email: string; role: string }> = [];
  let createSessionSpy: ReturnType<typeof vi.fn>;
  let joinSessionSpy: ReturnType<typeof vi.fn>;
  let getAssignableHostsSpy: ReturnType<typeof vi.fn>;

  async function mountPage(): Promise<ComponentFixture<LiveClassesPage>> {
    TestBed.configureTestingModule({
      imports: [LiveClassesPage],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            hasRole: (...roles: string[]) => {
              const effectiveRole = currentUserStub?.role || (isStaffUser ? 'teacher' : currentRole);
              return roles.includes(effectiveRole);
            },
            getCurrentUserSnapshot: () => currentUserStub,
          },
        },
        {
          provide: LearningService,
          useValue: {
            getDepartments: vi.fn(async () => [
              { id: 1, name: 'All / Common', is_active: true },
              { id: 3, name: 'Python Engineering', is_active: true },
              { id: 4, name: 'Cloud & DevOps', is_active: true },
            ]),
          },
        },
        {
          provide: LiveClassesService,
          useValue: {
            listSessions: vi.fn(() => of(mockListResponse)),
            getAssignableHosts: getAssignableHostsSpy,
            createSession: createSessionSpy,
            joinSession: joinSessionSpy,
            updateSession: vi.fn(() => of({})),
            deleteSession: vi.fn(() => of(void 0)),
          },
        },
      ],
    });

    const fixture = TestBed.createComponent(LiveClassesPage);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(() => {
    isStaffUser = false;
    currentRole = 'learner';
    currentUserStub = null;
    assignableHostsList = [];
    getAssignableHostsSpy = vi.fn(() => of(assignableHostsList));
    createSessionSpy = vi.fn((payload: any) =>
      of({
        id: 55,
        ...payload,
        department_name: 'Python Engineering',
        instructor_user_id: 2,
        instructor_name: 'Instructor A',
        status: 'scheduled',
        created_at: new Date().toISOString(),
      })
    );
    joinSessionSpy = vi.fn(() =>
      of({
        session_id: 10,
        department_id: 3,
        meeting_url: 'https://meet.jit.si/csm-python',
        platform: 'Jitsi Meet',
        title: 'Python Async Live Workshop',
      })
    );
  });

  it('shows restricted department access gate to unapproved learners with zero sessions', async () => {
    mockListResponse = {
      sessions: [],
      approved_department_id: null,
      restricted_reason: 'Complete all onboarding assessments and obtain department approval first.',
    };

    const fixture = await mountPage();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Department Access Required');
    expect(el.textContent).toContain('Complete all onboarding assessments and obtain department approval first.');
    expect(el.querySelectorAll('article.session-card').length).toBe(0);
    expect(el.textContent).not.toContain('Schedule Live Class');
  });

  it('renders approved department live classes and joins session on click', async () => {
    mockListResponse = {
      approved_department_id: 3,
      restricted_reason: null,
      sessions: [
        {
          id: 10,
          title: 'Python Async Live Workshop',
          description: 'Deep dive into asyncio and FastAPI streaming.',
          department_id: 3,
          department_name: 'Python Engineering',
          instructor_user_id: 2,
          instructor_name: 'Dr. Rao',
          scheduled_start: new Date(Date.now() + 3600_000).toISOString(),
          duration_minutes: 60,
          meeting_url: 'https://meet.jit.si/csm-python',
          platform: 'Jitsi Meet',
          status: 'live',
          created_at: new Date().toISOString(),
        },
      ],
    };

    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
    const fixture = await mountPage();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Python Engineering');
    expect(el.textContent).toContain('Python Async Live Workshop');
    expect(el.querySelectorAll('article.session-card').length).toBe(1);

    const joinBtn = el.querySelector('button.btn-join') as HTMLButtonElement;
    joinBtn.click();
    await fixture.whenStable();

    expect(joinSessionSpy).toHaveBeenCalledWith(10);
    expect(openSpy).toHaveBeenCalledWith('https://meet.jit.si/csm-python', '_blank', 'noopener,noreferrer');
    openSpy.mockRestore();
  });

  it('requires target department selection for staff scheduler before creating live class', async () => {
    isStaffUser = true;
    mockListResponse = {
      sessions: [],
      approved_department_id: null,
      restricted_reason: null,
    };

    const fixture = await mountPage();
    const comp = fixture.componentInstance;

    // Active non-common departments should exclude "All / Common"
    expect(comp.departments().map(d => d.name)).toEqual(['Python Engineering', 'Cloud & DevOps']);

    comp.openScheduler();
    comp.formDepartmentId = null;
    comp.formTitle = 'Kafka Architecture';
    comp.formMeetingUrl = 'https://meet.jit.si/csm-kafka';
    await comp.createSession();

    expect(createSessionSpy).not.toHaveBeenCalled();
    expect(comp.errorMessage()).toContain('select a target Department');

    comp.formDepartmentId = 4;
    await comp.createSession();
    expect(createSessionSpy).toHaveBeenCalledTimes(1);
    expect(createSessionSpy.mock.calls[0][0].department_id).toBe(4);
  });

  it('shows Join Live button ONLY for live sessions and hides it on scheduled upcoming sessions', async () => {
    mockListResponse = {
      approved_department_id: 3,
      restricted_reason: null,
      sessions: [
        {
          id: 101,
          title: 'Upcoming Python Session',
          description: 'Scheduled only',
          department_id: 3,
          department_name: 'Python Engineering',
          instructor_user_id: 2,
          instructor_name: 'Priya Teacher',
          scheduled_start: new Date(Date.now() + 7200_000).toISOString(),
          duration_minutes: 60,
          meeting_url: 'https://meet.jit.si/csm-upcoming',
          platform: 'Jitsi Meet',
          status: 'scheduled',
        },
        {
          id: 102,
          title: 'Active Live Python Class',
          description: 'Currently live',
          department_id: 3,
          department_name: 'Python Engineering',
          instructor_user_id: 2,
          instructor_name: 'Priya Teacher',
          scheduled_start: new Date().toISOString(),
          duration_minutes: 60,
          meeting_url: 'https://meet.jit.si/csm-live-now',
          platform: 'Jitsi Meet',
          status: 'live',
        },
      ],
    };

    const fixture = await mountPage();
    const cards = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll('article.session-card')
    );
    expect(cards.length).toBe(2);

    const scheduledCard = cards[0];
    const liveCard = cards[1];

    expect(scheduledCard.textContent).toContain('Upcoming Python Session');
    expect(scheduledCard.querySelector('.btn-join')).toBeNull();
    expect(scheduledCard.textContent).not.toContain('Join Live Session');
    expect(scheduledCard.textContent).toContain('Scheduled');

    const joinBtn = liveCard.querySelector('.btn-join') as HTMLButtonElement | null;
    expect(joinBtn).not.toBeNull();
    expect(joinBtn?.textContent).toContain('Join Live Session');
  });

  it('enforces role-filtered host dropdown (Admin: Admin+Teacher, Teacher: all Teachers) and Go Live only for assigned host', async () => {
    currentUserStub = {
      id: 10,
      full_name: 'Admin Patel',
      email: 'admin@csm.local',
      role: 'admin',
    };
    assignableHostsList = [
      { id: 2, full_name: 'Teacher Verma', email: 't@csm.local', role: 'teacher' },
      { id: 3, full_name: 'Teacher Rao', email: 'trao@csm.local', role: 'teacher' },
      { id: 10, full_name: 'Admin Patel', email: 'admin@csm.local', role: 'admin' },
      { id: 1, full_name: 'Root SuperAdmin', email: 'sa@csm.local', role: 'superadmin' },
    ];
    mockListResponse = {
      approved_department_id: null,
      restricted_reason: null,
      sessions: [
        {
          id: 201,
          title: 'Assigned to Teacher Verma',
          department_id: 3,
          department_name: 'Python Engineering',
          instructor_user_id: 2,
          instructor_name: 'Teacher Verma',
          scheduled_start: new Date(Date.now() + 3600_000).toISOString(),
          duration_minutes: 60,
          meeting_url: 'https://meet.jit.si/verma',
          platform: 'Jitsi Meet',
          status: 'scheduled',
        },
        {
          id: 202,
          title: 'Assigned to Admin Patel',
          department_id: 3,
          department_name: 'Python Engineering',
          instructor_user_id: 10,
          instructor_name: 'Admin Patel',
          scheduled_start: new Date(Date.now() + 7200_000).toISOString(),
          duration_minutes: 60,
          meeting_url: 'https://meet.jit.si/admin-patel',
          platform: 'Jitsi Meet',
          status: 'scheduled',
        },
      ],
    };

    const adminFixture = await mountPage();
    const comp = adminFixture.componentInstance;

    // Admin sees Teachers and Admins, NOT SuperAdmin
    expect(comp.canAssignOtherHost()).toBe(true);
    expect(comp.assignableHosts().map(h => h.role)).toEqual(['teacher', 'teacher', 'admin']);
    expect(comp.assignableHosts().some(h => h.role === 'superadmin')).toBe(false);

    // Go Live button MUST be hidden on Teacher Verma's session and visible ONLY on Admin Patel's session
    const cards = Array.from(
      (adminFixture.nativeElement as HTMLElement).querySelectorAll('article.session-card')
    );
    expect(cards[0].textContent).not.toContain('Go Live');
    expect(cards[0].textContent).toContain('Only Teacher Verma can start');
    expect(cards[1].textContent).toContain('Go Live');

    // Admin assigns Teacher Verma when creating a new class
    comp.openScheduler();
    comp.formDepartmentId = 3;
    comp.formInstructorUserId = 2;
    comp.formTitle = 'Backend Async Streams';
    comp.formMeetingUrl = 'https://meet.jit.si/async-streams';
    await comp.createSession();
    expect(createSessionSpy).toHaveBeenCalledTimes(1);
    expect(createSessionSpy.mock.calls[0][0].instructor_user_id).toBe(2);

    // Switch to Teacher role: host dropdown shows ALL active teachers ONLY (no Admins/SuperAdmins)
    TestBed.resetTestingModule();
    currentUserStub = {
      id: 2,
      full_name: 'Teacher Verma',
      email: 't@csm.local',
      role: 'teacher',
    };
    const teacherFixture = await mountPage();
    const teacherComp = teacherFixture.componentInstance;
    expect(teacherComp.canAssignOtherHost()).toBe(true);
    expect(teacherComp.assignableHosts().map(h => h.id)).toEqual([2, 3]);
    expect(teacherComp.assignableHosts().every(h => h.role === 'teacher')).toBe(true);

    teacherComp.openScheduler();
    teacherFixture.detectChanges();
    const teacherSelect = (teacherFixture.nativeElement as HTMLElement).querySelector(
      '#lcInstructor'
    ) as HTMLSelectElement | null;
    expect(teacherSelect?.tagName.toLowerCase()).toBe('select');
    const optionTexts = Array.from(teacherSelect?.options ?? []).map(o => o.textContent?.trim() || '');
    expect(optionTexts).toEqual(['Teacher Verma (Teacher)', 'Teacher Rao (Teacher)']);

    teacherComp.formDepartmentId = 3;
    teacherComp.formInstructorUserId = 3;
    teacherComp.formTitle = 'Peer Teacher Python Lab';
    teacherComp.formMeetingUrl = 'https://meet.jit.si/peer-teacher';
    await teacherComp.createSession();
    expect(createSessionSpy.mock.calls[1][0].instructor_user_id).toBe(3);
  });

  it('allows SuperAdmin to see and select SuperAdmin, Admin, and Teacher hosts', async () => {
    currentUserStub = {
      id: 1,
      full_name: 'Root SuperAdmin',
      email: 'sa@csm.local',
      role: 'superadmin',
    };
    assignableHostsList = [
      { id: 2, full_name: 'Teacher Verma', email: 't@csm.local', role: 'teacher' },
      { id: 10, full_name: 'Admin Patel', email: 'admin@csm.local', role: 'admin' },
      { id: 99, full_name: 'Second SuperAdmin', email: 'sa2@csm.local', role: 'superadmin' },
    ];
    mockListResponse = {
      approved_department_id: null,
      restricted_reason: null,
      sessions: [],
    };

    const fixture = await mountPage();
    const comp = fixture.componentInstance;
    expect(comp.assignableHosts().map(h => h.id)).toEqual([2, 10, 99]);

    comp.openScheduler();
    comp.formDepartmentId = 4;
    comp.formInstructorUserId = 99;
    comp.formTitle = 'Enterprise Security Townhall';
    comp.formMeetingUrl = 'https://meet.jit.si/sa-townhall';
    await comp.createSession();
    expect(createSessionSpy.mock.calls[0][0].instructor_user_id).toBe(99);
  });
});

