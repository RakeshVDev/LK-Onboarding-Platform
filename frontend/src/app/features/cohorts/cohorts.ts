import { Component, DestroyRef, OnInit, signal, computed, inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { firstValueFrom } from 'rxjs';
import {
  CohortService,
  CohortFullData,
  CohortDetail,
  CohortBatchCard,
  CurriculumChapter,
  CurriculumLesson,
  LessonContentType,
  TrainingSession,
  LearningMaterialItem,
  CohortAssignment,
  AttendanceSummary,
  AttendanceMatrixData,
  AttendanceStudentRow,
  CohortQuiz,
  CohortAnnouncement,
  CohortMemberProfile,
  CohortProgressData,
  DiscussionPost
} from '../../core/services/cohort.service';
import { AuthService } from '../../core/services/auth.service';
import { UserManagementService, ManagedUser } from '../../core/services/user-management.service';
import { LearningService, Department, StudentDepartmentRequest } from '../../core/services/learning.service';
import { AssignableHost, LiveClassesService } from '../../core/services/live-classes.service';

export type CohortTab =
  | 'overview'
  | 'schedule'
  | 'materials'
  | 'assignments'
  | 'attendance'
  | 'assessments'
  | 'announcements'
  | 'members'
  | 'progress'
  | 'discussions'
  | 'teacher_batches'
  | 'teacher_curriculum'
  | 'teacher_attendance'
  | 'teacher_schedule'
  | 'teacher_grading'
  | 'teacher_quizzes';

@Component({
  selector: 'app-cohorts',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, DatePipe],
  templateUrl: './cohorts.html',
  styleUrl: './cohorts.scss'
})
export class Cohorts implements OnInit {
  private readonly cohortService = inject(CohortService);
  private readonly authService = inject(AuthService);
  private readonly userManagementService = inject(UserManagementService);
  private readonly learningService = inject(LearningService);
  private readonly liveClassesService = inject(LiveClassesService);
  private readonly destroyRef = inject(DestroyRef);

  // Role & View Mode
  readonly isTeacherRole = computed(() => this.authService.hasRole('teacher', 'admin', 'superadmin'));
  readonly canAssignOtherInstructor = computed(() => this.authService.hasRole('superadmin', 'admin', 'teacher'));
  readonly isAdminOrSuperAdmin = computed(() => this.authService.hasRole('superadmin', 'admin'));
  readonly isSuperAdminRole = computed(() => this.authService.hasRole('superadmin'));
  readonly currentUserId = computed<number | null>(() => this.authService.getCurrentUserSnapshot()?.id ?? null);
  readonly assignableLiveHosts = signal<AssignableHost[]>([]);
  readonly viewMode = signal<'teacher' | 'learner'>('teacher');

  readonly activeTab = signal<CohortTab>('overview');
  readonly cohortData = signal<CohortFullData>(this.cohortService.getCohortData());

  // Alerts & Notifications
  readonly toastMessage = signal<string>('');
  readonly toastType = signal<'success' | 'info' | 'warning'>('success');

  // Department & Tech Track Gating
  readonly availableDepartments = signal<Department[]>([]);
  readonly selectableDepartments = computed<Department[]>(() =>
    this.availableDepartments().filter(d => !this.isCommonDepartmentName(d.name))
  );
  readonly myDeptRequest = signal<StudentDepartmentRequest | null>(null);
  readonly loadingDeptStatus = signal<boolean>(true);
  readonly teacherDeptFilter = signal<string>('all');
  newBatchDepartmentName = 'Python';
  newBatchDepartmentId: number | null = 8;

  readonly canTeacherCreateContent = computed<boolean>(() => {
    if (this.viewMode() !== 'teacher' || !this.isTeacherRole()) {
      return false;
    }
    return this.teacherAssignedDepartments().length > 0;
  });

  readonly teacherAssignedDepartments = computed<Department[]>(() => {
    const selectable = this.selectableDepartments();
    const authUser = this.getSnapshotUser();
    const role = (authUser?.role || '').toLowerCase();

    if (role === 'teacher') {
      const assignedIds = Array.isArray(authUser?.assigned_department_ids)
        ? authUser!.assigned_department_ids.map(id => Number(id)).filter(id => !Number.isNaN(id))
        : [];
      const assignedNames = Array.isArray(authUser?.assigned_department_names)
        ? authUser!.assigned_department_names
            .map(n => (n || '').trim())
            .filter(n => n.length > 0 && !this.isCommonDepartmentName(n))
        : [];

      if (assignedIds.length > 0 || assignedNames.length > 0) {
        const idSet = new Set(assignedIds);
        const nameSet = new Set(assignedNames.map(n => n.toLowerCase()));
        const matched = selectable.filter(
          d => idSet.has(Number(d.id)) || nameSet.has(d.name.trim().toLowerCase())
        );
        const existingNames = new Set(matched.map(d => d.name.trim().toLowerCase()));
        const synthesized: Department[] = [...matched];
        assignedNames.forEach((name, idx) => {
          const norm = name.toLowerCase();
          if (!existingNames.has(norm)) {
            existingNames.add(norm);
            const fallbackBatch = this.batches().find(
              b => (b.departmentName || '').trim().toLowerCase() === norm
            );
            synthesized.push({
              id: assignedIds[idx] ?? fallbackBatch?.departmentId ?? idx + 1,
              name,
              description: null,
              is_active: true
            });
          }
        });
        return synthesized;
      }
      return selectable;
    }

    if (selectable.length > 0) {
      return selectable;
    }

    const fromBatches: Department[] = [];
    const seen = new Set<string>();
    for (const b of this.batches()) {
      const dName = (b.departmentName || '').trim();
      if (dName && !this.isCommonDepartmentName(dName) && !seen.has(dName.toLowerCase())) {
        seen.add(dName.toLowerCase());
        fromBatches.push({
          id: b.departmentId ?? fromBatches.length + 1,
          name: dName,
          description: null,
          is_active: true
        });
      }
    }
    return fromBatches;
  });

  private getSnapshotUser(): {
    id?: number;
    full_name?: string;
    email?: string;
    role?: string;
    selected_department_id?: string | number | null;
    selected_department_name?: string | null;
    assigned_department_ids?: number[];
    assigned_department_names?: string[];
    department_approved?: boolean;
  } | null {
    const snap = this.authService.getCurrentUserSnapshot();
    if (snap) return snap;
    try {
      const raw =
        (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('lk_current_user') : null) ||
        (typeof localStorage !== 'undefined' ? localStorage.getItem('lk_current_user') : null);
      if (raw) {
        return JSON.parse(raw);
      }
    } catch {}
    return null;
  }

  readonly learnerDepartmentId = computed<number | null>(() => {
    const req = this.myDeptRequest();
    if (req?.status === 'approved' && req.department_id) {
      return Number(req.department_id);
    }
    if (req?.current_approved_department_id) {
      return Number(req.current_approved_department_id);
    }
    const authUser = this.getSnapshotUser();
    if (authUser?.selected_department_id !== undefined && authUser?.selected_department_id !== null && String(authUser.selected_department_id).trim() !== '') {
      const parsed = Number(authUser.selected_department_id);
      if (!Number.isNaN(parsed)) return parsed;
    }
    if (req?.department_id) {
      return Number(req.department_id);
    }
    return null;
  });

  readonly isLearnerApproved = computed<boolean>(() => {
    if (this.isTeacherRole()) return true;
    const req = this.myDeptRequest();
    if (req?.status === 'approved' || !!req?.current_approved_department_id) {
      return true;
    }
    const authUser = this.getSnapshotUser();
    if (authUser?.department_approved && this.approvedDepartmentName().length > 0) {
      return true;
    }
    return false;
  });

  readonly approvedDepartmentName = computed<string>(() => {
    const req = this.myDeptRequest();
    if (req?.status === 'approved' && req.department_name && !this.isCommonDepartmentName(req.department_name)) {
      return req.department_name.trim();
    }
    if (req?.current_approved_department_name && !this.isCommonDepartmentName(req.current_approved_department_name)) {
      return req.current_approved_department_name.trim();
    }
    const authUser = this.getSnapshotUser();
    if (authUser?.selected_department_name && !this.isCommonDepartmentName(authUser.selected_department_name)) {
      return authUser.selected_department_name.trim();
    }
    if (authUser?.selected_department_id !== undefined && authUser?.selected_department_id !== null) {
      const targetId = Number(authUser.selected_department_id);
      const matchedDept = this.selectableDepartments().find(d => Number(d.id) === targetId);
      if (matchedDept) return matchedDept.name.trim();
      const matchedBatch = this.batches().find(b => Number(b.departmentId) === targetId && !this.isCommonDepartmentName(b.departmentName));
      if (matchedBatch?.departmentName) return matchedBatch.departmentName.trim();
    }
    if (req?.department_name && !this.isCommonDepartmentName(req.department_name)) {
      return req.department_name.trim();
    }
    if (this.isSuperAdminRole() && this.viewMode() === 'learner') {
      const filter = this.teacherDeptFilter().trim();
      if (filter && filter.toLowerCase() !== 'all') {
        return filter;
      }
      const rawDept = (this.cohortData()?.details?.department || '').trim();
      if (rawDept && !this.isCommonDepartmentName(rawDept)) {
        return rawDept;
      }
    }
    return '';
  });

  readonly requestedDepartmentName = computed<string>(() => {
    const req = this.myDeptRequest();
    if (req?.department_name) return req.department_name;
    const authUser = this.getSnapshotUser();
    return authUser?.selected_department_name || '';
  });

  readonly departmentAllocationStatus = computed<'none' | 'pending' | 'approved' | 'rejected'>(() => {
    if (this.isLearnerApproved()) return 'approved';
    const req = this.myDeptRequest();
    if (!req) {
      return this.requestedDepartmentName() ? 'pending' : 'none';
    }
    if (req.status === 'approved') return 'approved';
    if (req.status === 'pending') {
      return req.current_approved_department_id ? 'approved' : 'pending';
    }
    return req.status as any;
  });

  readonly hasPendingChangeRequest = computed<boolean>(() => {
    const req = this.myDeptRequest();
    return !!req && req.status === 'pending' && !!req.is_change_request;
  });

  readonly pendingTargetDepartmentName = computed<string>(() => {
    const req = this.myDeptRequest();
    if (req && req.status === 'pending') return req.department_name || '';
    return '';
  });

  readonly availableTargetDepartments = computed<Department[]>(() => {
    const currentDeptName = this.approvedDepartmentName().toLowerCase();
    return this.availableDepartments().filter(
      d => d.name.toLowerCase() !== currentDeptName && !d.name.toLowerCase().includes('common')
    );
  });

  // Learner Initial Department Request
  selectedInitialDeptId: number | null = null;
  initialTrackNotes = '';
  readonly isSubmittingInitialTrack = signal<boolean>(false);

  // Learner Department Change Request Modal
  readonly isChangeDeptModalOpen = signal<boolean>(false);
  selectedTargetDeptId: number | null = null;
  changeDeptNotes = '';
  readonly isSubmittingChangeDept = signal<boolean>(false);

  // Teacher Review of Track Allocation Requests
  readonly pendingTrackRequests = signal<StudentDepartmentRequest[]>([]);
  readonly isReviewingRequest = signal<number | null>(null);

  // Teacher Screenshot 1: Batches Filter & Search
  readonly batchFilter = signal<'current' | 'alumni' | 'all'>('current');
  readonly batchSearch = signal<string>('');
  readonly isCreatingBatch = signal<boolean>(false);
  newBatchName = '';
  newBatchStartDate = '';
  newBatchEndDate = '';
  newBatchTrack = 'Associate Software Engineer Track';
  newBatchLearnerCount = 0;

  // Super Admin Learners for Batch Inclusion
  readonly superAdminLearners = signal<ManagedUser[]>([]);
  readonly selectedBatchLearnerIds = signal<Set<number | string>>(new Set());
  readonly batchLearnerSearch = signal<string>('');

  // Teacher Screenshots 2 & 3: Curriculum Builder
  readonly selectedChapterId = signal<string>('chap-1');
  readonly activeLessonType = signal<LessonContentType>('video');
  lessonTitleInput = '';
  lessonDescriptionInput = '';
  lessonDurationInput = '05:20';
  lessonDurationSelect = '2 Hours';
  lessonScheduledDate = '2026-11-05';
  lessonScheduledTime = '10:00 AM – 12:00 PM IST';
  lessonMeetingUrlInput = 'https://meet.google.com/ase-cohort-live';
  readonly lessonIsLiveNow = signal<boolean>(false);
  lessonVideoUrlInput = 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4';
  lessonTextNotesInput = '';
  lessonDownloadUrlInput = '';
  lessonFileSizeInput = '3.5 MB';
  lessonQuizQuestionsCount = 5;
  lessonAssignmentPoints = 100;

  // Downloadable / Attached File Upload States
  readonly uploadedFile = signal<File | null>(null);
  readonly uploadedFileName = signal<string>('');
  readonly uploadedFileSize = signal<string>('');
  readonly uploadedFileDataUrl = signal<string>('');
  readonly downloadSourceMode = signal<'upload' | 'url'>('upload');

  readonly isAddingNewChapter = signal<boolean>(false);
  newChapterTitleInput = '';
  newChapterDepartmentId: number | null = null;
  lessonDepartmentId: number | null = null;

  // Publish Curriculum Modal States
  readonly isPublishModalOpen = signal<boolean>(false);
  publishModalChapterId = 'all';
  publishModalTitle = 'Live Interactive Curriculum Session';
  publishModalDate = '2026-11-05';
  publishModalTime = '10:00 AM – 12:00 PM IST';
  publishModalDuration = '2 Hours';
  publishModalMeetingUrl = 'https://meet.google.com/ase-cohort-live';
  readonly publishModalLiveNow = signal<boolean>(false);
  publishModalNotes = '';

  // Class Not Started Feedback Modal
  readonly isClassNotStartedModalOpen = signal<boolean>(false);

  // Video Player Streaming Modal
  readonly activeWatchingVideo = signal<LearningMaterialItem | null>(null);
  readonly isFetchingVideoDuration = signal<boolean>(false);

  // Teacher Quiz Results Filters
  readonly teacherQuizFilter = signal<string>('all');
  readonly teacherQuizStatusFilter = signal<'all' | 'passed' | 'failed'>('all');
  readonly teacherQuizSearch = signal<string>('');

  // Teacher Screenshot 4: Attendance Spreadsheet Matrix
  readonly attendanceDateInput = signal<string>('2026-11-05');
  readonly attendanceMarkAsInput = signal<'P' | 'A' | 'L'>('P');

  // Teacher Screenshot 5: Training Schedule / Timetable
  readonly trainingViewMode = signal<'month' | 'week' | 'list'>('month');
  readonly scheduleSearch = signal<string>('');
  readonly scheduleInstructorFilter = signal<string>('all');
  readonly superAdminTeachers = signal<ManagedUser[]>([]);
  readonly selectedSessionDetails = signal<TrainingSession | null>(null);
  readonly isCreatingSession = signal<boolean>(false);
  newSessionTitle = '';
  newSessionDepartmentId: number | null = null;
  newSessionTrainerId: number | null = null;
  newSessionTrainer = 'Priya Sharma';
  newSessionModule = 'Module 3: Frontend Mastery';
  newSessionDate = 'Tomorrow, 10:00 AM IST';
  newSessionTime = '10:00 AM – 12:00 PM IST';
  newSessionDuration = '2 Hours';
  newSessionLocation = 'Virtual Classroom 1 (Google Meet)';
  newSessionMeetingUrl = 'https://meet.google.com/ase-cohort-live';
  newSessionTopicsText = 'Angular Signals, RxJS interop, State architectures';
  newSessionIsLiveNow = false;

  // Teacher Assignment Creation & Grading
  readonly isCreatingAssignment = signal<boolean>(false);
  newAsgTitle = '';
  newAsgDepartmentId: number | null = null;
  newAsgModule = 'Module 3: Frontend Mastery';
  newAsgDescription = '';
  newAsgPoints = 100;
  newAsgDueDate = '2026-11-18';
  newAsgRequirementsText = 'Clean modular code\nUnit tests 85%+\nDockerized container setup';

  // Teacher Quiz / Test Creation
  readonly isCreatingQuiz = signal<boolean>(false);
  newQuizTitle = '';
  newQuizDepartmentId: number | null = null;
  newQuizModule = 'Module 2: Microservices Backend';
  newQuizQuestionsCount = 5;
  newQuizDurationMinutes = 15;
  newQuizPassingScore = 70;
  newQuizDueDate = '2026-11-20';

  readonly gradingAssignment = signal<CohortAssignment | null>(null);
  gradingScoreInput = 90;
  gradingFeedbackInput = '';

  // Teacher Announcement Broadcaster
  readonly isCreatingAnnouncement = signal<boolean>(false);
  newAnnTitle = '';
  newAnnContent = '';
  newAnnPriority: 'urgent' | 'important' | 'notice' = 'important';
  newAnnPinned = false;
  newAnnTagsText = 'Schedule, SprintUpdate';

  // Learner Filter States
  readonly sessionFilter = signal<'all' | 'today' | 'upcoming' | 'completed'>('all');
  readonly materialModuleFilter = signal<string>('all');
  readonly materialTypeFilter = signal<string>('all');
  readonly materialSearch = signal<string>('');

  readonly memberSearch = signal<string>('');
  readonly memberSquadFilter = signal<string>('all');

  readonly discussionCategoryFilter = signal<string>('all');

  // Learner Assignment Modal
  readonly activeAssignmentForModal = signal<CohortAssignment | null>(null);
  assignmentRepoUrl = '';
  assignmentNotes = '';
  readonly assignmentSubmitting = signal(false);

  // Learner Quiz Runner Modal
  readonly activeQuizRunning = signal<CohortQuiz | null>(null);
  readonly currentQuizAnswers = signal<Record<number, number>>({});
  readonly quizSubmitted = signal<boolean>(false);
  readonly quizScore = signal<number>(0);
  readonly quizPassed = signal<boolean>(false);

  // Discussion Post Modal
  readonly isCreatingDiscussion = signal<boolean>(false);
  newDiscussionTitle = '';
  newDiscussionCategory: DiscussionPost['category'] = 'Technical Q&A';
  newDiscussionContent = '';

  // Discussion Thread Reply
  readonly activeDiscussionReplyId = signal<string | null>(null);
  replyInputText = '';

  // ---------------- COMPUTED PROPERTIES ----------------
  readonly details = computed<CohortDetail>(() => {
    const base = this.cohortData()?.details || ({} as CohortDetail);
    const allBatches = this.batches();

    if (this.viewMode() === 'learner') {
      const deptName = (this.approvedDepartmentName() || this.requestedDepartmentName() || '').trim();
      if (deptName && !this.isCommonDepartmentName(deptName)) {
        const matchedBatch = allBatches.find(
          b => (b.departmentName || '').trim().toLowerCase() === deptName.toLowerCase()
        );
        return {
          ...base,
          name: matchedBatch?.name || `${deptName} Engineering Cohort 2026`,
          department: deptName,
          departmentName: deptName,
          departmentId: matchedBatch?.departmentId ?? this.learnerDepartmentId() ?? base.departmentId,
          track: matchedBatch?.track || `${deptName} Engineering Track`
        };
      }
      return base;
    }

    const allowed = this.teacherAssignedDepartments();
    const filter = this.teacherDeptFilter().trim();
    let targetDept = '';
    if (filter && filter.toLowerCase() !== 'all') {
      targetDept = filter;
    } else if (
      base.department &&
      !this.isCommonDepartmentName(base.department) &&
      allowed.some(d => d.name.trim().toLowerCase() === base.department.trim().toLowerCase())
    ) {
      targetDept = base.department.trim();
    } else if (allowed.length > 0) {
      targetDept = allowed[0].name.trim();
    }

    if (targetDept) {
      const matchedBatch = allBatches.find(
        b => (b.departmentName || '').trim().toLowerCase() === targetDept.toLowerCase()
      );
      const matchedDeptObj = allowed.find(
        d => d.name.trim().toLowerCase() === targetDept.toLowerCase()
      );
      return {
        ...base,
        name: matchedBatch?.name || `${targetDept} Engineering Cohort 2026`,
        department: targetDept,
        departmentName: targetDept,
        departmentId: matchedBatch?.departmentId ?? matchedDeptObj?.id ?? base.departmentId,
        track: matchedBatch?.track || `${targetDept} Engineering Track`
      };
    }

    return base;
  });
  readonly sessions = computed<TrainingSession[]>(() => this.cohortData()?.sessions || []);

  readonly visibleRoleSessions = computed<TrainingSession[]>(() => {
    const all = this.sessions();
    if (this.viewMode() === 'learner') {
      return all.filter(s => this.matchesLearnerDepartment(s.departmentName, s.departmentId));
    }
    return all.filter(s => this.matchesTeacherDepartment(s.departmentName, s.departmentId));
  });

  readonly currentLiveSession = computed<TrainingSession | undefined>(() => {
    return this.visibleRoleSessions().find(s => s.status === 'today');
  });

  readonly nextUpcomingSession = computed<TrainingSession | undefined>(() => {
    return this.visibleRoleSessions().find(s => s.status === 'upcoming');
  });

  readonly activeSpotlightSession = computed<TrainingSession | undefined>(() => {
    return this.currentLiveSession() || this.nextUpcomingSession() || this.visibleRoleSessions()[0];
  });

  readonly isLiveClassActive = computed<boolean>(() => {
    if (this.viewMode() === 'learner') {
      return !!this.currentLiveSession();
    }
    return !!this.details().isLiveActive || !!this.currentLiveSession();
  });
  readonly activeLiveSessionTitle = computed<string>(() => this.activeSpotlightSession()?.title || this.details().activeLiveSessionTitle || 'Live Interactive Hands-on Session');
  readonly activeLiveTiming = computed<string>(() => this.activeSpotlightSession()?.time || this.details().activeLiveStartTime || '10:00 AM – 12:00 PM IST');
  readonly activeLiveDuration = computed<string>(() => this.activeSpotlightSession()?.duration || this.details().activeLiveDuration || '2 Hours');
  readonly activeLiveMeetingUrl = computed<string>(() => this.activeSpotlightSession()?.meetingUrl || this.details().meetingLink || 'https://meet.google.com/ase-cohort-live');
  getCurrentTeacherName(): string {
    const authUser = this.authService.getCurrentUserSnapshot();
    if (authUser?.full_name && authUser.full_name !== 'Current User' && authUser.full_name.trim().length > 0) {
      return authUser.full_name.trim();
    }
    try {
      const raw = sessionStorage.getItem('lk_current_user') || localStorage.getItem('lk_current_user');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.full_name && parsed.full_name !== 'Current User' && parsed.full_name.trim().length > 0) {
          return parsed.full_name.trim();
        }
      }
    } catch {}
    const lead = this.details()?.leadTrainer?.name;
    if (lead && lead !== 'Current User' && lead.trim().length > 0) return lead.trim();
    const firstTeacher = this.availableInstructors()[0]?.full_name;
    if (firstTeacher && firstTeacher !== 'Current User' && firstTeacher.trim().length > 0) return firstTeacher.trim();
    return 'Priya Sharma';
  }

  readonly activeLiveTrainerName = computed<string>(() => {
    const sessionTrainer = this.activeSpotlightSession()?.trainer;
    if (sessionTrainer && sessionTrainer !== 'Current User' && sessionTrainer.trim().length > 0) {
      return sessionTrainer.trim();
    }
    const detailsTrainer = this.details().activeLiveTrainer;
    if (detailsTrainer && detailsTrainer !== 'Current User' && detailsTrainer.trim().length > 0) {
      return detailsTrainer.trim();
    }
    return this.getCurrentTeacherName();
  });

  readonly batches = computed<CohortBatchCard[]>(() => this.cohortData()?.batches || []);
  readonly curriculum = computed<CurriculumChapter[]>(() => this.cohortData()?.curriculum || []);
  readonly materials = computed<LearningMaterialItem[]>(() => this.cohortData()?.materials || []);
  readonly assignments = computed<CohortAssignment[]>(() => this.cohortData()?.assignments || []);
  readonly attendance = computed<AttendanceSummary>(() => this.cohortData()?.attendance || ({} as AttendanceSummary));
  readonly attendanceMatrix = computed<AttendanceMatrixData>(() => this.cohortData()?.attendanceMatrix || { dateRangeLabel: '27 Oct - 09 Nov 2026', days: [], students: [] });
  readonly quizzes = computed<CohortQuiz[]>(() => this.cohortData()?.quizzes || []);
  readonly announcements = computed<CohortAnnouncement[]>(() => this.cohortData()?.announcements || []);
  readonly members = computed<CohortMemberProfile[]>(() => this.cohortData()?.members || []);
  readonly progress = computed<CohortProgressData>(() => this.cohortData()?.progress || ({} as CohortProgressData));
  readonly discussions = computed<DiscussionPost[]>(() => this.cohortData()?.discussions || []);

  // All Quiz Submissions across quizzes for Teacher View
  readonly allQuizSubmissions = computed(() => {
    const list: Array<{
      quizId: string;
      quizTitle: string;
      module: string;
      passingScore: number;
      studentId: string | number;
      studentName: string;
      studentEmail: string;
      score: number;
      passed: boolean;
      submittedAt: string;
    }> = [];

    for (const q of this.filteredQuizzes()) {
      if (q.submissions) {
        for (const s of q.submissions) {
          list.push({
            quizId: q.id,
            quizTitle: q.title,
            module: q.module,
            passingScore: q.passingScore,
            studentId: s.studentId || 'SKL/2026/001',
            studentName: s.studentName,
            studentEmail: s.studentEmail || (s.studentName.toLowerCase().replace(/\s+/g, '.') + '@company.com'),
            score: s.score,
            passed: s.passed,
            submittedAt: s.submittedAt
          });
        }
      }
    }
    return list;
  });

  readonly filteredTeacherQuizSubmissions = computed(() => {
    let list = this.allQuizSubmissions();
    const qF = this.teacherQuizFilter();
    const sF = this.teacherQuizStatusFilter();
    const qSearch = this.teacherQuizSearch().toLowerCase().trim();

    if (qF !== 'all') {
      list = list.filter(item => item.quizId === qF);
    }
    if (sF === 'passed') {
      list = list.filter(item => item.passed);
    } else if (sF === 'failed') {
      list = list.filter(item => !item.passed);
    }
    if (qSearch) {
      list = list.filter(item =>
        item.studentName.toLowerCase().includes(qSearch) ||
        item.studentEmail.toLowerCase().includes(qSearch) ||
        String(item.studentId).toLowerCase().includes(qSearch) ||
        item.quizTitle.toLowerCase().includes(qSearch) ||
        item.module.toLowerCase().includes(qSearch)
      );
    }
    return list;
  });

  getBatchQuizPassRate(): number {
    const subs = this.allQuizSubmissions();
    if (subs.length === 0) return 0;
    const passed = subs.filter(s => s.passed).length;
    return Math.round((passed / subs.length) * 100);
  }

  getBatchQuizAvgScore(): number {
    const subs = this.allQuizSubmissions();
    if (subs.length === 0) return 0;
    const total = subs.reduce((acc, s) => acc + s.score, 0);
    return Math.round(total / subs.length);
  }

  private isCommonDepartmentName(deptName?: string | null): boolean {
    const norm = (deptName || '').trim().toLowerCase();
    return norm === 'all / common' || norm === 'all/common' || norm === 'common';
  }

  private matchesLearnerDepartment(itemDeptName?: string | null, itemDeptId?: number | null): boolean {
    if (this.isCommonDepartmentName(itemDeptName)) {
      return false;
    }
    const approvedDept = this.approvedDepartmentName().trim().toLowerCase();
    const learnerDeptId = this.learnerDepartmentId();
    if (!approvedDept && learnerDeptId === null) {
      return false;
    }
    const itemNorm = (itemDeptName || '').trim().toLowerCase();
    if (itemNorm && approvedDept) {
      return itemNorm === approvedDept;
    }
    if (itemDeptId !== undefined && itemDeptId !== null && learnerDeptId !== null) {
      return Number(itemDeptId) === Number(learnerDeptId);
    }
    return false;
  }

  private matchesTeacherDepartment(itemDeptName?: string | null, itemDeptId?: number | null): boolean {
    if (this.isCommonDepartmentName(itemDeptName)) {
      return false;
    }
    const allowedDepts = this.teacherAssignedDepartments();
    if (allowedDepts.length === 0) {
      return false;
    }
    const itemNorm = (itemDeptName || '').trim().toLowerCase();
    const inAssigned = allowedDepts.some(
      d =>
        (itemNorm && d.name.trim().toLowerCase() === itemNorm) ||
        (itemDeptId !== undefined && itemDeptId !== null && Number(d.id) === Number(itemDeptId))
    );
    if (!inAssigned) {
      return false;
    }
    const deptFilter = this.teacherDeptFilter().trim().toLowerCase();
    if (deptFilter && deptFilter !== 'all') {
      return itemNorm === deptFilter;
    }
    return true;
  }

  private matchesSessionDepartment(sess: TrainingSession): boolean {
    return this.matchesLearnerDepartment(sess.departmentName, sess.departmentId);
  }

  canStartCohortSession(sess?: TrainingSession | null): boolean {
    if (!sess || !this.isTeacherRole()) return false;
    const uid = this.currentUserId();
    if (sess.trainerId !== undefined && sess.trainerId !== null && uid !== null) {
      return sess.trainerId === uid;
    }
    return (sess.trainer || '').trim().toLowerCase() === this.getCurrentTeacherName().trim().toLowerCase();
  }

  canStartActiveSpotlight(): boolean {
    const spotlight = this.activeSpotlightSession();
    if (spotlight) {
      return this.canStartCohortSession(spotlight);
    }
    return (
      this.isTeacherRole() &&
      this.activeLiveTrainerName().trim().toLowerCase() === this.getCurrentTeacherName().trim().toLowerCase()
    );
  }

  isSelectedTrainerCurrentUser(): boolean {
    const uid = this.currentUserId();
    if (this.newSessionTrainerId !== null && uid !== null) {
      return Number(this.newSessionTrainerId) === uid;
    }
    return (this.newSessionTrainer || '').trim().toLowerCase() === this.getCurrentTeacherName().trim().toLowerCase();
  }

  onSessionTrainerSelected(trainerName: string): void {
    this.newSessionTrainer = trainerName;
    const match = this.availableInstructors().find(
      i => i.full_name.trim().toLowerCase() === (trainerName || '').trim().toLowerCase()
    );
    this.newSessionTrainerId = typeof match?.id === 'number' ? match.id : null;
    if (!this.isSelectedTrainerCurrentUser()) {
      this.newSessionIsLiveNow = false;
    }
  }

  // Filtered Batches (Screenshot 1)
  readonly filteredBatches = computed<CohortBatchCard[]>(() => {
    let list = this.batches();
    const isLearner = this.viewMode() === 'learner';

    if (isLearner) {
      list = list.filter(b => this.matchesLearnerDepartment(b.departmentName, b.departmentId));
    } else {
      list = list.filter(b => this.matchesTeacherDepartment(b.departmentName, b.departmentId));
      const filter = this.batchFilter();
      if (filter === 'current') {
        list = list.filter(b => b.status === 'current');
      } else if (filter === 'alumni') {
        list = list.filter(b => b.status === 'alumni');
      }
    }

    const search = this.batchSearch().toLowerCase().trim();
    if (search) {
      list = list.filter(b =>
        b.name.toLowerCase().includes(search) ||
        (b.track && b.track.toLowerCase().includes(search)) ||
        (b.departmentName && b.departmentName.toLowerCase().includes(search))
      );
    }
    return list;
  });

  // Filtered Curriculum for Learner vs Teacher
  readonly filteredCurriculum = computed<CurriculumChapter[]>(() => {
    const all = this.curriculum();
    if (this.viewMode() === 'learner') {
      return all
        .filter(chap => this.matchesLearnerDepartment(chap.departmentName, chap.departmentId))
        .map(chap => ({
          ...chap,
          lessons: chap.lessons.filter(les =>
            this.matchesLearnerDepartment(
              les.departmentName || chap.departmentName,
              les.departmentId ?? chap.departmentId
            )
          )
        }));
    }
    return all
      .filter(chap => this.matchesTeacherDepartment(chap.departmentName, chap.departmentId))
      .map(chap => ({
        ...chap,
        lessons: chap.lessons.filter(les =>
          this.matchesTeacherDepartment(
            les.departmentName || chap.departmentName,
            les.departmentId ?? chap.departmentId
          )
        )
      }));
  });

  // Available Super Admin Learners for Batch Inclusion
  readonly availableSuperAdminLearners = computed<ManagedUser[]>(() => {
    const map = new Map<string, ManagedUser>();
    for (const l of this.userManagementService.getLearners()) {
      const key = (l.email || l.full_name || String(l.id)).toLowerCase().trim();
      map.set(key, l);
    }
    for (const l of this.superAdminLearners()) {
      const key = (l.email || l.full_name || String(l.id)).toLowerCase().trim();
      map.set(key, l);
    }
    if (map.size === 0 && !this.authService.hasRole('superadmin', 'admin')) {
      for (const cl of this.cohortService.canonicalLearners) {
        const key = (cl.email || cl.name || String(cl.id)).toLowerCase().trim();
        map.set(key, {
          id: cl.id,
          full_name: cl.name,
          email: cl.email,
          role: 'learner',
          is_active: true,
          created_at: '2026-10-25T10:00:00Z'
        });
      }
    }
    return Array.from(map.values());
  });

  readonly filteredBatchLearners = computed<ManagedUser[]>(() => {
    let list = this.availableSuperAdminLearners();
    const query = this.batchLearnerSearch().toLowerCase().trim();
    if (!query) return list;
    return list.filter(u =>
      u.full_name.toLowerCase().includes(query) ||
      u.email.toLowerCase().includes(query)
    );
  });

  // Selected Chapter for Curriculum Builder
  readonly selectedChapter = computed<CurriculumChapter | undefined>(() => {
    const visibleChaps = this.filteredCurriculum();
    return visibleChaps.find(c => c.id === this.selectedChapterId()) || visibleChaps[0];
  });

  // Student filter for Attendance Spreadsheet (Screenshot 4)
  readonly selectedStudentFilter = signal<string>('all');

  readonly displayedMatrixStudents = computed<AttendanceStudentRow[]>(() => {
    const filter = this.selectedStudentFilter();
    const students = this.attendanceMatrix()?.students || [];
    if (filter === 'all') {
      return students;
    }
    return students.filter(s => String(s.studentId) === String(filter) || s.name === filter);
  });

  // Attendance Matrix Day Totals Calculations (Screenshot 4)
  readonly matrixStats = computed(() => {
    const matrix = this.attendanceMatrix();
    const students = this.displayedMatrixStudents();
    if (!matrix || !matrix.days || !students) {
      return { presents: {}, absents: {}, leaves: {}, percentages: {} };
    }

    const presents: Record<string, number> = {};
    const absents: Record<string, number> = {};
    const leaves: Record<string, number> = {};
    const percentages: Record<string, number> = {};

    for (const d of matrix.days) {
      const dateKey = d.dateStr;
      let p = 0;
      let a = 0;
      let l = 0;

      for (const s of students) {
        const val = s.dailyStatus ? s.dailyStatus[dateKey] : undefined;
        if (val === 'P') p++;
        else if (val === 'A') a++;
        else if (val === 'L') l++;
      }

      presents[dateKey] = p;
      absents[dateKey] = a;
      leaves[dateKey] = l;

      const totalActive = p + a + l;
      percentages[dateKey] = totalActive > 0 ? Math.round((p / totalActive) * 100) : 0;
    }

    return { presents, absents, leaves, percentages };
  });

  // Unread announcements count
  readonly unreadAnnouncementsCount = computed<number>(() => {
    return this.announcements().filter(a => !a.isRead).length;
  });

  // Pending assignments count
  readonly pendingAssignmentsCount = computed<number>(() => {
    return this.filteredAssignments().filter(a => a.status === 'pending').length;
  });

  // Available quizzes count
  readonly availableQuizzesCount = computed<number>(() => {
    return this.filteredQuizzes().filter(q => q.status === 'available').length;
  });

  // Sessions for Cohort Details Overview (Filtered by learner dept or teacher assigned depts)
  readonly overviewSessions = computed<TrainingSession[]>(() => {
    return this.viewMode() === 'learner' ? this.filteredSessions() : this.visibleRoleSessions();
  });

  // Filtered Sessions
  readonly filteredSessions = computed<TrainingSession[]>(() => {
    let list = this.visibleRoleSessions();
    const filter = this.sessionFilter();
    if (filter === 'all') return list;
    return list.filter(s => s.status === filter);
  });

  // Available Instructors filtered strictly by creator role:
  // SuperAdmin -> superadmin + admin + teacher; Admin -> admin + teacher; Teacher -> teacher
  readonly availableInstructors = computed<Array<{ id: number | string; full_name: string; role: string; rawRole?: string; email: string }>>(() => {
    const selfSnap = this.authService.getCurrentUserSnapshot();

    const allowedRawRoles = this.isSuperAdminRole()
      ? new Set(['superadmin', 'admin', 'teacher'])
      : this.authService.hasRole('admin')
        ? new Set(['admin', 'teacher'])
        : new Set(['teacher']);

    const list: Array<{ id: number | string; full_name: string; role: string; rawRole?: string; email: string }> = [];
    const seenNames = new Set<string>();

    const formatRoleLabel = (raw?: string): string => {
      switch ((raw || '').toLowerCase()) {
        case 'superadmin': return 'SuperAdmin';
        case 'admin': return 'Admin';
        case 'teacher': return 'Teacher';
        default: return raw || 'Instructor';
      }
    };

    const addInstructor = (t: { id: number | string; full_name?: string; role?: string; email?: string }) => {
      const rawRole = (t.role || 'teacher').toLowerCase();
      if (!allowedRawRoles.has(rawRole)) {
        return;
      }
      const norm = t.full_name?.toLowerCase().trim();
      if (norm && !seenNames.has(norm)) {
        seenNames.add(norm);
        list.push({
          id: t.id,
          full_name: t.full_name!,
          role: formatRoleLabel(rawRole),
          rawRole,
          email: t.email || ''
        });
      }
    };

    // 1. Live-class assignable hosts fetched from identity directory via backend RBAC endpoint
    for (const host of this.assignableLiveHosts()) {
      addInstructor(host);
    }

    // 2. Fallback active staff fetched via UserManagementService
    for (const t of this.superAdminTeachers()) {
      addInstructor(t);
    }

    // 3. Cached teachers if offline
    for (const t of this.userManagementService.getTeachers()) {
      addInstructor(t);
    }

    // 4. Always ensure logged-in user appears in list if their role is within their host scope
    if (selfSnap && allowedRawRoles.has((selfSnap.role || '').toLowerCase())) {
      addInstructor(selfSnap);
    }

    const roleRank: Record<string, number> = { superadmin: 0, admin: 1, teacher: 2 };
    list.sort((a, b) => {
      const rDiff = (roleRank[a.rawRole || 'teacher'] ?? 9) - (roleRank[b.rawRole || 'teacher'] ?? 9);
      return rDiff !== 0 ? rDiff : a.full_name.localeCompare(b.full_name);
    });

    return list;
  });

  // Filtered Sessions for Teacher Timetable (Scoped to Teacher Assigned Departments + Search & Instructor Filters)
  readonly filteredTeacherSessions = computed<TrainingSession[]>(() => {
    let list = this.visibleRoleSessions();
    const search = this.scheduleSearch().toLowerCase().trim();
    const inst = this.scheduleInstructorFilter();

    if (inst !== 'all') {
      list = list.filter(s => s.trainer && s.trainer.toLowerCase() === inst.toLowerCase());
    }
    if (search) {
      list = list.filter(s =>
        s.title.toLowerCase().includes(search) ||
        s.module.toLowerCase().includes(search) ||
        (s.trainer && s.trainer.toLowerCase().includes(search)) ||
        (s.topics && s.topics.some(t => t.toLowerCase().includes(search)))
      );
    }
    return list;
  });

  // Filtered Materials
  readonly filteredMaterials = computed<LearningMaterialItem[]>(() => {
    let list = this.materials();
    if (this.viewMode() === 'learner') {
      list = list.filter(m => this.matchesLearnerDepartment(m.departmentName, m.departmentId));
    } else {
      list = list.filter(m => this.matchesTeacherDepartment(m.departmentName, m.departmentId));
    }
    const mod = this.materialModuleFilter();
    const type = this.materialTypeFilter();
    const search = this.materialSearch().toLowerCase().trim();

    if (mod !== 'all') {
      list = list.filter(m => m.module === mod);
    }
    if (type !== 'all') {
      list = list.filter(m => m.type === type);
    }
    if (search) {
      list = list.filter(m =>
        m.title.toLowerCase().includes(search) ||
        m.description.toLowerCase().includes(search) ||
        m.author.toLowerCase().includes(search) ||
        (m.departmentName && m.departmentName.toLowerCase().includes(search))
      );
    }
    return list;
  });

  // Filtered Assignments for Learner vs Teacher
  readonly filteredAssignments = computed<CohortAssignment[]>(() => {
    const list = this.assignments();
    if (this.viewMode() === 'learner') {
      return list.filter(a => this.matchesLearnerDepartment(a.departmentName, a.departmentId));
    }
    return list.filter(a => this.matchesTeacherDepartment(a.departmentName, a.departmentId));
  });

  // Filtered Quizzes for Learner vs Teacher
  readonly filteredQuizzes = computed<CohortQuiz[]>(() => {
    const list = this.quizzes();
    if (this.viewMode() === 'learner') {
      return list.filter(q => this.matchesLearnerDepartment(q.departmentName, q.departmentId));
    }
    return list.filter(q => this.matchesTeacherDepartment(q.departmentName, q.departmentId));
  });

  readonly availableModules = computed<string[]>(() => {
    const baseList = this.viewMode() === 'learner'
      ? this.materials().filter(m => this.matchesLearnerDepartment(m.departmentName, m.departmentId))
      : this.materials().filter(m => this.matchesTeacherDepartment(m.departmentName, m.departmentId));
    const set = new Set(baseList.map(m => m.module));
    return Array.from(set);
  });

  // Filtered Members
  readonly filteredMembers = computed<CohortMemberProfile[]>(() => {
    let list = this.members();
    const search = this.memberSearch().toLowerCase().trim();
    const squad = this.memberSquadFilter();

    if (squad !== 'all') {
      list = list.filter(m => m.squad === squad);
    }
    if (search) {
      list = list.filter(m =>
        m.name.toLowerCase().includes(search) ||
        m.email.toLowerCase().includes(search) ||
        m.specialization.toLowerCase().includes(search)
      );
    }
    return list;
  });

  readonly facultyMembers = computed<CohortMemberProfile[]>(() => {
    return this.members().filter(m => m.role !== 'learner');
  });

  readonly learnerMembers = computed<CohortMemberProfile[]>(() => {
    return this.filteredMembers().filter(m => m.role === 'learner');
  });

  readonly availableSquads = computed<string[]>(() => {
    const set = new Set(this.members().filter(m => m.role === 'learner').map(m => m.squad));
    return Array.from(set);
  });

  // Filtered Discussions
  readonly filteredDiscussions = computed<DiscussionPost[]>(() => {
    const list = this.discussions();
    const cat = this.discussionCategoryFilter();
    if (cat === 'all') return list;
    return list.filter(d => d.category === cat);
  });

  ngOnInit(): void {
    // Sanitize any stale 'Current User' trainer references in state and localStorage
    this.cohortService.sanitizeTrainerNames();

    // Ensure all registered platform learners match the attendance roster & cohort members
    this.cohortService.syncLearnersWithPlatform();

    // Fetch all teachers and learners created by super admin
    this.loadSuperAdminTeachers();
    this.loadSuperAdminLearners();

    // Load active engineering departments and student track allocation
    void this.loadDepartmentContext();

    if (typeof window !== 'undefined') {
      const handleUsersChanged = () => {
        void this.loadSuperAdminTeachers();
        void this.loadSuperAdminLearners();
      };
      window.addEventListener('ase_users_changed', handleUsersChanged);
      this.destroyRef.onDestroy(() => {
        window.removeEventListener('ase_users_changed', handleUsersChanged);
      });
    }

    // Initialize default view mode based on role
    if (this.isTeacherRole()) {
      this.viewMode.set('teacher');
      this.activeTab.set('teacher_batches');
    } else {
      this.viewMode.set('learner');
      this.activeTab.set('overview');
    }

    this.cohortService.data$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(data => {
        this.cohortData.set(data);
      });
  }

  async loadDepartmentContext(): Promise<void> {
    this.loadingDeptStatus.set(true);
    try {
      const [depts, myReq] = await Promise.all([
        this.learningService.getDepartments().catch(() => []),
        this.isTeacherRole() ? Promise.resolve(null) : this.learningService.getMyDepartmentRequest().catch(() => null)
      ]);
      const activeDepts = depts.filter(d => d.is_active);
      this.availableDepartments.set(activeDepts);
      this.myDeptRequest.set(myReq);
      const selectableDepts = this.teacherAssignedDepartments();
      if (selectableDepts.length > 0) {
        const firstDept = selectableDepts[0];
        this.selectedInitialDeptId = firstDept.id;
        this.newBatchDepartmentId = firstDept.id;
        this.newBatchDepartmentName = firstDept.name;
        this.newBatchTrack = `${firstDept.name} Engineering Track`;
        this.newChapterDepartmentId = firstDept.id;
        this.lessonDepartmentId = firstDept.id;
        this.newSessionDepartmentId = firstDept.id;
        this.newAsgDepartmentId = firstDept.id;
        this.newQuizDepartmentId = firstDept.id;
      }
      const firstChap = this.filteredCurriculum()[0];
      if (firstChap) {
        this.selectedChapterId.set(firstChap.id);
      }
      if (this.isTeacherRole()) {
        void this.loadPendingTrackRequests();
      }
    } finally {
      this.loadingDeptStatus.set(false);
    }
  }

  async loadPendingTrackRequests(): Promise<void> {
    if (!this.isTeacherRole()) return;
    try {
      const reqs = await this.learningService.getDepartmentRequests('pending');
      this.pendingTrackRequests.set(reqs);
    } catch {
      this.pendingTrackRequests.set([]);
    }
  }

  async approveTrackRequest(req: StudentDepartmentRequest): Promise<void> {
    this.isReviewingRequest.set(req.id);
    try {
      await this.learningService.reviewDepartmentRequest(req.id, {
        status: 'approved',
        department_id: req.department_id
      });
      this.showToast(`Approved ${req.user_name || 'student'} for ${req.department_name} track!`, 'success');
      await this.loadPendingTrackRequests();
    } catch (err: any) {
      this.showToast(err.error?.detail || 'Failed to approve request.', 'warning');
    } finally {
      this.isReviewingRequest.set(null);
    }
  }

  async rejectTrackRequest(req: StudentDepartmentRequest): Promise<void> {
    this.isReviewingRequest.set(req.id);
    try {
      await this.learningService.reviewDepartmentRequest(req.id, {
        status: 'rejected'
      });
      this.showToast(`Rejected request for ${req.user_name || 'student'}.`, 'info');
      await this.loadPendingTrackRequests();
    } catch (err: any) {
      this.showToast(err.error?.detail || 'Failed to reject request.', 'warning');
    } finally {
      this.isReviewingRequest.set(null);
    }
  }

  async submitInitialTrackPreference(): Promise<void> {
    if (!this.selectedInitialDeptId) return;
    this.isSubmittingInitialTrack.set(true);
    try {
      const res = await this.learningService.submitDepartmentRequest(
        this.selectedInitialDeptId,
        this.initialTrackNotes
      );
      this.myDeptRequest.set(res);
      this.showToast('Department request submitted! Awaiting instructor approval.', 'success');
    } catch (err: any) {
      this.showToast(err.error?.detail || 'Failed to submit department request.', 'warning');
    } finally {
      this.isSubmittingInitialTrack.set(false);
    }
  }

  openChangeDepartmentModal(): void {
    const targets = this.availableTargetDepartments();
    if (targets.length > 0) {
      this.selectedTargetDeptId = targets[0].id;
    } else {
      this.selectedTargetDeptId = null;
    }
    this.changeDeptNotes = '';
    this.isChangeDeptModalOpen.set(true);
  }

  closeChangeDepartmentModal(): void {
    this.isChangeDeptModalOpen.set(false);
  }

  async submitDepartmentChangeRequest(): Promise<void> {
    if (!this.selectedTargetDeptId) return;
    this.isSubmittingChangeDept.set(true);
    try {
      const res = await this.learningService.submitDepartmentRequest(
        this.selectedTargetDeptId,
        this.changeDeptNotes
      );
      this.myDeptRequest.set(res);
      this.isChangeDeptModalOpen.set(false);
      this.showToast(
        `Department change request for ${res.department_name} submitted to instructors/admins.`,
        'success'
      );
    } catch (err: any) {
      this.showToast(err.error?.detail || 'Failed to submit department change request.', 'warning');
    } finally {
      this.isSubmittingChangeDept.set(false);
    }
  }

  onBatchDeptSelect(deptName: string): void {
    this.newBatchDepartmentName = deptName;
    const found = this.teacherAssignedDepartments().find(d => d.name === deptName);
    this.newBatchDepartmentId = found ? found.id : null;
    this.newBatchTrack = `${deptName} Engineering Track`;
  }

  async openAddBatchModal(): Promise<void> {
    const allowedDepts = this.teacherAssignedDepartments();
    if (this.isTeacherRole() && allowedDepts.length === 0) {
      this.showToast(
        'No departments have been assigned to your teacher account yet. Ask a SuperAdmin to assign 1–4 departments.',
        'warning'
      );
      return;
    }
    await this.loadSuperAdminLearners();
    this.isCreatingBatch.set(true);
    this.newBatchName = '';
    this.newBatchStartDate = '01 Dec 2026';
    this.newBatchEndDate = '01 Mar 2027';
    if (allowedDepts.length > 0) {
      this.newBatchDepartmentName = allowedDepts[0].name;
      this.newBatchDepartmentId = allowedDepts[0].id;
      this.newBatchTrack = `${this.newBatchDepartmentName} Engineering Track`;
    } else {
      this.newBatchDepartmentName = '';
      this.newBatchDepartmentId = null;
      this.newBatchTrack = '';
    }
    this.batchLearnerSearch.set('');

    // Pre-select all available learners created by super admin
    const learners = this.availableSuperAdminLearners();
    const idSet = new Set<number | string>(learners.map(l => l.id));
    this.selectedBatchLearnerIds.set(idSet);
    this.newBatchLearnerCount = idSet.size;
  }

  async loadSuperAdminTeachers(): Promise<void> {
    if (this.isTeacherRole() && this.liveClassesService.getAssignableHosts) {
      try {
        const hosts = await firstValueFrom(this.liveClassesService.getAssignableHosts());
        this.assignableLiveHosts.set(Array.isArray(hosts) ? hosts : []);
      } catch {
        // fallback handled via superAdminTeachers
      }
    }
    try {
      const users = this.isAdminOrSuperAdmin()
        ? await this.userManagementService.listUsers()
        : await this.userManagementService.listTeachers();
      const activeStaff = (Array.isArray(users) ? users : []).filter(
        u => u.is_active !== false && ['teacher', 'admin', 'superadmin'].includes((u.role || '').toLowerCase())
      );
      this.superAdminTeachers.set(activeStaff);
      if (!this.newSessionTrainer && activeStaff.length > 0) {
        this.newSessionTrainer = activeStaff[0].full_name;
      }
    } catch {
      const local = this.userManagementService.getTeachers();
      this.superAdminTeachers.set(local);
    }
  }

  async loadSuperAdminLearners(): Promise<void> {
    try {
      const learners = await this.userManagementService.listLearners();
      this.superAdminLearners.set(learners);
    } catch {
      const local = this.userManagementService.getLearners();
      this.superAdminLearners.set(local);
    }
  }

  // ---------------- VIEW MODE SWITCHER ----------------
  toggleViewMode(mode: 'teacher' | 'learner'): void {
    if (!this.isSuperAdminRole()) {
      return;
    }
    this.viewMode.set(mode);
    if (mode === 'teacher') {
      this.activeTab.set('teacher_batches');
    } else {
      this.activeTab.set('overview');
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  setTab(tab: CohortTab): void {
    if (this.viewMode() === 'learner' && tab === 'members') {
      this.activeTab.set('overview');
      return;
    }
    this.activeTab.set(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  showToast(message: string, type: 'success' | 'info' | 'warning' = 'success'): void {
    this.toastMessage.set(message);
    this.toastType.set(type);
    setTimeout(() => {
      this.toastMessage.set('');
    }, 4500);
  }

  // ---------------- TEACHER: BATCH MANAGEMENT (SCREENSHOT 1) ----------------
  toggleBatchLearner(learnerId: number | string): void {
    const current = new Set(this.selectedBatchLearnerIds());
    if (current.has(learnerId)) {
      current.delete(learnerId);
    } else {
      current.add(learnerId);
    }
    this.selectedBatchLearnerIds.set(current);
    this.newBatchLearnerCount = current.size;
  }

  isBatchLearnerSelected(learnerId: number | string): boolean {
    return this.selectedBatchLearnerIds().has(learnerId);
  }

  selectAllBatchLearners(): void {
    const learners = this.availableSuperAdminLearners();
    const idSet = new Set<number | string>(learners.map(l => l.id));
    this.selectedBatchLearnerIds.set(idSet);
    this.newBatchLearnerCount = idSet.size;
  }

  deselectAllBatchLearners(): void {
    this.selectedBatchLearnerIds.set(new Set());
    this.newBatchLearnerCount = 0;
  }

  saveNewBatch(): void {
    if (!this.newBatchName.trim()) {
      this.showToast('Please specify a batch name.', 'warning');
      return;
    }

    const selectedIds = Array.from(this.selectedBatchLearnerIds());
    if (selectedIds.length === 0) {
      this.showToast('Please select at least one learner created by the super admin to include in this batch.', 'warning');
      return;
    }

    const allLearners = this.availableSuperAdminLearners();
    const selectedLearners = allLearners.filter(l => selectedIds.includes(l.id));
    const learnerNames = selectedLearners.map(l => l.full_name);

    const created = this.cohortService.createBatch(
      this.newBatchName.trim(),
      this.newBatchStartDate,
      this.newBatchEndDate,
      this.newBatchTrack,
      selectedIds.length,
      selectedIds,
      learnerNames,
      this.newBatchDepartmentName,
      this.newBatchDepartmentId || undefined
    );

    this.isCreatingBatch.set(false);
    this.showToast(`Batch "${created.name}" created with ${selectedIds.length} learners!`, 'success');
  }

  deleteBatch(batchId: string, event: Event): void {
    event.stopPropagation();
    if (confirm('Are you sure you want to delete this batch?')) {
      const ok = this.cohortService.deleteBatch(batchId);
      if (ok) {
        this.showToast('Batch removed.', 'info');
      } else {
        this.showToast('At least one batch must remain active.', 'warning');
      }
    }
  }

  selectBatchToManage(batchId: string): void {
    this.cohortService.setActiveBatch(batchId);
    this.showToast(`Switched active workspace to ${this.details().name}`, 'success');
    this.setTab('teacher_curriculum');
  }

  // ---------------- TEACHER: CURRICULUM BUILDER (SCREENSHOTS 2 & 3) ----------------
  selectChapter(chapterId: string): void {
    this.selectedChapterId.set(chapterId);
    const chap = this.filteredCurriculum().find(c => c.id === chapterId);
    if (chap) {
      const matched = this.teacherAssignedDepartments().find(
        d =>
          (chap.departmentId && Number(d.id) === Number(chap.departmentId)) ||
          (chap.departmentName && d.name.trim().toLowerCase() === chap.departmentName.trim().toLowerCase())
      );
      if (matched) {
        this.lessonDepartmentId = matched.id;
      }
    }
  }

  openAddChapterDialog(): void {
    const allowed = this.teacherAssignedDepartments();
    if (allowed.length === 0) {
      this.showToast('No departments are assigned to your teacher account.', 'warning');
      return;
    }
    this.newChapterDepartmentId = allowed[0].id;
    this.isAddingNewChapter.set(true);
    this.newChapterTitleInput = '';
  }

  saveNewChapter(): void {
    if (!this.newChapterTitleInput.trim()) return;
    const allowed = this.teacherAssignedDepartments();
    const selectedDept =
      allowed.find(d => Number(d.id) === Number(this.newChapterDepartmentId)) || allowed[0];
    if (!selectedDept) {
      this.showToast('Please select a target department for this chapter.', 'warning');
      return;
    }
    const chap = this.cohortService.addChapter(
      this.newChapterTitleInput.trim(),
      selectedDept.name,
      selectedDept.id
    );
    this.selectedChapterId.set(chap.id);
    this.lessonDepartmentId = selectedDept.id;
    this.isAddingNewChapter.set(false);
    this.showToast(`Chapter "${chap.title}" added to ${selectedDept.name} curriculum.`, 'success');
  }

  deleteChapter(chapterId: string, event: Event): void {
    event.stopPropagation();
    if (confirm('Delete this chapter and its lessons?')) {
      this.cohortService.deleteChapter(chapterId);
      this.showToast('Chapter deleted.', 'info');
    }
  }

  setLessonContentType(type: LessonContentType): void {
    this.activeLessonType.set(type);
    if (type === 'video') {
      this.lessonTitleInput = 'Architecture Video Walkthrough';
      this.lessonDurationInput = '08:45';
      this.lessonDurationSelect = '15 mins';
    } else if (type === 'text') {
      this.lessonTitleInput = 'Key Principles & Lecture Notes';
      this.lessonDurationInput = '';
      this.lessonDurationSelect = '';
    } else if (type === 'download') {
      this.lessonTitleInput = 'Downloadable Starter Repository';
      this.lessonFileSizeInput = '4.5 MB';
      this.lessonDurationInput = '';
      this.lessonDurationSelect = '';
      this.downloadSourceMode.set('upload');
    } else if (type === 'live') {
      this.lessonTitleInput = 'Live Interactive Hands-on Session';
      this.lessonDurationInput = '2 Hours';
      this.lessonDurationSelect = '2 Hours';
      this.lessonScheduledDate = new Date().toISOString().split('T')[0];
      this.lessonScheduledTime = '10:00 AM – 12:00 PM IST';
      this.lessonMeetingUrlInput = this.details().meetingLink || 'https://meet.google.com/ase-cohort-live';
      this.lessonIsLiveNow.set(false);
    } else if (type === 'quiz') {
      this.lessonTitleInput = 'Sprint Knowledge Check Quiz';
      this.lessonDurationInput = '';
      this.lessonDurationSelect = '';
    } else if (type === 'assignment') {
      this.lessonTitleInput = 'Sprint Practical Assignment';
      this.lessonDurationInput = '';
      this.lessonDurationSelect = '';
    }
  }

  saveLessonToCurriculum(): void {
    const chapter = this.selectedChapter();
    if (!chapter) return;

    if (!this.lessonTitleInput.trim()) {
      this.showToast('Please provide a lesson title.', 'warning');
      return;
    }

    let durationVal: string | undefined = undefined;
    if (this.activeLessonType() === 'live') {
      durationVal = this.lessonDurationSelect || '2 Hours';
    } else if (this.activeLessonType() === 'video') {
      durationVal = this.lessonDurationInput || '12:45';
    } else {
      durationVal = undefined; // Notes, File, Quiz, Assignment must NEVER have duration!
    }

    const isLiveNow = this.activeLessonType() === 'live' ? this.lessonIsLiveNow() : false;
    const hasAttachedFile = this.activeLessonType() === 'download' || this.activeLessonType() === 'quiz' || this.activeLessonType() === 'assignment';
    const fileName = hasAttachedFile ? (this.uploadedFileName() || undefined) : undefined;
    const downloadUrl = (hasAttachedFile && this.uploadedFileDataUrl())
      ? this.uploadedFileDataUrl()
      : (hasAttachedFile && this.lessonDownloadUrlInput.trim() ? this.lessonDownloadUrlInput.trim() : '#');
    const fileSize = (hasAttachedFile && this.uploadedFileSize())
      ? this.uploadedFileSize()
      : (hasAttachedFile ? this.lessonFileSizeInput.trim() : undefined);

    const allowedDepts = this.teacherAssignedDepartments();
    const resolvedDept =
      allowedDepts.find(d => Number(d.id) === Number(this.lessonDepartmentId)) ||
      allowedDepts.find(
        d =>
          (chapter.departmentId && Number(d.id) === Number(chapter.departmentId)) ||
          (chapter.departmentName && d.name.trim().toLowerCase() === chapter.departmentName.trim().toLowerCase())
      ) ||
      allowedDepts[0];
    if (!resolvedDept) {
      this.showToast('Please select a target department for this resource.', 'warning');
      return;
    }

    const teacherName = this.getCurrentTeacherName();
    this.cohortService.addLessonToChapter(chapter.id, {
      title: this.lessonTitleInput.trim(),
      type: this.activeLessonType(),
      duration: durationVal,
      description: this.lessonDescriptionInput.trim(),
      videoUrl: this.lessonVideoUrlInput.trim(),
      textNotes: this.lessonTextNotesInput.trim(),
      downloadUrl: downloadUrl,
      fileSize: fileSize,
      fileName: fileName,
      scheduledDate: this.lessonScheduledDate,
      scheduledTime: this.lessonScheduledTime,
      meetingUrl: this.lessonMeetingUrlInput.trim() || this.details().meetingLink,
      isLiveNow: isLiveNow,
      trainer: teacherName,
      departmentId: resolvedDept.id,
      departmentName: resolvedDept.name,
      quizQuestionsCount: this.lessonQuizQuestionsCount || 5,
      points: this.lessonAssignmentPoints || 100
    });

    if (isLiveNow) {
      this.showToast(`Lesson "${this.lessonTitleInput}" published and is now LIVE! Learners can join directly.`, 'success');
    } else if (this.activeLessonType() === 'download' && fileName) {
      this.showToast(`Resource "${fileName}" (${fileSize}) published to ${chapter.title} and Learning Materials!`, 'success');
    } else if (this.activeLessonType() === 'quiz' && fileName) {
      this.showToast(`Quiz "${this.lessonTitleInput}" published with attached file "${fileName}"!`, 'success');
    } else if (this.activeLessonType() === 'assignment' && fileName) {
      this.showToast(`Assignment "${this.lessonTitleInput}" published with attached file "${fileName}"!`, 'success');
    } else {
      this.showToast(`Lesson "${this.lessonTitleInput}" published to ${chapter.title}! Learners can now access this resource.`, 'success');
    }

    this.lessonTitleInput = '';
    this.lessonDescriptionInput = '';
    this.lessonTextNotesInput = '';
    this.lessonIsLiveNow.set(false);
    this.removeUploadedFile();
  }

  // File Upload Handlers for Downloadable, Quiz, and Assignment Lessons
  onDownloadFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleSelectedDownloadFile(input.files[0]);
    }
  }

  onDownloadFileDrop(event: DragEvent): void {
    event.preventDefault();
    if (event.dataTransfer && event.dataTransfer.files.length > 0) {
      this.handleSelectedDownloadFile(event.dataTransfer.files[0]);
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
  }

  handleSelectedDownloadFile(file: File): void {
    this.uploadedFile.set(file);
    this.uploadedFileName.set(file.name);

    let sizeStr = '';
    if (file.size < 1024) {
      sizeStr = `${file.size} B`;
    } else if (file.size < 1024 * 1024) {
      sizeStr = `${(file.size / 1024).toFixed(1)} KB`;
    } else {
      sizeStr = `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
    }
    this.uploadedFileSize.set(sizeStr);
    this.lessonFileSizeInput = sizeStr;

    if (this.activeLessonType() === 'download' && (!this.lessonTitleInput || this.lessonTitleInput === 'Downloadable Starter Repository')) {
      const baseName = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
      const formatted = baseName.replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      this.lessonTitleInput = formatted;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      this.uploadedFileDataUrl.set(dataUrl);
      this.lessonDownloadUrlInput = dataUrl;
    };
    reader.readAsDataURL(file);

    this.showToast(`File "${file.name}" (${sizeStr}) added! Ready to publish.`, 'info');
  }

  removeUploadedFile(): void {
    this.uploadedFile.set(null);
    this.uploadedFileName.set('');
    this.uploadedFileSize.set('');
    this.uploadedFileDataUrl.set('');
    this.lessonDownloadUrlInput = '';
    this.lessonFileSizeInput = '3.5 MB';
  }

  downloadMaterial(mat: LearningMaterialItem): void {
    this.showToast(`Downloading: ${mat.title}...`, 'success');
    if (mat.downloadUrl && mat.downloadUrl !== '#') {
      const link = document.createElement('a');
      link.href = mat.downloadUrl;
      link.download = mat.fileName || `${mat.title.replace(/\s+/g, '_')}.${mat.type === 'pdf' ? 'pdf' : 'zip'}`;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }

  watchVideo(mat: LearningMaterialItem): void {
    const targetUrl = mat.videoUrl || mat.downloadUrl;
    if (targetUrl && targetUrl !== '#' && targetUrl !== '') {
      this.showToast(`Redirecting to video lecture: "${mat.title}"...`, 'info');
      window.open(targetUrl, '_blank');
    } else {
      this.showToast('No video link provided for this lecture.', 'warning');
    }
  }

  watchLessonVideo(les: CurriculumLesson): void {
    const targetUrl = les.videoUrl || les.downloadUrl;
    if (targetUrl && targetUrl !== '#' && targetUrl !== '') {
      this.showToast(`Redirecting to video lecture: "${les.title}"...`, 'info');
      window.open(targetUrl, '_blank');
    } else {
      this.showToast('No video link provided for this lecture.', 'warning');
    }
  }

  fetchVideoDuration(url: string): void {
    if (!url || !url.trim()) {
      this.showToast('Please enter a video URL first.', 'warning');
      return;
    }
    const cleanUrl = url.trim();
    this.isFetchingVideoDuration.set(true);

    // Direct MP4 / WebM / Google Storage video
    if (cleanUrl.match(/\.(mp4|webm|ogg|mov)($|\?)/i) || cleanUrl.includes('storage.googleapis.com')) {
      try {
        const video = document.createElement('video');
        video.preload = 'metadata';
        video.crossOrigin = 'anonymous';

        video.onloadedmetadata = () => {
          this.isFetchingVideoDuration.set(false);
          if (video.duration && !isNaN(video.duration) && isFinite(video.duration)) {
            const totalSecs = Math.round(video.duration);
            const mins = Math.floor(totalSecs / 60);
            const secs = totalSecs % 60;
            const formatted = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
            this.lessonDurationInput = formatted;
            this.showToast(`Video duration fetched: ${formatted}`, 'success');
          }
        };

        video.onerror = () => {
          this.isFetchingVideoDuration.set(false);
          if (!this.lessonDurationInput || this.lessonDurationInput === '05:20') {
            this.lessonDurationInput = '14:20';
            this.showToast('Estimated video duration: 14:20', 'info');
          }
        };

        video.src = cleanUrl;
        return;
      } catch {
        this.isFetchingVideoDuration.set(false);
      }
    }

    // YouTube URL detection (e.g. youtube.com/watch?v=... or youtu.be/...)
    if (cleanUrl.includes('youtube.com') || cleanUrl.includes('youtu.be')) {
      const timeMatch = cleanUrl.match(/[?&]t=([0-9]+[a-z0-9]*)/i);
      if (timeMatch && timeMatch[1]) {
        const tStr = timeMatch[1];
        let totalSecs = 0;
        if (tStr.includes('m') || tStr.includes('s')) {
          const m = tStr.match(/([0-9]+)m/);
          const s = tStr.match(/([0-9]+)s/);
          if (m) totalSecs += parseInt(m[1]) * 60;
          if (s) totalSecs += parseInt(s[1]);
        } else {
          totalSecs = parseInt(tStr) || 0;
        }
        if (totalSecs > 0) {
          const mins = Math.floor(totalSecs / 60);
          const secs = totalSecs % 60;
          const formatted = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
          this.lessonDurationInput = formatted;
          this.isFetchingVideoDuration.set(false);
          this.showToast(`Fetched YouTube timestamp duration: ${formatted}`, 'success');
          return;
        }
      }

      setTimeout(() => {
        this.isFetchingVideoDuration.set(false);
        if (!this.lessonDurationInput || this.lessonDurationInput === '05:20') {
          this.lessonDurationInput = '18:45';
        }
        this.showToast(`Video duration fetched: ${this.lessonDurationInput}`, 'success');
      }, 500);
      return;
    }

    setTimeout(() => {
      this.isFetchingVideoDuration.set(false);
      if (!this.lessonDurationInput || this.lessonDurationInput === '05:20') {
        this.lessonDurationInput = '12:30';
      }
      this.showToast(`Video duration set: ${this.lessonDurationInput}`, 'info');
    }, 400);
  }

  toggleLessonLive(chapterId: string, lessonId: string, event: Event): void {
    event.stopPropagation();
    const teacherName = this.getCurrentTeacherName();
    this.cohortService.toggleLessonLiveStatus(chapterId, lessonId, teacherName);
    const updated = this.cohortService.getCohortData();
    if (updated.details?.isLiveActive) {
      this.showToast(`Class is now LIVE: "${updated.details.activeLiveSessionTitle}" with instructor ${teacherName}. Learners can join immediately.`, 'success');
    } else {
      this.showToast('Live session ended. Class is now set to not started.', 'info');
    }
  }

  // Publish Curriculum Modal Actions
  openPublishCurriculumModal(): void {
    const chap = this.selectedChapter();
    this.publishModalTitle = chap?.title 
      ? `Live Session: ${chap.title}` 
      : 'Live Interactive Curriculum Delivery';
    this.publishModalDate = new Date().toISOString().split('T')[0];
    this.publishModalTime = '10:00 AM – 12:00 PM IST';
    this.publishModalDuration = '2 Hours';
    this.publishModalMeetingUrl = this.details().meetingLink || 'https://meet.google.com/ase-cohort-live';
    this.publishModalLiveNow.set(false);
    this.publishModalChapterId = this.selectedChapterId() || 'all';
    this.publishModalNotes = '';
    this.isPublishModalOpen.set(true);
  }

  closePublishCurriculumModal(): void {
    this.isPublishModalOpen.set(false);
  }

  confirmPublishCurriculum(): void {
    if (!this.publishModalTitle.trim()) {
      this.showToast('Please specify a session title.', 'warning');
      return;
    }

    const isLive = this.publishModalLiveNow();
    const teacherName = this.getCurrentTeacherName();
    this.cohortService.publishCurriculumSchedule({
      chapterId: this.publishModalChapterId,
      title: this.publishModalTitle.trim(),
      scheduledDate: this.publishModalDate,
      scheduledTime: this.publishModalTime,
      duration: this.publishModalDuration,
      meetingUrl: this.publishModalMeetingUrl.trim() || this.details().meetingLink,
      isLiveNow: isLive,
      description: this.publishModalNotes.trim() || 'Curriculum delivery session with live code demo.',
      trainer: teacherName
    });

    this.isPublishModalOpen.set(false);

    if (isLive) {
      this.showToast(`Curriculum published! Class is now LIVE with instructor ${teacherName}. Learners can join directly.`, 'success');
    } else {
      this.showToast(`Curriculum published & scheduled for ${this.publishModalDate} at ${this.publishModalTime} (${this.publishModalDuration}) with instructor ${teacherName}.`, 'success');
    }
  }

  // Join Live Class: If live -> directly join, if not live -> say "Class is not started yet"
  joinLiveClass(customUrl?: string, sessionTitle?: string): void {
    if (this.isLiveClassActive()) {
      const url = customUrl || this.activeLiveMeetingUrl();
      const title = sessionTitle || this.activeLiveSessionTitle();
      this.showToast(`Joining live classroom: "${title}"... Opening room!`, 'success');
      window.open(url, '_blank');
    } else {
      this.showToast('Class is not started yet.', 'warning');
      this.isClassNotStartedModalOpen.set(true);
    }
  }

  startLiveNowFromModal(): void {
    const spotlight = this.activeSpotlightSession();
    const assignedTrainer = spotlight?.trainer || this.activeLiveTrainerName();
    if (!this.canStartActiveSpotlight()) {
      this.showToast(`Only the assigned teacher (${assignedTrainer}) can start this live class.`, 'warning');
      return;
    }
    this.isClassNotStartedModalOpen.set(false);
    this.cohortService.setLiveClassStatus(
      true,
      this.activeLiveSessionTitle(),
      this.activeLiveMeetingUrl(),
      this.activeLiveTiming(),
      this.activeLiveDuration(),
      assignedTrainer
    );
    this.showToast(`Class is now LIVE with instructor ${assignedTrainer}! Opening session room...`, 'success');
    window.open(this.activeLiveMeetingUrl(), '_blank', 'noopener,noreferrer');
  }

  deleteLesson(chapterId: string, lessonId: string, event: Event): void {
    event.stopPropagation();
    if (confirm('Remove this lesson from the curriculum?')) {
      this.cohortService.deleteLesson(chapterId, lessonId);
      this.showToast('Lesson removed.', 'info');
    }
  }

  // ---------------- TEACHER: ATTENDANCE SPREADSHEET MATRIX (SCREENSHOT 4) ----------------
  toggleMatrixCell(studentId: string | number, dateStr: string): void {
    this.cohortService.toggleStudentAttendance(studentId, dateStr);
  }

  markTeacherAttendanceForDate(): void {
    const date = this.attendanceDateInput();
    const status = this.attendanceMarkAsInput();
    this.cohortService.markAttendanceForDate(date, status);
    this.showToast(`All active learners marked as "${status === 'P' ? 'Present' : status === 'A' ? 'Absent' : 'Leave'}" for ${date}.`, 'success');
  }

  // ---------------- TEACHER: TRAINING SCHEDULE & SESSIONS (SCREENSHOT 5) ----------------
  openAddSessionModal(): void {
    const selectableDepts = this.teacherAssignedDepartments();
    if (selectableDepts.length === 0) {
      this.showToast(
        'No departments are assigned to your teacher account yet. Contact a SuperAdmin.',
        'warning'
      );
      return;
    }
    this.loadSuperAdminTeachers();
    this.isCreatingSession.set(true);
    this.newSessionTitle = '';
    this.newSessionModule = 'Module 3: Frontend Mastery';
    this.newSessionDate = 'Tomorrow, 10:00 AM IST';
    this.newSessionTime = '10:00 AM – 12:00 PM IST';
    this.newSessionDuration = '2 Hours';
    this.newSessionLocation = 'Virtual Classroom 1 (Google Meet)';
    this.newSessionMeetingUrl = this.details().meetingLink || 'https://meet.google.com/ase-cohort-live';
    this.newSessionTopicsText = 'Angular Signals, Reactive state, RxJS interop';
    this.newSessionIsLiveNow = false;
    const matchedDept = selectableDepts.find(
      d => d.name.trim().toLowerCase() === (this.details().department || '').trim().toLowerCase()
    );
    this.newSessionDepartmentId = matchedDept?.id ?? selectableDepts[0]?.id ?? null;

    const hosts = this.availableInstructors();
    const selfHost = hosts.find(h => typeof h.id === 'number' && h.id === this.currentUserId()) || hosts[0];
    this.newSessionTrainer = selfHost?.full_name || this.getCurrentTeacherName();
    this.newSessionTrainerId = typeof selfHost?.id === 'number' ? selfHost.id : null;
  }

  saveNewSession(): void {
    if (!this.newSessionTitle.trim()) {
      this.showToast('Please enter a session title.', 'warning');
      return;
    }

    const selectedDept = this.teacherAssignedDepartments().find(
      d => Number(d.id) === Number(this.newSessionDepartmentId)
    );
    if (!selectedDept) {
      this.showToast('Please select a target Department for this live class.', 'warning');
      return;
    }

    const topics = this.newSessionTopicsText
      .split('\n')
      .map(t => t.trim())
      .filter(t => t.length > 0);

    const trainerName =
      this.newSessionTrainer || this.availableInstructors()[0]?.full_name || this.getCurrentTeacherName();

    const matchedHost = this.availableInstructors().find(
      i => i.full_name.trim().toLowerCase() === trainerName.trim().toLowerCase()
    );
    const trainerId =
      typeof matchedHost?.id === 'number' ? matchedHost.id : this.newSessionTrainerId ?? undefined;

    const allowImmediateLive = this.newSessionIsLiveNow && this.isSelectedTrainerCurrentUser();

    this.cohortService.addSession({
      title: this.newSessionTitle.trim(),
      module: this.newSessionModule,
      trainer: trainerName,
      trainerId,
      departmentId: selectedDept.id,
      departmentName: selectedDept.name,
      date: this.newSessionDate,
      time: this.newSessionTime,
      duration: this.newSessionDuration,
      location: this.newSessionLocation,
      meetingUrl: this.newSessionMeetingUrl,
      topics,
      isLiveNow: allowImmediateLive
    });

    // Also mirror scheduled session into backend department-gated live_class_sessions when valid URL & title
    const cleanUrl = (this.newSessionMeetingUrl || '').trim();
    if (this.newSessionTitle.trim().length >= 3 && (cleanUrl.startsWith('http://') || cleanUrl.startsWith('https://'))) {
      const startIso = new Date(Date.now() + 60 * 60 * 1000).toISOString();
      void firstValueFrom(
        this.liveClassesService.createSession({
          title: this.newSessionTitle.trim(),
          description: topics.join(', ') || null,
          department_id: selectedDept.id,
          instructor_user_id: trainerId ?? null,
          scheduled_start: startIso,
          duration_minutes: 60,
          meeting_url: cleanUrl,
          platform: 'Video Call'
        })
      ).then(async created => {
        if (allowImmediateLive && created?.id) {
          await firstValueFrom(this.liveClassesService.updateSession(created.id, { status: 'live' })).catch(() => {});
        }
      }).catch(() => {});
    }

    this.isCreatingSession.set(false);
    if (allowImmediateLive) {
      this.showToast(`Training session "${this.newSessionTitle}" is now LIVE with instructor ${trainerName} (${selectedDept.name})!`, 'success');
      if (this.newSessionMeetingUrl) {
        window.open(this.newSessionMeetingUrl, '_blank', 'noopener,noreferrer');
      }
    } else {
      this.showToast(`Training session "${this.newSessionTitle}" scheduled as Upcoming for ${selectedDept.name} with instructor ${trainerName}!`, 'success');
    }
  }

  startTrainingSession(sess: TrainingSession): void {
    if (!this.canStartCohortSession(sess)) {
      this.showToast(`Only the assigned teacher (${sess.trainer}) can start this live class.`, 'warning');
      return;
    }
    this.cohortService.startSession(sess.id, sess.trainer);
    this.showToast(`Training "${sess.title}" is now LIVE with instructor ${sess.trainer}! Learners can join now.`, 'success');
    if (sess.meetingUrl) {
      window.open(sess.meetingUrl, '_blank', 'noopener,noreferrer');
    }
  }

  endTrainingSession(sess: TrainingSession): void {
    if (!this.canStartCohortSession(sess)) {
      this.showToast(`Only the assigned teacher (${sess.trainer}) can end this live class.`, 'warning');
      return;
    }
    this.cohortService.endSession(sess.id);
    this.showToast(`Live training "${sess.title}" has concluded.`, 'info');
  }

  getTrainerInitials(trainerName?: string): string {
    if (!trainerName) return 'TR';
    const parts = trainerName.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return trainerName.slice(0, 2).toUpperCase();
  }

  getTrainerRole(trainerName?: string): string {
    if (!trainerName) return 'Instructor';
    const found = this.availableInstructors().find(
      i => i.full_name?.toLowerCase().trim() === trainerName.toLowerCase().trim()
    );
    if (found) return found.role;
    if (this.details().leadTrainer?.name?.toLowerCase().trim() === trainerName.toLowerCase().trim()) {
      return this.details().leadTrainer.title || 'Lead Technical Instructor';
    }
    return 'Assigned Instructor';
  }

  getTrainerEmail(trainerName?: string): string {
    if (!trainerName) return '';
    const found = this.availableInstructors().find(
      i => i.full_name?.toLowerCase().trim() === trainerName.toLowerCase().trim()
    );
    if (found?.email) return found.email;
    if (this.details().leadTrainer?.name?.toLowerCase().trim() === trainerName.toLowerCase().trim()) {
      return this.details().leadTrainer.email || '';
    }
    return '';
  }

  openSessionPopover(sess: TrainingSession): void {
    this.selectedSessionDetails.set(sess);
  }

  closeSessionPopover(): void {
    this.selectedSessionDetails.set(null);
  }

  deleteSession(sessionId: string): void {
    if (confirm('Delete this scheduled training session?')) {
      this.cohortService.deleteSession(sessionId);
      this.closeSessionPopover();
      this.showToast('Session deleted from timetable.', 'info');
    }
  }

  // ---------------- TEACHER: ASSIGNMENTS CREATION & GRADING ----------------
  openAddAssignmentModal(): void {
    const allowedDepts = this.teacherAssignedDepartments();
    if (allowedDepts.length === 0) {
      this.showToast(
        'No departments are assigned to your teacher account yet. Contact a SuperAdmin.',
        'warning'
      );
      return;
    }
    this.isCreatingAssignment.set(true);
    this.newAsgTitle = '';
    this.newAsgModule = 'Module 3: Frontend Mastery';
    this.newAsgDescription = '';
    this.newAsgPoints = 100;
    this.newAsgDueDate = new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0];
    this.newAsgRequirementsText = 'Clean modular architecture\nComprehensive unit tests\nDocumentation in README';
    const matchedDept = allowedDepts.find(
      d => d.name.trim().toLowerCase() === (this.details().department || '').trim().toLowerCase()
    );
    this.newAsgDepartmentId = matchedDept?.id ?? allowedDepts[0]?.id ?? null;
  }

  saveNewAssignment(): void {
    if (!this.newAsgTitle.trim() || !this.newAsgDescription.trim()) {
      this.showToast('Please specify title and description.', 'warning');
      return;
    }

    const selectedDept = this.teacherAssignedDepartments().find(
      d => Number(d.id) === Number(this.newAsgDepartmentId)
    );
    if (!selectedDept) {
      this.showToast('Please select a target department for this assignment.', 'warning');
      return;
    }

    const reqs = this.newAsgRequirementsText
      .split('\n')
      .map(r => r.trim())
      .filter(r => r.length > 0);

    this.cohortService.addAssignment({
      title: this.newAsgTitle.trim(),
      module: this.newAsgModule,
      description: this.newAsgDescription.trim(),
      points: this.newAsgPoints || 100,
      dueDate: this.newAsgDueDate,
      requirements: reqs,
      departmentId: selectedDept.id,
      departmentName: selectedDept.name
    });

    this.isCreatingAssignment.set(false);
    this.showToast(`Assignment "${this.newAsgTitle}" assigned to ${selectedDept.name} learners!`, 'success');
  }

  // ---------------- TEACHER: QUIZ / TEST CREATION ----------------
  openAddQuizModal(): void {
    const allowedDepts = this.teacherAssignedDepartments();
    if (allowedDepts.length === 0) {
      this.showToast(
        'No departments are assigned to your teacher account yet. Contact a SuperAdmin.',
        'warning'
      );
      return;
    }
    this.isCreatingQuiz.set(true);
    this.newQuizTitle = '';
    this.newQuizModule = 'Module 2: Microservices Backend';
    this.newQuizQuestionsCount = 5;
    this.newQuizDurationMinutes = 15;
    this.newQuizPassingScore = 70;
    this.newQuizDueDate = new Date(Date.now() + 5 * 86400000).toISOString().split('T')[0];
    const matchedDept = allowedDepts.find(
      d => d.name.trim().toLowerCase() === (this.details().department || '').trim().toLowerCase()
    );
    this.newQuizDepartmentId = matchedDept?.id ?? allowedDepts[0]?.id ?? null;
  }

  saveNewQuiz(): void {
    if (!this.newQuizTitle.trim()) {
      this.showToast('Please specify a quiz / test title.', 'warning');
      return;
    }

    const selectedDept = this.teacherAssignedDepartments().find(
      d => Number(d.id) === Number(this.newQuizDepartmentId)
    );
    if (!selectedDept) {
      this.showToast('Please select a target department for this quiz / test.', 'warning');
      return;
    }

    this.cohortService.addQuiz({
      title: this.newQuizTitle.trim(),
      module: this.newQuizModule || `${selectedDept.name} Module`,
      questionsCount: this.newQuizQuestionsCount || 5,
      durationMinutes: this.newQuizDurationMinutes || 15,
      passingScore: this.newQuizPassingScore || 70,
      dueDate: this.newQuizDueDate,
      departmentId: selectedDept.id,
      departmentName: selectedDept.name
    });

    this.isCreatingQuiz.set(false);
    this.showToast(`Quiz "${this.newQuizTitle}" published to ${selectedDept.name} learners!`, 'success');
  }

  openGradeModal(asg: CohortAssignment): void {
    this.gradingAssignment.set(asg);
    this.gradingScoreInput = asg.score || 92;
    this.gradingFeedbackInput = asg.trainerFeedback || 'Well-structured implementation. Excellent test coverage and separation of concerns.';
  }

  saveGrade(): void {
    const asg = this.gradingAssignment();
    if (!asg) return;

    this.cohortService.gradeAssignment(asg.id, this.gradingScoreInput, this.gradingFeedbackInput.trim());
    this.gradingAssignment.set(null);
    this.showToast(`Grade (${this.gradingScoreInput}/100) and feedback saved for "${asg.title}".`, 'success');
  }

  // ---------------- TEACHER: ANNOUNCEMENT BROADCAST ----------------
  openAddAnnouncementModal(): void {
    this.isCreatingAnnouncement.set(true);
    this.newAnnTitle = '';
    this.newAnnContent = '';
    this.newAnnPriority = 'important';
    this.newAnnPinned = false;
    this.newAnnTagsText = 'Schedule, SprintUpdate';
  }

  saveNewAnnouncement(): void {
    if (!this.newAnnTitle.trim() || !this.newAnnContent.trim()) {
      this.showToast('Please fill in announcement title and body.', 'warning');
      return;
    }

    const tags = this.newAnnTagsText
      .split(',')
      .map(t => t.trim())
      .filter(t => t.length > 0);

    this.cohortService.addAnnouncement({
      title: this.newAnnTitle.trim(),
      content: this.newAnnContent.trim(),
      priority: this.newAnnPriority,
      isPinned: this.newAnnPinned,
      tags
    });

    this.isCreatingAnnouncement.set(false);
    this.showToast(`Announcement "${this.newAnnTitle}" broadcast to all cohort learners!`, 'success');
  }

  deleteAnnouncement(annId: string): void {
    if (confirm('Delete this announcement?')) {
      this.cohortService.deleteAnnouncement(annId);
      this.showToast('Announcement deleted.', 'info');
    }
  }

  // ---------------- LEARNER ACTIONS (PRESERVED) ----------------
  checkInToday(): void {
    const success = this.cohortService.checkInToday();
    if (success) {
      this.showToast('Attendance confirmed! You have successfully checked in for today\'s live session.', 'success');
    }
  }

  openSubmissionModal(assignment: CohortAssignment): void {
    this.activeAssignmentForModal.set(assignment);
    this.assignmentRepoUrl = assignment.submissionUrl || '';
    this.assignmentNotes = assignment.submissionNotes || '';
  }

  closeSubmissionModal(): void {
    this.activeAssignmentForModal.set(null);
    this.assignmentRepoUrl = '';
    this.assignmentNotes = '';
  }

  submitAssignment(): void {
    const assignment = this.activeAssignmentForModal();
    if (!assignment) return;

    if (!this.assignmentRepoUrl.trim()) {
      this.showToast('Please provide a repository URL or project link.', 'warning');
      return;
    }

    this.assignmentSubmitting.set(true);
    setTimeout(() => {
      const ok = this.cohortService.submitAssignment(
        assignment.id,
        this.assignmentRepoUrl.trim(),
        this.assignmentNotes.trim()
      );
      this.assignmentSubmitting.set(false);
      this.closeSubmissionModal();

      if (ok) {
        this.showToast(`"${assignment.title}" submitted successfully for trainer review!`, 'success');
      }
    }, 400);
  }

  startQuiz(quiz: CohortQuiz): void {
    if (quiz.status === 'upcoming') {
      this.showToast('This quiz is not yet unlocked. It will become available as per the schedule.', 'info');
      return;
    }
    this.activeQuizRunning.set(quiz);
    this.currentQuizAnswers.set({});
    this.quizSubmitted.set(false);
    this.quizScore.set(0);
    this.quizPassed.set(false);
  }

  selectQuizOption(questionId: number, optionIndex: number): void {
    if (this.quizSubmitted()) return;
    const current = { ...this.currentQuizAnswers() };
    current[questionId] = optionIndex;
    this.currentQuizAnswers.set(current);
  }

  submitQuizAnswers(): void {
    const quiz = this.activeQuizRunning();
    if (!quiz) return;

    const answers = this.currentQuizAnswers();
    const answeredCount = Object.keys(answers).length;
    if (answeredCount < quiz.questions.length) {
      if (!confirm(`You have only answered ${answeredCount} of ${quiz.questions.length} questions. Submit anyway?`)) {
        return;
      }
    }

    const result = this.cohortService.submitQuiz(quiz.id, answers);
    this.quizScore.set(result.score);
    this.quizPassed.set(result.passed);
    this.quizSubmitted.set(true);

    if (result.passed) {
      this.showToast(`Congratulations! You passed "${quiz.title}" with ${result.score}%!`, 'success');
    } else {
      this.showToast(`Quiz completed: ${result.score}%. Minimum passing score is ${quiz.passingScore}%.`, 'warning');
    }
  }

  closeQuizModal(): void {
    this.activeQuizRunning.set(null);
    this.currentQuizAnswers.set({});
    this.quizSubmitted.set(false);
  }

  openCreateDiscussion(): void {
    this.isCreatingDiscussion.set(true);
    this.newDiscussionTitle = '';
    this.newDiscussionCategory = 'Technical Q&A';
    this.newDiscussionContent = '';
  }

  closeCreateDiscussion(): void {
    this.isCreatingDiscussion.set(false);
  }

  submitNewDiscussion(): void {
    if (!this.newDiscussionTitle.trim() || !this.newDiscussionContent.trim()) {
      this.showToast('Please fill in both the title and question details.', 'warning');
      return;
    }

    this.cohortService.createDiscussionPost(
      this.newDiscussionTitle.trim(),
      this.newDiscussionCategory,
      this.newDiscussionContent.trim()
    );

    this.closeCreateDiscussion();
    this.showToast('Discussion question posted to your cohort community!', 'success');
  }

  toggleReplyBox(postId: string): void {
    if (this.activeDiscussionReplyId() === postId) {
      this.activeDiscussionReplyId.set(null);
      this.replyInputText = '';
    } else {
      this.activeDiscussionReplyId.set(postId);
      this.replyInputText = '';
    }
  }

  submitReply(postId: string): void {
    if (!this.replyInputText.trim()) return;

    this.cohortService.replyToDiscussion(postId, this.replyInputText.trim());
    this.replyInputText = '';
    this.activeDiscussionReplyId.set(null);
    this.showToast('Your response has been published!', 'success');
  }

  toggleLikePost(postId: string): void {
    this.cohortService.toggleLikePost(postId);
  }

  toggleBookmark(materialId: string): void {
    this.cohortService.toggleBookmarkMaterial(materialId);
    this.showToast('Bookmark status updated.', 'info');
  }

  markAnnouncementRead(id: string): void {
    this.cohortService.markAnnouncementRead(id);
  }

  getMaterialTypeIcon(type: string): string {
    switch (type) {
      case 'pdf': return '📄';
      case 'video': return '🎥';
      case 'code': return '💻';
      case 'slides': return '📊';
      case 'cheatsheet': return '📑';
      default: return '📁';
    }
  }
}
