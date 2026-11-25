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

    // Cohort Members, Quizzes, and Progress tabs are removed from learner navigation bar and blocked on setTab
    const tabButtonsText = Array.from<HTMLElement>(
      fixture.nativeElement.querySelectorAll('.cohort-tab-bar .tab-btn')
    ).map(btn => btn.textContent || '');
    expect(tabButtonsText.some(t => t.includes('Cohort Members'))).toBe(false);
    expect(tabButtonsText.some(t => t.includes('Quizzes'))).toBe(false);
    expect(tabButtonsText.some(t => t.includes('Progress'))).toBe(false);

    comp.setTab('members');
    expect(comp.activeTab()).toBe('overview');
    comp.setTab('progress');
    expect(comp.activeTab()).toBe('overview');
    comp.setTab('assessments');
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

  it('allows selecting up to 5 teachers for a batch and divides Cohort tabs by department for multi-department staff', async () => {
    const fixture = await mountWithRole('superadmin');
    const comp = fixture.componentInstance;

    // 1. Batch teacher picker allows up to 5 teachers and blocks the 6th
    for (const id of [101, 102, 103, 104, 105]) {
      comp.toggleBatchTeacher(id);
    }
    expect(comp.selectedBatchTeacherIds().size).toBe(5);
    comp.toggleBatchTeacher(106);
    expect(comp.selectedBatchTeacherIds().size).toBe(5);
    expect(comp.selectedBatchTeacherIds().has(106)).toBe(false);

    // 2. Persistent Department Workspace Bar renders across tabs and divides all tabs by department
    const deptBar = fixture.nativeElement.querySelector('.cohort-global-dept-bar');
    expect(deptBar).not.toBeNull();

    comp.selectTeacherDepartmentFilter('Python');
    fixture.detectChanges();
    expect(comp.filteredTeacherSessions().map(s => s.id)).toEqual(['s-py']);
    expect(comp.filteredMaterials().map(m => m.id)).toEqual(['m-py']);
    expect(comp.filteredCurriculum().map(c => c.id)).toEqual(['ch-py']);
    expect(comp.filteredAssignments().map(a => a.id)).toEqual(['a-py']);
    expect(comp.filteredQuizzes().map(q => q.id)).toEqual(['q-py']);
    expect(comp.filteredBatches().map(b => b.id)).toEqual(['b-py']);

    comp.selectTeacherDepartmentFilter('Java');
    fixture.detectChanges();
    expect(comp.filteredTeacherSessions().map(s => s.id)).toEqual(['s-java']);
    expect(comp.filteredMaterials().map(m => m.id)).toEqual(['m-java']);
    expect(comp.filteredCurriculum().map(c => c.id)).toEqual(['ch-java']);
    expect(comp.filteredAssignments().map(a => a.id)).toEqual(['a-java']);
    expect(comp.filteredQuizzes().map(q => q.id)).toEqual(['q-java']);
    expect(comp.filteredBatches().map(b => b.id)).toEqual(['b-java']);
  });

  it('shows all-department attendance students with individual search for superadmin/admin and dept-only students for teacher', async () => {
    const sampleMatrix = {
      dateRangeLabel: '10 Nov - 23 Nov 2026',
      days: [{ dateStr: '2026-11-23', dayLetter: 'M', dateNum: '23', isWeekend: false }],
      students: [
        { studentId: 'std-1', admissionNo: 'LRN/2026/0001', name: 'Priya Python', email: 'priya@lk.test', departmentId: 1, departmentName: 'Python', absCount: 0, lveCount: 0, dailyStatus: { '2026-11-23': 'P' as const } },
        { studentId: 'std-2', admissionNo: 'LRN/2026/0002', name: 'Jay Java', email: 'jay@lk.test', departmentId: 2, departmentName: 'Java', absCount: 0, lveCount: 0, dailyStatus: { '2026-11-23': 'P' as const } },
      ],
    };

    const saFixture = await mountWithRole('superadmin');
    const saComp = saFixture.componentInstance;
    saComp.cohortData.set({ ...saComp.cohortData(), attendanceMatrix: sampleMatrix });
    expect(saComp.scopedMatrixStudents().map(s => s.name)).toEqual(['Priya Python', 'Jay Java']);
    saComp.attendanceSearch.set('jay');
    expect(saComp.displayedMatrixStudents().map(s => s.name)).toEqual(['Jay Java']);

    TestBed.resetTestingModule();
    const tFixture = await mountWithRole('teacher');
    const tComp = tFixture.componentInstance;
    tComp.cohortData.set({ ...tComp.cohortData(), attendanceMatrix: sampleMatrix });
    expect(tComp.scopedMatrixStudents().map(s => s.name)).toEqual(['Priya Python']);
    expect(tComp.displayedMatrixStudents().map(s => s.name)).toEqual(['Priya Python']);
  });

  it('excludes live and assignment lessons from Curriculum, opens Notes View modal with Description + safe Markdown, enforces file-only Downloadables, and handles 5-minute live cooldown', async () => {
    const fixture = await mountWithRole('teacher');
    const comp = fixture.componentInstance;

    // 1. Curriculum filtering hides live/assignment/quiz lessons and keeps only video/text/download
    comp.cohortData.set({
      ...comp.cohortData(),
      curriculum: [
        {
          id: 'ch-py',
          title: 'Python Core',
          sequenceOrder: 1,
          departmentName: 'Python',
          departmentId: 1,
          lessons: [
            { id: 'l-vid', title: 'Video Walk', type: 'video', departmentName: 'Python', departmentId: 1 },
            { id: 'l-txt', title: 'REST Notes', type: 'text', description: 'API overview', textNotes: '# Heading\n**Bold** <script>alert(1)</script>', departmentName: 'Python', departmentId: 1 },
            { id: 'l-dl', title: 'Starter PDF', type: 'download', fileName: 'guide.pdf', hasFile: true, departmentName: 'Python', departmentId: 1 },
            { id: 'l-live', title: 'Hidden Live', type: 'live', departmentName: 'Python', departmentId: 1 },
            { id: 'l-asg', title: 'Hidden Assignment', type: 'assignment', departmentName: 'Python', departmentId: 1 },
          ],
        },
      ],
    });
    expect(comp.filteredCurriculum()[0].lessons.map(l => l.id)).toEqual(['l-vid', 'l-txt', 'l-dl']);

    // 2. Clicking View on Text/Notes populates Description + Lecture Notes + XSS-escaped Markdown
    comp.viewLessonNotes(comp.filteredCurriculum()[0].lessons[1]);
    const viewing = comp.activeViewingResource();
    expect(viewing).not.toBeNull();
    expect(viewing?.description).toBe('API overview');
    expect(viewing?.lectureNotes).toContain('# Heading');
    const renderedStr = String((viewing?.renderedMarkdown as any)?.changingThisBreaksApplicationSecurity || '');
    expect(renderedStr).toContain('<strong>Bold</strong>');
    expect(renderedStr).not.toContain('<script>');
    expect(renderedStr).toContain('&lt;script&gt;');

    // 3. Downloadable builder has file-upload only (no External URL / GitHub toggle)
    comp.setTab('teacher_curriculum');
    comp.setLessonContentType('download');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelectorAll('.source-tab-btn').length).toBe(0);

    // 4. Live class 5-minute cooldown helpers
    const now = Date.now();
    comp.nowTickMs.set(now);
    const coolingSession: any = {
      id: 's-cool',
      title: 'Cycle Session',
      status: 'completed',
      departmentId: 1,
      departmentName: 'Python',
      reopenAtIso: new Date(now + 125_000).toISOString(),
    };
    expect(comp.getSessionReopenRemainingSec(coolingSession)).toBe(125);
    expect(comp.formatCooldownMmSs(125)).toBe('02:05');
    expect(comp.canGoLiveAgain(coolingSession)).toBe(false);

    const readySession: any = {
      ...coolingSession,
      reopenAtIso: new Date(now - 5_000).toISOString(),
    };
    expect(comp.getSessionReopenRemainingSec(readySession)).toBe(0);
    expect(comp.canGoLiveAgain(readySession)).toBe(true);
  });

  it('places newly added materials and curriculum lessons at the top (newest-first ordering)', () => {
    const svc = new CohortService(undefined as any, undefined as any);
    const chap = svc.addChapter('Week 1 Python', 'Python', 1);

    svc.addLessonToChapter(chap.id, {
      title: 'First Material',
      type: 'text',
      textNotes: 'Oldest notes',
      departmentId: 1,
      departmentName: 'Python',
    });
    svc.addLessonToChapter(chap.id, {
      title: 'Second Material',
      type: 'video',
      videoUrl: 'https://example.com/v2.mp4',
      departmentId: 1,
      departmentName: 'Python',
    });
    svc.addLessonToChapter(chap.id, {
      title: 'Third Material (Newest)',
      type: 'download',
      fileName: 'latest.pdf',
      departmentId: 1,
      departmentName: 'Python',
    });

    const state = svc.getCohortData();
    const targetChap = state.curriculum.find(c => c.id === chap.id)!;
    expect(targetChap.lessons.map(l => l.title)).toEqual([
      'Third Material (Newest)',
      'Second Material',
      'First Material',
    ]);
    expect(state.materials.slice(0, 3).map(m => m.title)).toEqual([
      'Third Material (Newest)',
      'Second Material',
      'First Material',
    ]);
  });

  it('maps Resource Vault deliveries so PDFs show Download + Read, notes show View only, and videos show Watch Video', async () => {
    const svc = new CohortService(undefined as any, undefined as any);
    svc.syncBackendBatchesAndMaterials(
      [
        {
          id: 10,
          department_id: 1,
          department_name: 'Python',
          name: 'Python Batch A',
          status: 'active',
          teacher_ids: [2],
          teachers: [{ id: 2, full_name: 'Lead Teacher', email: 'lead@lk.test' }],
          member_ids: [10],
          learner_count: 1,
        },
      ],
      {
        10: [
          {
            id: 1,
            cohort_id: 10,
            course_id: 5,
            material_id: 101,
            title: 'FastAPI Guide',
            material_type: 'pdf',
            storage_key: 'abc123_fastapi-guide.pdf',
            source_department_name: 'Python',
            sent_by_name: 'Lead Teacher',
            sent_at: '2026-11-25T09:00:00Z',
          },
          {
            id: 2,
            cohort_id: 10,
            course_id: 5,
            material_id: 102,
            title: 'Async Notes',
            material_type: 'notes',
            storage_key: '# Async Patterns\nUse await carefully.',
            source_department_name: 'Python',
            sent_by_name: 'Lead Teacher',
            sent_at: '2026-11-25T09:05:00Z',
          },
          {
            id: 3,
            cohort_id: 10,
            course_id: 5,
            material_id: 103,
            title: 'FastAPI Video',
            material_type: 'video',
            storage_key: 'https://video.example.com/fastapi.mp4',
            source_department_name: 'Python',
            sent_by_name: 'Lead Teacher',
            sent_at: '2026-11-25T09:10:00Z',
          },
        ],
      }
    );

    const mats = svc.getCohortData().materials;
    const pdfMat = mats.find(m => m.title === 'FastAPI Guide')!;
    const notesMat = mats.find(m => m.title === 'Async Notes')!;
    const videoMat = mats.find(m => m.title === 'FastAPI Video')!;

    expect(pdfMat.isDownloadable).toBe(true);
    expect(pdfMat.hasFile).toBe(true);
    expect(pdfMat.downloadUrl).toBe('/training-api/api/v1/courses/5/materials/101/file');
    expect(pdfMat.fileName).toBe('fastapi-guide.pdf');

    expect(notesMat.isDownloadable).toBe(false);
    expect(notesMat.textNotes).toContain('# Async Patterns');

    expect(videoMat.type).toBe('video');
    expect(videoMat.isDownloadable).toBe(false);
    expect(videoMat.videoUrl).toBe('https://video.example.com/fastapi.mp4');

    // Render learner Materials tab and assert exact action buttons per resource type
    const fixture = await mountWithRole('learner');
    const comp = fixture.componentInstance;
    comp.cohortData.set({ ...comp.cohortData(), materials: [pdfMat, notesMat, videoMat] });
    comp.setTab('materials');
    fixture.detectChanges();

    const cards = Array.from<HTMLElement>(fixture.nativeElement.querySelectorAll('.material-card'));
    expect(cards.length).toBe(3);

    // PDF card -> Download + Read
    expect(cards[0].textContent).toContain('Download');
    expect(cards[0].textContent).toContain('Read');

    // Notes card -> View only (no Download)
    expect(cards[1].textContent).toContain('View');
    expect(cards[1].textContent).not.toContain('Download');

    // Video card -> Watch Video only (no Download)
    expect(cards[2].textContent).toContain('Watch Video');
    expect(cards[2].textContent).not.toContain('Download');
  });

  it('loads delivered Resource Vault materials from /cohorts/workspace directly into Curriculum & Materials newest-first', async () => {
    const fakeHttp = {
      get: vi.fn(() =>
        of({
          curriculum: [
            {
              id: '1',
              backendId: 1,
              title: 'Week 1',
              sequenceOrder: 1,
              departmentId: 1,
              departmentName: 'Python',
              lessons: [
                {
                  id: '10',
                  backendId: 10,
                  title: 'Older Lesson Notes',
                  type: 'text',
                  textNotes: 'Old notes',
                  departmentId: 1,
                  departmentName: 'Python',
                  createdAt: '2026-11-24T08:00:00Z',
                },
              ],
            },
          ],
          deliveredMaterials: [
            {
              id: 50,
              cohort_id: 7,
              course_id: 3,
              material_id: 201,
              title: 'Fresh Vault PDF',
              material_type: 'pdf',
              storage_key: 'xyz_fresh.pdf',
              department_id: 1,
              department_name: 'Python',
              source_department_name: 'All / Common',
              sent_by_name: 'Instructor A',
              sent_at: '2026-11-25T10:00:00Z',
            },
          ],
          assignments: [],
          quizzes: [],
          announcements: [],
          discussions: [],
          bookmarkedMaterialKeys: [],
        })
      ),
      post: vi.fn(() => of({})),
    };
    const fakeAuth = {
      getToken: () => 'jwt-token',
      getCurrentUserSnapshot: () => ({ id: 2, full_name: 'Teacher', email: 't@lk.test', role: 'teacher' }),
    };

    const svc = new CohortService(fakeHttp as any, fakeAuth as any);
    await svc.loadWorkspaceFromBackend(7);

    const mats = svc.getCohortData().materials;
    expect(mats.map(m => m.title)).toEqual(['Fresh Vault PDF', 'Older Lesson Notes']);
    expect(mats[0].isDownloadable).toBe(true);
    expect(mats[0].departmentName).toBe('Python');
    expect(mats[0].downloadUrl).toBe('/training-api/api/v1/courses/3/materials/201/file');
  });

  it('strictly preserves interleaved manual and Resource Vault upload sequence (newest at very top)', async () => {
    const fakeHttp = {
      get: vi.fn(() =>
        of({
          curriculum: [
            {
              id: '1',
              backendId: 1,
              title: 'Week 1',
              sequenceOrder: 1,
              departmentId: 1,
              departmentName: 'Python',
              lessons: [
                {
                  id: '10',
                  backendId: 10,
                  title: '1st - Manual Notes',
                  type: 'text',
                  departmentId: 1,
                  departmentName: 'Python',
                  createdAt: '2026-11-25T10:00:00',
                },
                {
                  id: '11',
                  backendId: 11,
                  title: '3rd - Manual Video',
                  type: 'video',
                  videoUrl: 'https://video.example.com/v3.mp4',
                  departmentId: 1,
                  departmentName: 'Python',
                  createdAt: '2026-11-25T10:02:00',
                },
              ],
            },
          ],
          deliveredMaterials: [
            {
              id: 2,
              cohort_id: 7,
              course_id: 3,
              material_id: 202,
              title: '4th - Latest Vault PDF',
              material_type: 'pdf',
              storage_key: 'latest.pdf',
              department_id: 1,
              department_name: 'Python',
              sent_at: '2026-11-25T10:03:00',
            },
            {
              id: 1,
              cohort_id: 7,
              course_id: 3,
              material_id: 201,
              title: '2nd - Earlier Vault PDF',
              material_type: 'pdf',
              storage_key: 'earlier.pdf',
              department_id: 1,
              department_name: 'Python',
              sent_at: '2026-11-25T10:01:00',
            },
          ],
          assignments: [],
          quizzes: [],
          announcements: [],
          discussions: [],
          bookmarkedMaterialKeys: [],
        })
      ),
      post: vi.fn(() => of({})),
    };
    const fakeAuth = {
      getToken: () => 'jwt-token',
      getCurrentUserSnapshot: () => ({ id: 2, full_name: 'Teacher', email: 't@lk.test', role: 'teacher' }),
    };

    const svc = new CohortService(fakeHttp as any, fakeAuth as any);
    await svc.loadWorkspaceFromBackend(7);

    expect(svc.getCohortData().materials.map(m => m.title)).toEqual([
      '4th - Latest Vault PDF',
      '3rd - Manual Video',
      '2nd - Earlier Vault PDF',
      '1st - Manual Notes',
    ]);
  });
});
