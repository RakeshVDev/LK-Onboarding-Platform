import { Injectable, Optional } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { BehaviorSubject, Observable, firstValueFrom } from 'rxjs';
import { AuthService } from './auth.service';

export interface LeadTrainer {
  name: string;
  title: string;
  email: string;
  avatar: string;
  officeHours: string;
  bio: string;
}

export interface Mentor {
  name: string;
  title: string;
  email: string;
  avatar: string;
}

export interface CohortDetail {
  id: string;
  name: string;
  code: string;
  department: string;
  departmentId?: number;
  departmentName?: string;
  track: string;
  status: 'active' | 'upcoming' | 'completed';
  startDate: string;
  endDate: string;
  durationWeeks: number;
  currentWeek: number;
  currentModule: string;
  leadTrainer: LeadTrainer;
  mentors: Mentor[];
  description: string;
  objectives: string[];
  meetingLink: string;
  slackChannel: string;
  githubOrg: string;
  isLiveActive?: boolean;
  activeLiveSessionTitle?: string;
  activeLiveStartTime?: string;
  activeLiveDuration?: string;
  activeLiveTrainer?: string;
}

export interface CohortBatchCard {
  id: string;
  backendCohortId?: number;
  name: string;
  learnerCount: number;
  startDate: string;
  endDate: string;
  status: 'current' | 'alumni';
  description?: string;
  track?: string;
  departmentId?: number;
  departmentName?: string;
  learnerIds?: Array<number | string>;
  learnerNames?: string[];
  teacherIds?: number[];
  teacherNames?: string[];
}

export type LessonContentType = 'video' | 'text' | 'download' | 'quiz' | 'live' | 'assignment';

export interface CurriculumLesson {
  id: string;
  backendId?: number;
  title: string;
  type: LessonContentType;
  duration?: string; // e.g. "05:21", "2 Hours"
  description?: string;
  videoUrl?: string;
  textNotes?: string;
  downloadUrl?: string;
  fileSize?: string;
  fileName?: string;
  hasFile?: boolean;
  quizQuestionsCount?: number;
  isPublished?: boolean;
  scheduledDate?: string;
  scheduledTime?: string;
  meetingUrl?: string;
  isLiveNow?: boolean;
  trainer?: string;
  departmentName?: string;
  departmentId?: number;
  createdAt?: string;
}

export interface CurriculumChapter {
  id: string;
  title: string;
  sequenceOrder: number;
  isExpanded?: boolean;
  departmentName?: string;
  departmentId?: number;
  lessons: CurriculumLesson[];
}

export interface TrainingSession {
  id: string;
  backendLiveId?: number;
  liveRawStatus?: 'scheduled' | 'live' | 'completed' | 'cancelled';
  platform?: string;
  scheduledStartIso?: string;
  endedAtIso?: string | null;
  reopenAtIso?: string | null;
  title: string;
  module: string;
  trainer: string;
  trainerId?: number;
  date: string;
  time: string;
  duration: string;
  status: 'today' | 'upcoming' | 'completed';
  location: string;
  meetingUrl: string;
  recordingUrl?: string;
  slidesUrl?: string;
  topics: string[];
  isAttended?: boolean;
  departmentName?: string;
  departmentId?: number;
}

export interface LearningMaterialItem {
  id: string;
  backendCohortId?: number;
  backendCourseId?: number;
  backendMaterialId?: number;
  backendDeliveryId?: number;
  backendLessonId?: number;
  batchId?: string;
  title: string;
  module: string;
  type: 'pdf' | 'video' | 'code' | 'slides' | 'cheatsheet';
  size: string;
  uploadedAt: string;
  author: string;
  downloadUrl: string;
  videoUrl?: string;
  fileName?: string;
  hasFile?: boolean;
  isDownloadable?: boolean;
  textNotes?: string;
  description: string;
  isBookmarked?: boolean;
  departmentName?: string;
  departmentId?: number;
  createdAtMs?: number;
}

export interface CohortAssignment {
  id: string;
  backendId?: number;
  title: string;
  module: string;
  description: string;
  points: number;
  dueDate: string;
  dueRelative: string;
  status: 'pending' | 'submitted' | 'graded';
  attachmentName?: string;
  attachmentUrl?: string;
  attachmentSize?: string;
  hasAttachmentFile?: boolean;
  submissionId?: number;
  submissionDate?: string;
  submissionUrl?: string;
  submissionFileName?: string;
  hasSubmissionFile?: boolean;
  submissionNotes?: string;
  score?: number;
  trainerFeedback?: string;
  requirements: string[];
  departmentName?: string;
  departmentId?: number;
}

export interface AttendanceRecordItem {
  sessionId: string;
  sessionTitle: string;
  date: string;
  status: 'present' | 'absent' | 'excused' | 'late';
  recordedAt: string;
  recordedBy: string;
}

export interface AttendanceSummary {
  percentage: number;
  totalSessions: number;
  attended: number;
  missed: number;
  excused: number;
  late: number;
  minimumRequired: number;
  checkedInToday: boolean;
  history: AttendanceRecordItem[];
}

export interface AttendanceStudentRow {
  studentId: string | number;
  backendUserId?: number;
  admissionNo: string;
  name: string;
  email?: string;
  departmentId?: number | null;
  departmentName?: string | null;
  absCount: number;
  lveCount: number;
  dailyStatus: Record<string, 'P' | 'A' | 'L' | 'H'>;
}

export interface AttendanceDayCol {
  dateStr: string;
  dayLetter: string;
  dateNum: string;
  isWeekend?: boolean;
}

export interface AttendanceMatrixData {
  dateRangeLabel: string;
  days: AttendanceDayCol[];
  students: AttendanceStudentRow[];
}

export interface QuizQuestion {
  id: number;
  text: string;
  options: string[];
  correctIndex: number;
  explanation: string;
}

export interface CohortQuizSubmission {
  studentId: string | number;
  studentName: string;
  studentEmail?: string;
  score: number;
  passed: boolean;
  submittedAt: string;
}

export interface CohortQuiz {
  id: string;
  title: string;
  module: string;
  questionsCount: number;
  durationMinutes: number;
  dueDate: string;
  passingScore: number;
  status: 'available' | 'completed' | 'upcoming';
  attachmentName?: string;
  attachmentUrl?: string;
  attachmentSize?: string;
  score?: number;
  passed?: boolean;
  completedAt?: string;
  submissions?: CohortQuizSubmission[];
  questions: QuizQuestion[];
  departmentName?: string;
  departmentId?: number;
}

export interface CohortAnnouncement {
  id: string;
  title: string;
  author: string;
  authorRole: string;
  authorAvatar: string;
  date: string;
  priority: 'urgent' | 'important' | 'notice';
  isPinned: boolean;
  isRead: boolean;
  content: string;
  tags: string[];
}

export interface CohortMemberProfile {
  id: string | number;
  name: string;
  email: string;
  role: 'learner' | 'lead_trainer' | 'assistant_trainer' | 'mentor';
  specialization: string;
  squad: string;
  avatar: string;
  status: 'online' | 'in_session' | 'offline';
  progressPercentage: number;
}

export interface MilestoneItem {
  week: string;
  title: string;
  description: string;
  status: 'completed' | 'current' | 'upcoming';
  completedDate?: string;
}

export interface EarnedBadge {
  id: string;
  title: string;
  icon: string;
  description: string;
  earnedDate: string;
}

export interface CohortProgressData {
  overallPercentage: number;
  modulesCompleted: number;
  totalModules: number;
  assignmentsSubmitted: number;
  totalAssignments: number;
  quizzesPassed: number;
  totalQuizzes: number;
  attendanceRate: number;
  milestones: MilestoneItem[];
  earnedBadges: EarnedBadge[];
}

export interface DiscussionReply {
  id: string;
  author: string;
  authorRole: string;
  authorAvatar: string;
  createdAt: string;
  content: string;
  isTrainerReply?: boolean;
}

export interface DiscussionPost {
  id: string;
  title: string;
  category: 'Technical Q&A' | 'Assignments' | 'General' | 'Resources' | 'Project Squads';
  author: string;
  authorRole: string;
  authorAvatar: string;
  createdAt: string;
  content: string;
  likes: number;
  hasLiked?: boolean;
  isResolved?: boolean;
  replies: DiscussionReply[];
}

export interface CohortFullData {
  details: CohortDetail;
  batches: CohortBatchCard[];
  activeBatchId: string;
  curriculum: CurriculumChapter[];
  sessions: TrainingSession[];
  materials: LearningMaterialItem[];
  assignments: CohortAssignment[];
  attendance: AttendanceSummary;
  attendanceMatrix: AttendanceMatrixData;
  quizzes: CohortQuiz[];
  announcements: CohortAnnouncement[];
  members: CohortMemberProfile[];
  progress: CohortProgressData;
  discussions: DiscussionPost[];
}

@Injectable({
  providedIn: 'root'
})
export class CohortService {
  private readonly apiUrl = '/training-api/api/v1/cohorts';
  private readonly workspaceApiUrl = '/training-api/api/v1/cohorts/workspace';
  private readonly idAliasMap = new Map<string, number>();
  private workspaceQueue: Promise<void> = Promise.resolve();

  private dataSubject!: BehaviorSubject<CohortFullData>;
  readonly data$!: Observable<CohortFullData>;

  constructor(
    private readonly http: HttpClient,
    @Optional() private readonly authService?: AuthService
  ) {
    let initial: CohortFullData;
    try {
      initial = this.getInitialData();
    } catch (e) {
      console.error('Failed to get initial cohort data, falling back to defaults:', e);
      initial = this.getDefaultCohortData();
    }
    this.dataSubject = new BehaviorSubject<CohortFullData>(initial);
    this.data$ = this.dataSubject.asObservable();

    this.sanitizeTrainerNames();

    if (typeof window !== 'undefined') {
      window.addEventListener('ase_users_changed', () => this.syncLearnersWithPlatform());
      window.addEventListener('storage', () => this.syncLearnersWithPlatform());
    }
  }

  private hasLiveBackend(): boolean {
    const token =
      this.authService?.getToken?.() ??
      (typeof sessionStorage !== 'undefined'
        ? sessionStorage.getItem('lk_access_token')
        : null);
    return (
      !!token &&
      !!this.http &&
      typeof this.http.get === 'function' &&
      typeof this.http.post === 'function'
    );
  }

  private getActiveBackendCohortId(): number | null {
    const current = this.getCohortData();
    const active = current.batches.find(b => b.id === current.activeBatchId);
    return active?.backendCohortId ?? null;
  }

  private resolveNumericId(rawId: string | number): number | null {
    if (typeof rawId === 'number' && Number.isFinite(rawId)) return rawId;
    const str = String(rawId);
    if (this.idAliasMap.has(str)) return this.idAliasMap.get(str)!;
    const stripped = str.replace(/^std-/, '');
    const parsed = Number(stripped);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
  }

  private enqueueWorkspaceOp(fn: () => Promise<void>): void {
    if (!this.hasLiveBackend()) return;
    this.workspaceQueue = this.workspaceQueue
      .then(fn)
      .catch(err => console.warn('Cohort workspace sync failed:', err));
  }

  private parseTimestampMs(raw?: string | null): number {
    if (!raw || raw === 'Just now') return 0;
    const normalized = raw.trim().replace(' ', 'T');
    const parsed = Date.parse(normalized);
    return Number.isNaN(parsed) ? 0 : parsed;
  }

  private mapDeliveredVaultItem(
    d: {
      id?: number;
      cohort_id: number;
      course_id: number;
      material_id: number;
      title: string;
      material_type: string;
      storage_key: string;
      department_id?: number | null;
      department_name?: string | null;
      source_department_name?: string | null;
      sent_by_name?: string | null;
      sent_at?: string | null;
    },
    fallbackDeptId?: number,
    fallbackDeptName?: string,
    bookmarkedSet?: Set<string>
  ): LearningMaterialItem {
    const rawType = (d.material_type || '').toLowerCase();
    const isVaultFile =
      rawType === 'pdf' ||
      (rawType === 'doc' && Boolean(d.storage_key) && !/^https?:\/\//i.test(d.storage_key));
    const isVideo = rawType === 'video';
    const isNotes = rawType === 'notes';
    const downloadUrl = isVaultFile
      ? `/training-api/api/v1/courses/${d.course_id}/materials/${d.material_id}/file`
      : isNotes
        ? ''
        : d.storage_key;
    let extractedFileName: string | undefined = undefined;
    if (isVaultFile) {
      const base = (d.storage_key || '').split(/[\\/]/).pop() || '';
      const clean = base.includes('_') ? base.split('_').slice(1).join('_') : base;
      extractedFileName =
        clean || (rawType === 'pdf' && !d.title.toLowerCase().endsWith('.pdf') ? `${d.title}.pdf` : d.title);
    }
    const matId = `deliv-${d.cohort_id}-${d.material_id}`;
    const deptId = d.department_id ?? fallbackDeptId;
    const deptName = (d.department_name || fallbackDeptName || '').trim() || undefined;
    const parsedSentMs = this.parseTimestampMs(d.sent_at);
    return {
      id: matId,
      backendCohortId: d.cohort_id,
      backendCourseId: d.course_id,
      backendMaterialId: d.material_id,
      backendDeliveryId: d.id,
      batchId: `backend-batch-${d.cohort_id}`,
      title: d.title,
      module: d.source_department_name || deptName || 'Course Vault',
      type: isVideo ? 'video' : isVaultFile ? (rawType === 'pdf' ? 'pdf' : 'code') : isNotes ? 'pdf' : 'slides',
      size: isNotes ? 'NOTES' : rawType.toUpperCase(),
      uploadedAt: parsedSentMs > 0 ? new Date(parsedSentMs).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }) : 'Delivered',
      author: d.sent_by_name || 'Instructor',
      downloadUrl,
      videoUrl: isVideo ? d.storage_key : undefined,
      fileName: extractedFileName,
      hasFile: isVaultFile,
      isDownloadable: isVaultFile,
      textNotes: isNotes ? d.storage_key : '',
      description: isVaultFile
        ? `Downloadable ${rawType.toUpperCase()} delivered from ${d.source_department_name || 'Course'} Resource Vault`
        : isNotes
          ? `Lecture notes delivered from ${d.source_department_name || 'Course'} Resource Vault`
          : `Delivered from ${d.source_department_name || 'Course'} Resource Vault`,
      isBookmarked: bookmarkedSet ? bookmarkedSet.has(matId) : false,
      departmentId: deptId,
      departmentName: deptName,
      createdAtMs: parsedSentMs
    };
  }

  private sortMaterialsNewestFirst(items: LearningMaterialItem[]): LearningMaterialItem[] {
    return items
      .map((item, idx) => ({ item, idx }))
      .sort((a, b) => {
        const tA = a.item.createdAtMs ?? 0;
        const tB = b.item.createdAtMs ?? 0;
        if (tB !== tA) return tB - tA;
        const idA = a.item.backendDeliveryId ?? a.item.backendLessonId ?? a.item.backendMaterialId ?? 0;
        const idB = b.item.backendDeliveryId ?? b.item.backendLessonId ?? b.item.backendMaterialId ?? 0;
        if (idB !== idA) return idB - idA;
        return a.idx - b.idx;
      })
      .map(entry => entry.item);
  }

  async loadWorkspaceFromBackend(cohortId?: number): Promise<void> {
    if (!this.hasLiveBackend()) return;
    try {
      const targetCohortId = cohortId ?? this.getActiveBackendCohortId();
      const query = targetCohortId ? `?cohort_id=${encodeURIComponent(String(targetCohortId))}` : '';
      const res: any = await firstValueFrom(
        this.http.get(`${this.workspaceApiUrl}${query}`, { headers: this.getHeaders() })
      );
      if (!res) return;
      const current = this.getCohortData();
      const bookmarkedSet = new Set<string>(res.bookmarkedMaterialKeys || []);
      const allowedLessonTypes = new Set<string>(['video', 'text', 'download']);
      const sanitizedCurriculum: CurriculumChapter[] = (res.curriculum || []).map((ch: any) => ({
        ...ch,
        lessons: (ch.lessons || [])
          .filter((les: any) => allowedLessonTypes.has(String(les.type || '').toLowerCase()))
          .sort((a: any, b: any) => {
            const tA = this.parseTimestampMs(a.createdAt);
            const tB = this.parseTimestampMs(b.createdAt);
            if (tB !== tA) return tB - tA;
            return (Number(b.backendId ?? b.id) || 0) - (Number(a.backendId ?? a.id) || 0);
          })
      }));

      const lessonDerivedMaterials: LearningMaterialItem[] = [];
      for (const ch of sanitizedCurriculum) {
        for (const les of ch.lessons) {
          const matId = `mat-${les.id}`;
          const isDownloadable = les.type === 'download';
          const matType: LearningMaterialItem['type'] =
            les.type === 'video' ? 'video' : isDownloadable ? 'code' : 'pdf';
          const resolvedUrl =
            les.type === 'video'
              ? (les.videoUrl || les.downloadUrl || '')
              : isDownloadable
                ? (les.downloadUrl || '')
                : '';
          const parsedCreatedMs = this.parseTimestampMs(les.createdAt);
          lessonDerivedMaterials.push({
            id: matId,
            backendLessonId: les.backendId ?? this.resolveNumericId(les.id) ?? undefined,
            title: les.title,
            module: ch.title,
            type: matType,
            size: les.type === 'video' ? (les.duration || 'Video') : (les.fileSize || (les.type === 'text' ? 'Notes' : 'File')),
            uploadedAt: parsedCreatedMs > 0 ? new Date(parsedCreatedMs).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }) : 'Curriculum',
            author: les.trainer || 'Instructor',
            downloadUrl: resolvedUrl,
            videoUrl: les.type === 'video' ? resolvedUrl : undefined,
            fileName: les.fileName,
            hasFile: Boolean(les.hasFile),
            isDownloadable,
            textNotes: les.textNotes || '',
            description: les.description || (les.type === 'text' ? '' : 'Curriculum resource provided by instructor.'),
            isBookmarked: bookmarkedSet.has(matId),
            departmentName: les.departmentName || ch.departmentName || 'All / Common',
            departmentId: les.departmentId ?? ch.departmentId,
            createdAtMs: parsedCreatedMs > 0 ? parsedCreatedMs : (les.backendId ?? 0)
          });
        }
      }

      const deliveredMaterials: LearningMaterialItem[] = Array.isArray(res.deliveredMaterials)
        ? res.deliveredMaterials.map((d: any) =>
            this.mapDeliveredVaultItem(d, d.department_id, d.department_name, bookmarkedSet)
          )
        : (current.materials || [])
            .filter(m => m.id.startsWith('deliv-'))
            .map(m => ({ ...m, isBookmarked: bookmarkedSet.has(m.id) }));

      this.saveState({
        ...current,
        curriculum: sanitizedCurriculum,
        assignments: res.assignments || [],
        quizzes: res.quizzes || [],
        announcements: res.announcements || [],
        discussions: res.discussions || [],
        attendance: res.attendance || current.attendance,
        attendanceMatrix: res.attendanceMatrix || current.attendanceMatrix,
        progress: res.progress || current.progress,
        materials: this.sortMaterialsNewestFirst([...lessonDerivedMaterials, ...deliveredMaterials])
      });
    } catch (err) {
      console.warn('Could not load cohort workspace from backend:', err);
    }
  }

  private getHeaders(): HttpHeaders {
    const token =
      this.authService?.getToken() ??
      (typeof sessionStorage !== 'undefined'
        ? sessionStorage.getItem('lk_access_token')
        : null);
    return new HttpHeaders({
      Authorization: `Bearer ${token || ''}`
    });
  }

  getCurrentUser(): { id?: string | number; full_name: string; email: string; role: string } {
    const authUser = this.authService?.getCurrentUserSnapshot();
    if (authUser?.full_name && authUser.full_name !== 'Current User') {
      return {
        id: authUser.id,
        full_name: authUser.full_name,
        email: authUser.email,
        role: authUser.role
      };
    }

    try {
      const raw =
        (typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('lk_current_user') : null) ||
        (typeof localStorage !== 'undefined' ? localStorage.getItem('lk_current_user') : null);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.full_name && parsed.full_name !== 'Current User') {
          return parsed;
        }
      }
    } catch { }

    try {
      const stored = typeof localStorage !== 'undefined' ? localStorage.getItem('ase_managed_users') : null;
      if (stored) {
        const users = JSON.parse(stored);
        const teacher = users.find((u: any) => (u.role === 'teacher' || u.role === 'admin') && u.is_active && u.full_name !== 'Current User');
        if (teacher) {
          return {
            id: teacher.id,
            full_name: teacher.full_name,
            email: teacher.email,
            role: teacher.role
          };
        }
      }
    } catch { }

    return {
      id: 0,
      full_name: 'Assigned Instructor',
      email: 'instructor@platform.internal',
      role: 'teacher'
    };
  }

  // ---------------------------------------------------------------------------
  // CANONICAL PLATFORM LEARNERS REFERENCE (MATCHING USER MANAGEMENT & ROSTER)
  // ---------------------------------------------------------------------------
  static readonly CANONICAL_LEARNERS: Array<{
    id: number;
    name: string;
    email: string;
    admissionNo: string;
    specialization: string;
    squad: string;
    avatar: string;
    defaultStatus: Record<string, 'P' | 'A' | 'L' | 'H'>;
  }> = [];

  readonly canonicalLearners = CohortService.CANONICAL_LEARNERS;

  static isDemoLearner(item: { email?: string; name?: string; full_name?: string }): boolean {
    const email = item.email?.toLowerCase().trim();
    if (email) {
      if (email.endsWith('@example.com')) {
        const canonicalEmails = [
          'aarav.sharma@example.com',
          'priya.nair@example.com',
          'diya.verma@example.com',
          'ishaan.patel@example.com',
          'ananya.kapoor@example.com',
          'vihaan.rao@example.com',
          'saanvi.mehta@example.com',
          'rohan.iyer@example.com',
          'myra.joshi@example.com',
          'rohan.varma@example.com',
          'rahul.pandey@example.com'
        ];
        if (canonicalEmails.includes(email)) return true;
      }
    }
    const name = (item.name || item.full_name)?.toLowerCase().trim();
    if (name) {
      const canonicalNames = [
        'aarav sharma',
        'priya nair',
        'diya verma',
        'ishaan patel',
        'ananya kapoor',
        'vihaan rao',
        'saanvi mehta',
        'rohan iyer',
        'myra joshi',
        'rohan varma',
        'rahul pandey'
      ];
      if (canonicalNames.includes(name)) {
        if (!email || email.endsWith('@example.com')) return true;
      }
    }
    return false;
  }

  // ---------------------------------------------------------------------------
  // INITIAL DATA GENERATOR (MATCHING USER SCREENSHOTS & SYNCHRONIZED ROSTER)
  // ---------------------------------------------------------------------------
  private getInitialData(): CohortFullData {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('ase_cohort_state_v5');
      localStorage.removeItem('ase_cohort_state_v6');
    }

    const data: CohortFullData = this.getDefaultCohortData();

    if (data && data.details) {
      if (data.details.isLiveActive === undefined) {
        data.details.isLiveActive = false;
      }
      if (!data.details.activeLiveTrainer || data.details.activeLiveTrainer === 'Current User' || data.details.activeLiveTrainer === 'Priya Sharma') {
        data.details.activeLiveTrainer = data.details.leadTrainer?.name || this.getCurrentUser().full_name || 'Assigned Instructor';
      }
    }

    if (data && data.sessions) {
      data.sessions = data.sessions.filter(s =>
        !s.id.startsWith('sess-') &&
        s.trainer !== 'Priya Sharma' &&
        s.trainer !== 'Vikram Joshi' &&
        s.trainer !== 'Vikram Joshi (Guest Architect)'
      );
      const defaultTrainer = data.details?.leadTrainer?.name || this.getCurrentUser().full_name || 'Assigned Instructor';
      for (const s of data.sessions) {
        if (!s.trainer || s.trainer === 'Current User' || s.trainer === 'Priya Sharma') {
          s.trainer = defaultTrainer;
        }
      }
    }

    // Clean up any stale duration on non-video/non-live lessons in cached localStorage
    if (data && data.curriculum) {
      for (const ch of data.curriculum) {
        for (const les of ch.lessons) {
          if (les.type !== 'live' && les.type !== 'video') {
            delete les.duration;
          }
        }
      }
    }

    return this.syncLearnersWithPlatform(data);
  }

  private getDefaultCohortData(): CohortFullData {
    const currentUser = this.getCurrentUser();
    const trainerName = currentUser.full_name || 'Assigned Instructor';
    const trainerEmail = currentUser.email || '';
    const trainerAvatar = (trainerName.charAt(0) || 'I').toUpperCase();

    return {
      activeBatchId: '',
      batches: [],
      details: {
        id: '',
        name: '',
        code: '',
        department: '',
        departmentName: '',
        track: '',
        status: 'active',
        startDate: '',
        endDate: '',
        durationWeeks: 0,
        currentWeek: 0,
        currentModule: '',
        leadTrainer: {
          name: trainerName,
          title: '',
          email: trainerEmail,
          avatar: trainerAvatar,
          officeHours: '',
          bio: ''
        },
        mentors: [],
        description: '',
        objectives: [],
        meetingLink: '',
        slackChannel: '',
        githubOrg: '',
        isLiveActive: false,
        activeLiveSessionTitle: '',
        activeLiveStartTime: '',
        activeLiveDuration: ''
      },
      curriculum: [],
      attendanceMatrix: {
        dateRangeLabel: '',
        days: [],
        students: []
      },
      sessions: [],
      materials: [],
      assignments: [],
      attendance: {
        percentage: 0,
        totalSessions: 0,
        attended: 0,
        missed: 0,
        excused: 0,
        late: 0,
        minimumRequired: 85,
        checkedInToday: false,
        history: []
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
        attendanceRate: 0,
        milestones: [],
        earnedBadges: []
      },
      discussions: []
    };
  }

  // ---------------------------------------------------------------------------
  // PLATFORM LEARNER SYNCHRONIZATION
  // ---------------------------------------------------------------------------
  public syncLearnersWithPlatform(inputData?: CohortFullData): CohortFullData {
    try {
      const data: CohortFullData = inputData ? JSON.parse(JSON.stringify(inputData)) : this.getCohortData();
      if (!data || !data.attendanceMatrix) return data || this.getDefaultCohortData();

      // Gather all learners from User Management & Local Storage
      let managedUsers: any[] = [];
      if (typeof localStorage !== 'undefined') {
        try {
          const stored = localStorage.getItem('ase_managed_users');
          if (stored) managedUsers = JSON.parse(stored);
        } catch { }
      }

      // Check logged in user in sessionStorage
      const existingEmails = new Set(managedUsers.map((u: any) => u.email?.toLowerCase().trim()));
      if (typeof sessionStorage !== 'undefined') {
        try {
          const cur = sessionStorage.getItem('lk_current_user');
          if (cur) {
            const parsed = JSON.parse(cur);
            if (parsed.role === 'learner' && parsed.email && !existingEmails.has(parsed.email.toLowerCase().trim())) {
              managedUsers.push({
                id: parsed.id || Date.now(),
                full_name: parsed.full_name || 'Current Learner',
                email: parsed.email,
                role: 'learner',
                is_active: true,
                created_at: new Date().toISOString(),
                temporary_password: 'Welcome@2026'
              });
              existingEmails.add(parsed.email.toLowerCase().trim());
            }
          }
        } catch { }
      }

      // Filter to find real user-inserted learners (excluding demo learners)
      const userInsertedLearners = managedUsers.filter((u: any) =>
        u.role === 'learner' &&
        u.is_active !== false &&
        !CohortService.isDemoLearner(u)
      );

      let platformLearners: any[] = [];
      if (userInsertedLearners.length > 0) {
        // KEEP ONLY USER-INSERTED DATA AND REMOVE DEMO LEARNERS
        platformLearners = userInsertedLearners;

        // Clean demo learners from ase_managed_users cache in localStorage so they never creep back
        if (typeof localStorage !== 'undefined') {
          try {
            const nonDemoAll = managedUsers.filter((u: any) => !CohortService.isDemoLearner(u));
            if (nonDemoAll.length !== managedUsers.length) {
              localStorage.setItem('ase_managed_users', JSON.stringify(nonDemoAll));
            }
          } catch { }
        }
      } else {
        // Fallback to canonical learners only if no real user data exists yet
        platformLearners = CohortService.CANONICAL_LEARNERS.map((cl, idx) => ({
          id: cl.id || (100 + idx),
          full_name: cl.name,
          email: cl.email,
          role: 'learner',
          is_active: true,
          created_at: '2026-10-25T10:00:00Z',
          admissionNo: cl.admissionNo
        }));
      }

      const matrix = data.attendanceMatrix;
      const days = matrix.days || [];
      let existingRows = matrix.students || [];

      // If user-inserted learners exist, purge all demo students from existingRows
      if (userInsertedLearners.length > 0) {
        existingRows = existingRows.filter(s =>
          !CohortService.isDemoLearner({ name: s.name }) &&
          userInsertedLearners.some(u =>
            (u.full_name && u.full_name.trim().toLowerCase() === s.name.trim().toLowerCase()) ||
            (u.id && s.studentId === `std-${u.id}`)
          )
        );
      }

      // Sort platform learners deterministically (by ID ascending, or created_at)
      const sortedLearners = [...platformLearners].sort((a: any, b: any) => {
        const idA = Number(a.id) || 0;
        const idB = Number(b.id) || 0;
        if (idA !== idB && idA > 0 && idB > 0) return idA - idB;
        const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return dateA - dateB;
      });

      const usedAdmissionNos = new Set<string>();
      const usedStudentIds = new Set<string>();

      // Track the highest admission number sequence so future learners are always strictly incremental
      let maxSeqNumber = 0;
      for (const s of existingRows) {
        if (s.admissionNo) {
          const match = s.admissionNo.match(/SKL\/\d{4}\/(\d+)/);
          if (match) {
            const num = parseInt(match[1], 10);
            if (!isNaN(num) && num > maxSeqNumber) {
              maxSeqNumber = num;
            }
          }
        }
      }

      for (const l of sortedLearners) {
        const numId = Number(l.id);
        if (!isNaN(numId) && numId > 0 && numId < 10000 && numId > maxSeqNumber) {
          maxSeqNumber = numId;
        }
      }

      // Incremental generator ensuring uniqueness and sequential IDs for all current and future learners
      const allocateAdmissionNo = (preferredNum?: number): string => {
        if (preferredNum && preferredNum > 0) {
          const candidate = `SKL/2026/${String(preferredNum).padStart(4, '0')}`;
          if (!usedAdmissionNos.has(candidate)) {
            usedAdmissionNos.add(candidate);
            if (preferredNum > maxSeqNumber) maxSeqNumber = preferredNum;
            return candidate;
          }
        }
        maxSeqNumber++;
        let candidate = `SKL/2026/${String(maxSeqNumber).padStart(4, '0')}`;
        while (usedAdmissionNos.has(candidate)) {
          maxSeqNumber++;
          candidate = `SKL/2026/${String(maxSeqNumber).padStart(4, '0')}`;
        }
        usedAdmissionNos.add(candidate);
        return candidate;
      };

      // Generator for strictly unique studentId
      const allocateStudentId = (preferredId?: string | number): string => {
        let candidate = preferredId ? String(preferredId) : '';
        if (candidate && !usedStudentIds.has(candidate)) {
          usedStudentIds.add(candidate);
          return candidate;
        }
        let counter = 1;
        let alt = `std-${counter}`;
        while (usedStudentIds.has(alt)) {
          counter++;
          alt = `std-${counter}`;
        }
        usedStudentIds.add(alt);
        return alt;
      };

      // Map each platform learner to AttendanceStudentRow with guaranteed unique, incremental ID
      const updatedStudents: AttendanceStudentRow[] = sortedLearners.map((learner: any, index: number) => {
        const email = learner.email?.toLowerCase().trim();
        const name = learner.full_name?.trim();

        // Match existing row strictly by user id or exact name
        const existing = existingRows.find(s =>
          (learner.id && s.studentId === `std-${learner.id}`) ||
          (name && s.name.toLowerCase().trim() === name.toLowerCase())
        );

        // Assign strictly unique and incremental admission number
        let admissionNo = '';
        if (existing?.admissionNo && !usedAdmissionNos.has(existing.admissionNo)) {
          admissionNo = existing.admissionNo;
          usedAdmissionNos.add(admissionNo);
        } else {
          const prefNum = Number(learner.id) || (index + 1);
          admissionNo = allocateAdmissionNo(prefNum);
        }

        // Assign strictly unique studentId
        const studentId = allocateStudentId(existing?.studentId || (learner.id ? `std-${learner.id}` : undefined));

        // Build daily status
        const dailyStatus: Record<string, 'P' | 'A' | 'L' | 'H'> = {};
        let absCount = 0;
        let lveCount = 0;

        for (const d of days) {
          const dateKey = d.dateStr;
          let status: 'P' | 'A' | 'L' | 'H';

          if (existing && existing.dailyStatus && existing.dailyStatus[dateKey]) {
            status = existing.dailyStatus[dateKey];
          } else if (d.isWeekend) {
            status = 'H';
          } else {
            status = 'P';
          }

          dailyStatus[dateKey] = status;
          if (status === 'A') absCount++;
          if (status === 'L') lveCount++;
        }

        return {
          studentId,
          admissionNo,
          name: learner.full_name,
          absCount,
          lveCount,
          dailyStatus
        };
      });

      data.attendanceMatrix.students = updatedStudents;

      // Synchronize Members List
      const faculty = (data.members || []).filter(m => m.role !== 'learner');
      const squads = ['Squad Alpha (API & Gateway)', 'Squad Beta (UI & Design Systems)', 'Squad Gamma (DevOps & Telemetry)'];
      const specs = [
        'Backend & High-Throughput DBs',
        'Frontend Architecture & Testing',
        'FastAPI & Async Event Loops',
        'PostgreSQL & DB Migrations',
        'Angular Reactive Architecture',
        'Full-Stack Integration',
        'Cloud Microservices & Testing',
        'Distributed Systems & Queues'
      ];

      const updatedMembers: CohortMemberProfile[] = sortedLearners.map((learner: any, idx: number) => {
        const email = learner.email?.toLowerCase().trim();
        const existingMember = (data.members || []).find(m =>
          (email && m.email?.toLowerCase().trim() === email) ||
          m.name.toLowerCase().trim() === learner.full_name?.toLowerCase().trim()
        );

        const initials = learner.full_name
          ? learner.full_name.split(' ').map((n: string) => n.charAt(0)).join('').toUpperCase().slice(0, 2)
          : 'LN';

        return {
          id: existingMember?.id || `m-learner-${learner.id || idx + 1}`,
          name: learner.full_name,
          email: learner.email || `${learner.full_name.toLowerCase().replace(/\s+/g, '.')}@platform.internal`,
          role: 'learner',
          specialization: existingMember?.specialization || specs[idx % specs.length],
          squad: existingMember?.squad || squads[idx % squads.length],
          avatar: existingMember?.avatar || initials,
          status: existingMember?.status || 'online',
          progressPercentage: existingMember?.progressPercentage || (68 + (idx % 4) * 4)
        };
      });

      data.members = [...faculty, ...updatedMembers];

      // Synchronize Batches Learner Count
      if (data.batches && data.batches.length > 0) {
        data.batches[0].learnerCount = updatedStudents.length;
      }

      if (!inputData && this.dataSubject) {
        this.dataSubject.next(data);
      }

      return data;
    } catch (err) {
      console.error('Error syncing learners with platform:', err);
      return inputData || (this.dataSubject ? this.dataSubject.value : this.getDefaultCohortData());
    }
  }

  // ---------------------------------------------------------------------------
  // STATE PERSISTENCE & DATA ACCESS
  // ---------------------------------------------------------------------------
  getCohortData(): CohortFullData {
    if (this.dataSubject) {
      return this.dataSubject.value;
    }
    try {
      return this.getInitialData();
    } catch {
      return this.getDefaultCohortData();
    }
  }

  private saveState(data: CohortFullData): void {
    this.dataSubject.next(data);
  }

  // ---------------------------------------------------------------------------
  // TEACHER ACTION: BATCH MANAGEMENT (SCREENSHOT 1)
  // ---------------------------------------------------------------------------
  createBatch(
    name: string,
    startDate: string,
    endDate: string,
    track: string,
    learnerCount: number = 10,
    learnerIds: Array<number | string> = [],
    learnerNames: string[] = [],
    departmentName: string = 'Python',
    departmentId?: number,
    backendCohortId?: number,
    teacherIds: number[] = [],
    teacherNames: string[] = []
  ): CohortBatchCard {
    const current = this.getCohortData();
    const count = learnerIds.length > 0 ? learnerIds.length : learnerCount;
    const newBatch: CohortBatchCard = {
      id: backendCohortId ? `backend-batch-${backendCohortId}` : `batch-${Date.now()}`,
      backendCohortId,
      name,
      learnerCount: count,
      startDate,
      endDate,
      status: 'current',
      track: track || `${departmentName} Track`,
      departmentName: departmentName || 'All / Common',
      departmentId,
      learnerIds,
      learnerNames,
      teacherIds,
      teacherNames
    };

    const updated: CohortFullData = {
      ...current,
      batches: [newBatch, ...current.batches],
      activeBatchId: newBatch.id
    };

    this.saveState(updated);
    return newBatch;
  }

  deleteBatch(batchId: string): boolean {
    const current = this.getCohortData();
    const target = current.batches.find(b => b.id === batchId);
    const remaining = current.batches.filter(b => b.id !== batchId);
    if (remaining.length === current.batches.length) return false;

    const isDeletedBatchMaterial = (m: LearningMaterialItem): boolean =>
      m.batchId === batchId || (!!target?.backendCohortId && m.backendCohortId === target.backendCohortId);

    const nextActive = current.activeBatchId === batchId ? (remaining[0] || null) : remaining.find(b => b.id === current.activeBatchId) || remaining[0] || null;

    const updated: CohortFullData = {
      ...current,
      batches: remaining,
      activeBatchId: nextActive ? nextActive.id : '',
      materials: current.materials.filter(m => !isDeletedBatchMaterial(m)),
      sessions: current.sessions.filter(s => (s as any).batchId !== batchId),
      assignments: current.assignments.filter(a => (a as any).batchId !== batchId),
      quizzes: current.quizzes.filter(q => (q as any).batchId !== batchId),
      announcements: current.announcements.filter(an => (an as any).batchId !== batchId)
    };
    this.saveState(updated);
    return true;
  }

  syncBackendBatchesAndMaterials(
    backendBatches: Array<{
      id: number;
      department_id: number;
      department_name?: string | null;
      course_id?: number | null;
      name: string;
      start_date?: string | null;
      end_date?: string | null;
      status: string;
      teacher_ids: number[];
      teachers: Array<{ id: number; full_name: string; email: string }>;
      member_ids: number[];
      learner_count: number;
    }>,
    deliveredByCohort: Record<
      number,
      Array<{
        id: number;
        cohort_id: number;
        course_id: number;
        material_id: number;
        title: string;
        material_type: string;
        storage_key: string;
        source_department_name?: string | null;
        sent_by_name?: string | null;
        sent_at: string;
      }>
    >
  ): void {
    const current = this.getCohortData();
    const mappedBatches: CohortBatchCard[] = backendBatches.map(bc => ({
      id: `backend-batch-${bc.id}`,
      backendCohortId: bc.id,
      name: bc.name,
      learnerCount: bc.learner_count ?? bc.member_ids.length,
      startDate: bc.start_date ? new Date(bc.start_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Active',
      endDate: bc.end_date ? new Date(bc.end_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : 'SuperAdmin Controlled',
      status: bc.status === 'completed' ? 'alumni' : 'current',
      track: `${bc.department_name || 'Engineering'} Track`,
      departmentId: bc.department_id,
      departmentName: bc.department_name || undefined,
      learnerIds: bc.member_ids,
      teacherIds: bc.teacher_ids,
      teacherNames: (bc.teachers || []).map(t => t.full_name)
    }));

    const activeBackendIds = new Set(backendBatches.map(b => b.id));
    // Keep only local non-backend manual materials from non-deleted batches, plus live delivered Vault materials
    const preservedNonDelivered = current.materials.filter(
      m => !m.id.startsWith('deliv-') && (!m.backendCohortId || activeBackendIds.has(m.backendCohortId))
    );
    const deliveredItems: LearningMaterialItem[] = [];
    for (const bc of backendBatches) {
      const deliveries = deliveredByCohort[bc.id] || [];
      for (const d of deliveries) {
        deliveredItems.push(
          this.mapDeliveredVaultItem(d, bc.department_id, bc.department_name || undefined)
        );
      }
    }

    const activeBatch =
      mappedBatches.find(b => b.id === current.activeBatchId) ||
      mappedBatches[0] ||
      null;

    this.saveState({
      ...current,
      batches: mappedBatches,
      activeBatchId: activeBatch ? activeBatch.id : '',
      materials: this.sortMaterialsNewestFirst([...deliveredItems, ...preservedNonDelivered]),
      details: activeBatch
        ? {
            ...current.details,
            name: activeBatch.name,
            track: activeBatch.track || current.details.track,
            department: activeBatch.departmentName || current.details.department,
            departmentName: activeBatch.departmentName || current.details.departmentName,
            departmentId: activeBatch.departmentId || current.details.departmentId
          }
        : current.details
    });
  }

  setActiveBatch(batchId: string): void {
    const current = this.getCohortData();
    const target = current.batches.find(b => b.id === batchId);
    if (!target) return;

    this.saveState({
      ...current,
      activeBatchId: batchId,
      details: {
        ...current.details,
        name: target.name,
        track: target.track || current.details.track,
        department: target.departmentName || current.details.department,
        departmentName: target.departmentName || current.details.departmentName,
        departmentId: target.departmentId || current.details.departmentId
      }
    });
  }

  // ---------------------------------------------------------------------------
  // TEACHER ACTION: CURRICULUM & SYLLABUS BUILDER (SCREENSHOTS 2 & 3)
  // ---------------------------------------------------------------------------
  addChapter(title: string, departmentName: string = 'All / Common', departmentId?: number): CurriculumChapter {
    const current = this.getCohortData();
    const newChap: CurriculumChapter = {
      id: `chap-${Date.now()}`,
      title,
      sequenceOrder: current.curriculum.length + 1,
      isExpanded: true,
      departmentName,
      departmentId,
      lessons: []
    };

    const updated = {
      ...current,
      curriculum: [...current.curriculum, newChap]
    };
    this.saveState(updated);

    const cohortId = this.getActiveBackendCohortId();
    this.enqueueWorkspaceOp(async () => {
      const created: any = await firstValueFrom(
        this.http.post(
          `${this.workspaceApiUrl}/chapters`,
          {
            cohort_id: cohortId,
            department_id: departmentId ?? null,
            department_name: departmentName,
            title
          },
          { headers: this.getHeaders() }
        )
      );
      if (created?.backendId) {
        this.idAliasMap.set(newChap.id, Number(created.backendId));
      }
      await this.loadWorkspaceFromBackend(cohortId ?? undefined);
    });

    return newChap;
  }

  deleteChapter(chapterId: string): void {
    const current = this.getCohortData();
    this.saveState({
      ...current,
      curriculum: current.curriculum.filter(c => c.id !== chapterId)
    });

    this.enqueueWorkspaceOp(async () => {
      const numId = this.resolveNumericId(chapterId);
      if (numId) {
        await firstValueFrom(
          this.http.delete(`${this.workspaceApiUrl}/chapters/${numId}`, { headers: this.getHeaders() })
        );
        await this.loadWorkspaceFromBackend();
      }
    });
  }

  addLessonToChapter(
    chapterId: string,
    lesson: {
      title: string;
      type: LessonContentType;
      duration?: string;
      description?: string;
      videoUrl?: string;
      textNotes?: string;
      downloadUrl?: string;
      fileSize?: string;
      fileName?: string;
      scheduledDate?: string;
      scheduledTime?: string;
      meetingUrl?: string;
      isLiveNow?: boolean;
      trainer?: string;
      departmentName?: string;
      departmentId?: number;
      quizQuestionsCount?: number;
      points?: number;
    }
  ): void {
    const current = this.getCohortData();
    const cIdx = current.curriculum.findIndex(c => c.id === chapterId);
    if (cIdx === -1) return;

    const isLive = lesson.type === 'live' && !!lesson.isLiveNow;
    let duration: string | undefined = undefined;
    if (lesson.type === 'live') {
      duration = lesson.duration || '2 Hours';
    } else if (lesson.type === 'video') {
      duration = lesson.duration || '15:00';
    } else {
      duration = undefined; // Notes, File, Quiz, Assignment must NEVER have duration!
    }
    const scheduledTime = lesson.scheduledTime || '10:00 AM – 12:00 PM IST';
    const scheduledDate = lesson.scheduledDate || 'Today';
    const meetingUrl = lesson.meetingUrl || current.details.meetingLink || 'https://meet.google.com/ase-cohort-live';
    const resolvedTrainer = lesson.trainer || this.getCurrentUser().full_name;

    const targetChap = current.curriculum[cIdx];
    const newLesson: CurriculumLesson = {
      id: `les-${Date.now()}`,
      title: lesson.title,
      type: lesson.type,
      duration: duration,
      description: lesson.description || '',
      videoUrl: lesson.videoUrl,
      textNotes: lesson.textNotes,
      downloadUrl: lesson.downloadUrl || '#',
      fileSize: lesson.fileSize || '2.5 MB',
      fileName: lesson.fileName,
      scheduledDate: scheduledDate,
      scheduledTime: scheduledTime,
      meetingUrl: meetingUrl,
      isLiveNow: isLive,
      isPublished: true,
      trainer: resolvedTrainer,
      departmentName: (lesson as any).departmentName || targetChap.departmentName || 'All / Common',
      departmentId: (lesson as any).departmentId || targetChap.departmentId,
      createdAt: new Date().toISOString()
    };

    // Strict 5-option routing: live & assignment lessons NEVER belong inside Curriculum or Materials
    const includeInCurriculum =
      lesson.type === 'video' || lesson.type === 'text' || lesson.type === 'download';

    const updatedCurriculum = [...current.curriculum];
    if (includeInCurriculum) {
      const updatedChap = {
        ...current.curriculum[cIdx],
        lessons: [newLesson, ...current.curriculum[cIdx].lessons]
      };
      updatedCurriculum[cIdx] = updatedChap;
    }

    // Synchronize ONLY video, text/notes, and downloadable resources to materials
    let updatedMaterials = [...current.materials];
    if (includeInCurriculum) {
      const isDownloadable = lesson.type === 'download';
      const matType: 'pdf' | 'video' | 'code' | 'slides' | 'cheatsheet' =
        lesson.type === 'video' ? 'video' : isDownloadable ? 'code' : 'pdf';

      const resUrl = lesson.type === 'video'
        ? (newLesson.videoUrl || lesson.videoUrl || '')
        : isDownloadable
          ? (newLesson.downloadUrl && newLesson.downloadUrl !== '#' ? newLesson.downloadUrl : '')
          : '';

      const displaySize = lesson.type === 'video'
        ? (newLesson.duration || '15 mins')
        : isDownloadable
          ? (newLesson.fileSize || 'File')
          : 'Notes';

      const deptName = newLesson.departmentName || targetChap.departmentName || 'All / Common';
      const deptId = newLesson.departmentId || targetChap.departmentId;

      const maxExistingMs = updatedMaterials.reduce((mx, m) => Math.max(mx, m.createdAtMs ?? 0), 0);
      updatedMaterials.unshift({
        id: `mat-${newLesson.id}`,
        title: newLesson.title,
        module: targetChap.title,
        type: matType,
        size: displaySize,
        uploadedAt: 'Just now',
        author: this.getCurrentUser().full_name + ' (Teacher)',
        downloadUrl: resUrl,
        videoUrl: lesson.type === 'video' ? resUrl : undefined,
        fileName: lesson.fileName,
        hasFile: Boolean(isDownloadable && lesson.fileName),
        isDownloadable,
        textNotes: lesson.textNotes || '',
        description: newLesson.description || '',
        isBookmarked: false,
        departmentName: deptName,
        departmentId: deptId,
        createdAtMs: Math.max(Date.now(), maxExistingMs + 1)
      });
    }

    // Synchronize to training sessions (timetable) simultaneously
    let updatedSessions = [...current.sessions];
    if (lesson.type === 'live') {
      const liveTrainer = (lesson as any).trainer || this.getCurrentUser().full_name;
      const deptName = newLesson.departmentName || targetChap.departmentName || 'All / Common';
      const deptId = newLesson.departmentId || targetChap.departmentId;
      updatedSessions.unshift({
        id: `sess-${newLesson.id}`,
        title: newLesson.title,
        module: targetChap.title,
        trainer: liveTrainer,
        date: isLive ? 'Today (Live Session)' : scheduledDate,
        time: scheduledTime,
        duration: duration || '2 Hours',
        status: isLive ? 'today' : 'upcoming',
        location: 'Virtual Classroom 1 (Google Meet)',
        meetingUrl: meetingUrl,
        topics: [newLesson.description || newLesson.title],
        departmentName: deptName,
        departmentId: deptId
      });
    }

    let updatedAssignments = [...current.assignments];
    if (lesson.type === 'assignment') {
      const deptName = newLesson.departmentName || targetChap.departmentName || 'All / Common';
      const deptId = newLesson.departmentId || targetChap.departmentId;
      updatedAssignments.unshift({
        id: `asg-${newLesson.id}`,
        title: newLesson.title,
        module: targetChap.title,
        description: newLesson.description || 'Complete the practical task according to rubric.',
        points: lesson.points || 100,
        dueDate: lesson.scheduledDate || new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0],
        dueRelative: 'Due in 7 days',
        status: 'pending',
        attachmentName: lesson.fileName,
        attachmentUrl: (lesson.downloadUrl && lesson.downloadUrl !== '#') ? lesson.downloadUrl : undefined,
        attachmentSize: lesson.fileSize,
        requirements: ['Code implementation meeting specification', 'Unit tests passing 85%+'],
        departmentName: deptName,
        departmentId: deptId
      });
    }

    let updatedQuizzes = [...current.quizzes];
    if (lesson.type === 'quiz') {
      const deptName = newLesson.departmentName || targetChap.departmentName || 'All / Common';
      const deptId = newLesson.departmentId || targetChap.departmentId;
      updatedQuizzes.unshift({
        id: `quiz-${newLesson.id}`,
        title: newLesson.title,
        module: targetChap.title,
        questionsCount: lesson.quizQuestionsCount || 5,
        durationMinutes: 15,
        dueDate: lesson.scheduledDate || 'Upcoming Sprint',
        passingScore: 70,
        status: 'available',
        attachmentName: lesson.fileName,
        attachmentUrl: (lesson.downloadUrl && lesson.downloadUrl !== '#') ? lesson.downloadUrl : undefined,
        attachmentSize: lesson.fileSize,
        departmentName: deptName,
        departmentId: deptId,
        questions: [
          {
            id: 1,
            text: `Core architectural checkpoint for ${newLesson.title}`,
            options: ['Option A (Recommended Pattern)', 'Option B (Legacy Fallback)', 'Option C (Anti-Pattern)', 'Option D (Incomplete Spec)'],
            correctIndex: 0,
            explanation: 'Based on instructor materials and attached problem assets.'
          }
        ]
      });
    }

    const updatedDetails = { ...current.details };
    if (isLive) {
      updatedDetails.isLiveActive = true;
      updatedDetails.activeLiveSessionTitle = newLesson.title;
      updatedDetails.activeLiveStartTime = scheduledTime;
      updatedDetails.activeLiveDuration = duration;
      updatedDetails.activeLiveTrainer = (lesson as any).trainer || this.getCurrentUser().full_name;
      updatedDetails.meetingLink = meetingUrl;
    }

    this.saveState({
      ...current,
      details: updatedDetails,
      curriculum: updatedCurriculum,
      materials: updatedMaterials,
      sessions: updatedSessions,
      assignments: updatedAssignments,
      quizzes: updatedQuizzes
    });

    const cohortId = this.getActiveBackendCohortId();
    this.enqueueWorkspaceOp(async () => {
      const numChapId = this.resolveNumericId(chapterId);
      if (!numChapId) return;
      await firstValueFrom(
        this.http.post(
          `${this.workspaceApiUrl}/chapters/${numChapId}/lessons`,
          {
            cohort_id: cohortId,
            department_id: newLesson.departmentId ?? null,
            department_name: newLesson.departmentName || 'All / Common',
            title: lesson.title,
            type: lesson.type,
            duration: duration,
            description: lesson.description || '',
            video_url: lesson.videoUrl || null,
            text_notes: lesson.textNotes || null,
            download_url: newLesson.downloadUrl || null,
            file_size: newLesson.fileSize || null,
            file_name: lesson.fileName || null,
            scheduled_date: scheduledDate,
            scheduled_time: scheduledTime,
            meeting_url: meetingUrl,
            is_live_now: isLive,
            trainer: resolvedTrainer,
            quiz_questions_count: lesson.quizQuestionsCount || null,
            points: lesson.points || null
          },
          { headers: this.getHeaders() }
        )
      );
      await this.loadWorkspaceFromBackend(cohortId ?? undefined);
    });
  }

  setLiveClassStatus(
    isActive: boolean,
    sessionTitle?: string,
    meetingUrl?: string,
    timing?: string,
    duration?: string,
    trainerName?: string
  ): void {
    const current = this.getCohortData();
    const updatedDetails = {
      ...current.details,
      isLiveActive: isActive
    };

    const resolvedTrainer = trainerName || this.getCurrentUser().full_name;

    if (isActive) {
      if (sessionTitle) updatedDetails.activeLiveSessionTitle = sessionTitle;
      if (meetingUrl) updatedDetails.meetingLink = meetingUrl;
      if (timing) updatedDetails.activeLiveStartTime = timing;
      if (duration) updatedDetails.activeLiveDuration = duration;
      updatedDetails.activeLiveTrainer = resolvedTrainer;
    }

    // Also update any matching curriculum lesson
    const updatedCurriculum = current.curriculum.map(ch => ({
      ...ch,
      lessons: ch.lessons.map(l => {
        if (l.type === 'live') {
          if (isActive && sessionTitle && l.title === sessionTitle) {
            return { ...l, isLiveNow: true };
          }
          if (!isActive) {
            return { ...l, isLiveNow: false };
          }
        }
        return l;
      })
    }));

    // Update sessions timetable status
    const updatedSessions = current.sessions.map(s => {
      if (s.status === 'today') {
        if (!isActive) {
          return { ...s, status: 'completed' as const };
        }
      }
      return s;
    });

    if (isActive && sessionTitle) {
      const exists = updatedSessions.some(s => s.title === sessionTitle);
      if (!exists) {
        updatedSessions.unshift({
          id: `sess-live-${Date.now()}`,
          title: sessionTitle,
          module: 'Active Live Module',
          trainer: resolvedTrainer,
          date: 'Today (Live Session)',
          time: updatedDetails.activeLiveStartTime || '10:00 AM – 12:00 PM IST',
          duration: updatedDetails.activeLiveDuration || '2 Hours',
          status: 'today',
          location: 'Virtual Classroom 1 (Google Meet)',
          meetingUrl: updatedDetails.meetingLink,
          topics: [sessionTitle]
        });
      } else {
        const idx = updatedSessions.findIndex(s => s.title === sessionTitle);
        if (idx !== -1) {
          updatedSessions[idx] = {
            ...updatedSessions[idx],
            trainer: resolvedTrainer,
            status: 'today',
            date: 'Today (Live Session)',
            meetingUrl: updatedDetails.meetingLink
          };
        }
      }
    }

    this.saveState({
      ...current,
      details: updatedDetails,
      curriculum: updatedCurriculum,
      sessions: updatedSessions
    });
  }

  toggleLessonLiveStatus(chapterId: string, lessonId: string, trainerName?: string): void {
    const current = this.getCohortData();
    const ch = current.curriculum.find(c => c.id === chapterId);
    if (!ch) return;
    const les = ch.lessons.find(l => l.id === lessonId);
    if (!les) return;

    const newLiveState = !les.isLiveNow;
    const resolvedTrainer = trainerName || (les as any).trainer || this.getCurrentUser().full_name;
    this.setLiveClassStatus(
      newLiveState,
      les.title,
      les.meetingUrl || current.details.meetingLink,
      les.scheduledTime || '10:00 AM – 12:00 PM IST',
      les.duration || '2 Hours',
      resolvedTrainer
    );

    this.enqueueWorkspaceOp(async () => {
      const numLesId = this.resolveNumericId(lessonId);
      if (numLesId) {
        await firstValueFrom(
          this.http.post(`${this.workspaceApiUrl}/lessons/${numLesId}/toggle-live`, {}, { headers: this.getHeaders() })
        );
      }
    });
  }

  publishCurriculumSchedule(params: {
    chapterId?: string;
    title: string;
    scheduledDate: string;
    scheduledTime: string;
    duration: string;
    meetingUrl: string;
    isLiveNow: boolean;
    description?: string;
    trainer?: string;
  }): void {
    const current = this.getCohortData();
    let targetChap = current.curriculum[0];
    if (params.chapterId && params.chapterId !== 'all') {
      const found = current.curriculum.find(c => c.id === params.chapterId);
      if (found) targetChap = found;
    }

    const resolvedTrainer = params.trainer || this.getCurrentUser().full_name;

    if (targetChap) {
      this.addLessonToChapter(targetChap.id, {
        title: params.title,
        type: 'live',
        duration: params.duration,
        scheduledDate: params.scheduledDate,
        scheduledTime: params.scheduledTime,
        meetingUrl: params.meetingUrl,
        isLiveNow: params.isLiveNow,
        description: params.description || 'Published curriculum live hands-on session.',
        trainer: resolvedTrainer
      } as any);
    }

    if (params.isLiveNow) {
      this.setLiveClassStatus(
        true,
        params.title,
        params.meetingUrl,
        params.scheduledTime,
        params.duration,
        resolvedTrainer
      );
    }
  }

  deleteLesson(chapterId: string, lessonId: string): void {
    const current = this.getCohortData();
    const cIdx = current.curriculum.findIndex(c => c.id === chapterId);
    if (cIdx === -1) return;

    const updatedChap = {
      ...current.curriculum[cIdx],
      lessons: current.curriculum[cIdx].lessons.filter(l => l.id !== lessonId)
    };

    const updatedCurriculum = [...current.curriculum];
    updatedCurriculum[cIdx] = updatedChap;

    this.saveState({
      ...current,
      curriculum: updatedCurriculum
    });

    this.enqueueWorkspaceOp(async () => {
      const numLesId = this.resolveNumericId(lessonId);
      if (numLesId) {
        await firstValueFrom(
          this.http.delete(`${this.workspaceApiUrl}/lessons/${numLesId}`, { headers: this.getHeaders() })
        );
        await this.loadWorkspaceFromBackend();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // TEACHER ACTION: ATTENDANCE SPREADSHEET & MARKING (SCREENSHOT 4)
  // ---------------------------------------------------------------------------
  toggleStudentAttendance(studentId: string | number, dateStr: string): void {
    const current = this.getCohortData();
    const matrix = current.attendanceMatrix;
    const sIdx = matrix.students.findIndex(s => s.studentId === studentId);
    if (sIdx === -1) return;

    const student = matrix.students[sIdx];
    const currentVal = student.dailyStatus[dateStr] || 'P';
    let nextVal: 'P' | 'A' | 'L' | 'H' = 'P';

    if (currentVal === 'P') nextVal = 'A';
    else if (currentVal === 'A') nextVal = 'L';
    else if (currentVal === 'L') nextVal = 'P';
    else nextVal = 'P';

    const updatedDaily = {
      ...student.dailyStatus,
      [dateStr]: nextVal
    };

    // Recalculate absCount & lveCount
    let abs = 0;
    let lve = 0;
    for (const d of Object.keys(updatedDaily)) {
      if (updatedDaily[d] === 'A') abs++;
      if (updatedDaily[d] === 'L') lve++;
    }

    const updatedStudent: AttendanceStudentRow = {
      ...student,
      dailyStatus: updatedDaily,
      absCount: abs,
      lveCount: lve
    };

    const updatedStudents = [...matrix.students];
    updatedStudents[sIdx] = updatedStudent;

    this.saveState({
      ...current,
      attendanceMatrix: {
        ...matrix,
        students: updatedStudents
      }
    });

    const cohortId = this.getActiveBackendCohortId();
    const backendUserId = (student as any).backendUserId ?? this.resolveNumericId(studentId);
    this.enqueueWorkspaceOp(async () => {
      if (!backendUserId) return;
      await firstValueFrom(
        this.http.post(
          `${this.workspaceApiUrl}/attendance/toggle`,
          { cohort_id: cohortId, learner_user_id: backendUserId, date_str: dateStr, status: nextVal },
          { headers: this.getHeaders() }
        )
      );
    });
  }

  markAttendanceForDate(dateStr: string, status: 'P' | 'A' | 'L'): void {
    const current = this.getCohortData();
    const matrix = current.attendanceMatrix;

    const updatedStudents = matrix.students.map(s => {
      const updatedDaily = {
        ...s.dailyStatus,
        [dateStr]: status
      };
      let abs = 0;
      let lve = 0;
      for (const d of Object.keys(updatedDaily)) {
        if (updatedDaily[d] === 'A') abs++;
        if (updatedDaily[d] === 'L') lve++;
      }
      return {
        ...s,
        dailyStatus: updatedDaily,
        absCount: abs,
        lveCount: lve
      };
    });

    this.saveState({
      ...current,
      attendanceMatrix: {
        ...matrix,
        students: updatedStudents
      }
    });

    const cohortId = this.getActiveBackendCohortId();
    const learnerIds = matrix.students
      .map(s => (s as any).backendUserId ?? this.resolveNumericId(s.studentId))
      .filter((id): id is number => typeof id === 'number' && id > 0);
    this.enqueueWorkspaceOp(async () => {
      await firstValueFrom(
        this.http.post(
          `${this.workspaceApiUrl}/attendance/bulk`,
          { cohort_id: cohortId, date_str: dateStr, status, learner_user_ids: learnerIds },
          { headers: this.getHeaders() }
        )
      );
    });
  }

  // ---------------------------------------------------------------------------
  // TEACHER ACTION: TRAINING SCHEDULE (SCREENSHOT 5)
  // ---------------------------------------------------------------------------
  addSession(session: {
    title: string;
    module: string;
    trainer: string;
    trainerId?: number;
    date: string;
    time: string;
    duration: string;
    location: string;
    meetingUrl: string;
    topics: string[];
    isLiveNow?: boolean;
    departmentName?: string;
    departmentId?: number;
  }): TrainingSession {
    const current = this.getCohortData();
    const isLive = !!session.isLiveNow;
    const newSession: TrainingSession = {
      id: `sess-${Date.now()}`,
      title: session.title,
      module: session.module,
      trainer: session.trainer || this.getCurrentUser().full_name,
      trainerId: session.trainerId,
      date: session.date,
      time: session.time,
      duration: session.duration || '2 Hours',
      status: isLive ? 'today' : 'upcoming',
      location: session.location || 'Virtual Classroom 1 (Google Meet)',
      meetingUrl: session.meetingUrl || current.details.meetingLink,
      topics: session.topics && session.topics.length > 0 ? session.topics : [session.title],
      departmentName: session.departmentName || 'All / Common',
      departmentId: session.departmentId
    };

    const updatedDetails = { ...current.details };
    if (isLive) {
      updatedDetails.isLiveActive = true;
      updatedDetails.activeLiveSessionTitle = newSession.title;
      updatedDetails.activeLiveStartTime = newSession.time;
      updatedDetails.activeLiveDuration = newSession.duration;
      updatedDetails.activeLiveTrainer = newSession.trainer;
      updatedDetails.meetingLink = newSession.meetingUrl;
    }

    this.saveState({
      ...current,
      details: updatedDetails,
      sessions: [newSession, ...current.sessions]
    });

    return newSession;
  }

  startSession(sessionId: string, startedByTrainerName?: string): void {
    const current = this.getCohortData();
    let startedSession: TrainingSession | undefined;

    const teacherName = startedByTrainerName || this.getCurrentUser().full_name || current.details.leadTrainer?.name || 'Assigned Instructor';

    const updatedSessions = current.sessions.map(s => {
      if (s.id === sessionId) {
        const assignedTrainer = s.trainer && s.trainer !== 'Current User' ? s.trainer : teacherName;
        startedSession = {
          ...s,
          trainer: assignedTrainer,
          status: 'today' as const
        };
        return startedSession;
      }
      if (s.status === 'today') {
        return { ...s, status: 'completed' as const };
      }
      return s;
    });

    const updatedDetails = { ...current.details };
    if (startedSession) {
      updatedDetails.isLiveActive = true;
      updatedDetails.activeLiveSessionTitle = (startedSession as TrainingSession).title;
      updatedDetails.activeLiveStartTime = (startedSession as TrainingSession).time;
      updatedDetails.activeLiveDuration = (startedSession as TrainingSession).duration;
      updatedDetails.activeLiveTrainer = (startedSession as TrainingSession).trainer || teacherName;
      updatedDetails.meetingLink = (startedSession as TrainingSession).meetingUrl;
    }

    this.saveState({
      ...current,
      details: updatedDetails,
      sessions: updatedSessions
    });
  }

  endSession(sessionId: string): void {
    const current = this.getCohortData();
    const updatedSessions = current.sessions.map(s => {
      if (s.id === sessionId) {
        return { ...s, status: 'completed' as const };
      }
      return s;
    });

    const remainingLive = updatedSessions.find(s => s.status === 'today');
    const updatedDetails = { ...current.details };
    if (remainingLive) {
      updatedDetails.isLiveActive = true;
      updatedDetails.activeLiveSessionTitle = remainingLive.title;
      updatedDetails.activeLiveStartTime = remainingLive.time;
      updatedDetails.activeLiveDuration = remainingLive.duration;
      updatedDetails.activeLiveTrainer = remainingLive.trainer;
      updatedDetails.meetingLink = remainingLive.meetingUrl;
    } else {
      updatedDetails.isLiveActive = false;
      const nextUp = updatedSessions.find(s => s.status === 'upcoming');
      if (nextUp) {
        updatedDetails.activeLiveSessionTitle = nextUp.title;
        updatedDetails.activeLiveStartTime = nextUp.time;
        updatedDetails.activeLiveDuration = nextUp.duration;
        updatedDetails.activeLiveTrainer = (nextUp.trainer && nextUp.trainer !== 'Current User') ? nextUp.trainer : (current.details.leadTrainer?.name || 'Assigned Instructor');
        updatedDetails.meetingLink = nextUp.meetingUrl;
      }
    }

    this.saveState({
      ...current,
      details: updatedDetails,
      sessions: updatedSessions
    });
  }

  sanitizeTrainerNames(): void {
    const current = this.getCohortData();
    let changed = false;
    const defaultTrainer = this.getCurrentUser().full_name || current.details.leadTrainer?.name || 'Assigned Instructor';

    const updatedSessions = current.sessions.map(s => {
      if (!s.trainer || s.trainer === 'Current User') {
        changed = true;
        return { ...s, trainer: defaultTrainer };
      }
      return s;
    });

    const updatedDetails = { ...current.details };
    if (!updatedDetails.activeLiveTrainer || updatedDetails.activeLiveTrainer === 'Current User') {
      changed = true;
      updatedDetails.activeLiveTrainer = defaultTrainer;
    }

    if (changed) {
      this.saveState({
        ...current,
        details: updatedDetails,
        sessions: updatedSessions
      });
    }
  }

  setSessions(sessions: TrainingSession[]): void {
    const current = this.getCohortData();
    const activeLive = sessions.find(s => s.status === 'today');
    const updatedDetails = { ...current.details };
    if (activeLive) {
      updatedDetails.isLiveActive = true;
      updatedDetails.activeLiveSessionTitle = activeLive.title;
      updatedDetails.activeLiveStartTime = activeLive.time;
      updatedDetails.activeLiveDuration = activeLive.duration;
      updatedDetails.activeLiveTrainer = activeLive.trainer;
      updatedDetails.meetingLink = activeLive.meetingUrl || updatedDetails.meetingLink;
    } else {
      updatedDetails.isLiveActive = false;
      const nextUp = sessions.find(s => s.status === 'upcoming');
      if (nextUp) {
        updatedDetails.activeLiveSessionTitle = nextUp.title;
        updatedDetails.activeLiveStartTime = nextUp.time;
        updatedDetails.activeLiveDuration = nextUp.duration;
        updatedDetails.activeLiveTrainer = nextUp.trainer;
        updatedDetails.meetingLink = nextUp.meetingUrl || updatedDetails.meetingLink;
      }
    }
    this.saveState({
      ...current,
      details: updatedDetails,
      sessions
    });
  }

  deleteSession(sessionId: string): void {
    const current = this.getCohortData();
    this.saveState({
      ...current,
      sessions: current.sessions.filter(s => s.id !== sessionId)
    });
  }

  // ---------------------------------------------------------------------------
  // TEACHER ACTION: ASSIGNMENTS & GRADING
  // ---------------------------------------------------------------------------
  addAssignment(asg: {
    title: string;
    module: string;
    description: string;
    points: number;
    dueDate: string;
    requirements: string[];
    departmentName?: string;
    departmentId?: number;
  }): void {
    const current = this.getCohortData();
    const newAsg: CohortAssignment = {
      id: `asg-${Date.now()}`,
      title: asg.title,
      module: asg.module,
      description: asg.description,
      points: asg.points || 100,
      dueDate: asg.dueDate,
      dueRelative: `Due on ${asg.dueDate}`,
      status: 'pending',
      requirements: asg.requirements || ['Implement required functionality', 'Add comprehensive test cases'],
      departmentName: asg.departmentName || 'All / Common',
      departmentId: asg.departmentId
    };

    this.saveState({
      ...current,
      assignments: [newAsg, ...current.assignments],
      progress: {
        ...current.progress,
        totalAssignments: current.progress.totalAssignments + 1
      }
    });

    const cohortId = this.getActiveBackendCohortId();
    this.enqueueWorkspaceOp(async () => {
      const created: any = await firstValueFrom(
        this.http.post(
          `${this.workspaceApiUrl}/assignments`,
          {
            cohort_id: cohortId,
            department_id: asg.departmentId ?? null,
            department_name: asg.departmentName || 'All / Common',
            title: asg.title,
            module: asg.module,
            description: asg.description,
            points: asg.points || 100,
            due_date: asg.dueDate,
            requirements: asg.requirements || []
          },
          { headers: this.getHeaders() }
        )
      );
      if (created?.backendId) {
        this.idAliasMap.set(newAsg.id, Number(created.backendId));
      }
      await this.loadWorkspaceFromBackend(cohortId ?? undefined);
    });
  }

  gradeAssignment(assignmentId: string, score: number, feedback: string): void {
    const current = this.getCohortData();
    const aIdx = current.assignments.findIndex(a => a.id === assignmentId);
    if (aIdx === -1) return;

    const target = current.assignments[aIdx];
    const updatedAsg: CohortAssignment = {
      ...target,
      status: 'graded',
      score,
      trainerFeedback: feedback
    };

    const newAssignments = [...current.assignments];
    newAssignments[aIdx] = updatedAsg;

    this.saveState({
      ...current,
      assignments: newAssignments
    });

    const targetLearnerId = (target as any).learnerUserId ?? null;
    this.enqueueWorkspaceOp(async () => {
      const numId = this.resolveNumericId(assignmentId);
      if (numId) {
        await firstValueFrom(
          this.http.post(
            `${this.workspaceApiUrl}/assignments/${numId}/grade`,
            { learner_user_id: targetLearnerId, score, feedback },
            { headers: this.getHeaders() }
          )
        );
        await this.loadWorkspaceFromBackend();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // TEACHER ACTION: QUIZZES
  // ---------------------------------------------------------------------------
  addQuiz(quiz: {
    title: string;
    module: string;
    questionsCount: number;
    durationMinutes: number;
    passingScore: number;
    dueDate?: string;
    departmentName?: string;
    departmentId?: number;
  }): void {
    const current = this.getCohortData();
    const newQuiz: CohortQuiz = {
      id: `quiz-${Date.now()}`,
      title: quiz.title,
      module: quiz.module,
      questionsCount: quiz.questionsCount || 5,
      durationMinutes: quiz.durationMinutes || 15,
      dueDate: quiz.dueDate || 'Scheduled by Instructor',
      passingScore: quiz.passingScore || 70,
      status: 'available',
      departmentName: quiz.departmentName || current.details.department || 'Python',
      departmentId: quiz.departmentId ?? current.details.departmentId,
      questions: [
        {
          id: 1,
          text: `Checkpoint question for ${quiz.title}?`,
          options: ['Option A (Correct standard)', 'Option B', 'Option C', 'Option D'],
          correctIndex: 0,
          explanation: 'Demonstrates baseline comprehension of module principles.'
        }
      ]
    };

    this.saveState({
      ...current,
      quizzes: [newQuiz, ...current.quizzes],
      progress: {
        ...current.progress,
        totalQuizzes: current.progress.totalQuizzes + 1
      }
    });

    const cohortId = this.getActiveBackendCohortId();
    this.enqueueWorkspaceOp(async () => {
      const created: any = await firstValueFrom(
        this.http.post(
          `${this.workspaceApiUrl}/quizzes`,
          {
            cohort_id: cohortId,
            department_id: quiz.departmentId ?? null,
            department_name: quiz.departmentName || 'All / Common',
            title: quiz.title,
            module: quiz.module,
            questions_count: quiz.questionsCount || 5,
            duration_minutes: quiz.durationMinutes || 15,
            passing_score: quiz.passingScore || 70,
            due_date: quiz.dueDate || 'Scheduled by Instructor',
            questions: newQuiz.questions
          },
          { headers: this.getHeaders() }
        )
      );
      if (created?.backendId) {
        this.idAliasMap.set(newQuiz.id, Number(created.backendId));
      }
      await this.loadWorkspaceFromBackend(cohortId ?? undefined);
    });
  }

  // ---------------------------------------------------------------------------
  // TEACHER ACTION: ANNOUNCEMENTS
  // ---------------------------------------------------------------------------
  addAnnouncement(ann: {
    title: string;
    content: string;
    priority: 'urgent' | 'important' | 'notice';
    isPinned: boolean;
    tags: string[];
  }): void {
    const current = this.getCohortData();
    const user = this.getCurrentUser();

    const newAnn: CohortAnnouncement = {
      id: `ann-${Date.now()}`,
      title: ann.title,
      author: `${user.full_name} (Lead Trainer)`,
      authorRole: 'Lead Instructor',
      authorAvatar: user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'TR',
      date: 'Just now',
      priority: ann.priority,
      isPinned: ann.isPinned,
      isRead: false,
      content: ann.content,
      tags: ann.tags && ann.tags.length > 0 ? ann.tags : ['InstructorUpdate']
    };

    this.saveState({
      ...current,
      announcements: [newAnn, ...current.announcements]
    });

    const cohortId = this.getActiveBackendCohortId();
    this.enqueueWorkspaceOp(async () => {
      const created: any = await firstValueFrom(
        this.http.post(
          `${this.workspaceApiUrl}/announcements`,
          {
            cohort_id: cohortId,
            department_id: current.details.departmentId ?? null,
            title: ann.title,
            content: ann.content,
            priority: ann.priority,
            is_pinned: ann.isPinned,
            tags: ann.tags || []
          },
          { headers: this.getHeaders() }
        )
      );
      if (created?.backendId) {
        this.idAliasMap.set(newAnn.id, Number(created.backendId));
      }
      await this.loadWorkspaceFromBackend(cohortId ?? undefined);
    });
  }

  deleteAnnouncement(annId: string): void {
    const current = this.getCohortData();
    this.saveState({
      ...current,
      announcements: current.announcements.filter(a => a.id !== annId)
    });

    this.enqueueWorkspaceOp(async () => {
      const numId = this.resolveNumericId(annId);
      if (numId) {
        await firstValueFrom(
          this.http.delete(`${this.workspaceApiUrl}/announcements/${numId}`, { headers: this.getHeaders() })
        );
        await this.loadWorkspaceFromBackend();
      }
    });
  }

  // ---------------------------------------------------------------------------
  // LEARNER ACTIONS (PRESERVED & FULLY FUNCTIONAL)
  // ---------------------------------------------------------------------------
  checkInToday(): boolean {
    const current = this.getCohortData();
    if (current.attendance.checkedInToday) return true;

    const user = this.getCurrentUser();
    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const newRecord: AttendanceRecordItem = {
      sessionId: 'sess-today',
      sessionTitle: current.sessions.find(s => s.status === 'today')?.title || "Today's Active Session",
      date: 'Today, Just Now',
      status: 'present',
      recordedAt: `${nowStr} IST`,
      recordedBy: `${user.full_name} (Self Check-in)`
    };

    const updatedAttended = current.attendance.attended + 1;
    const updatedTotal = current.attendance.totalSessions;
    const updatedPct = Math.round((updatedAttended / (updatedTotal || 1)) * 100);

    const updated: CohortFullData = {
      ...current,
      attendance: {
        ...current.attendance,
        attended: updatedAttended,
        percentage: updatedPct,
        checkedInToday: true,
        history: [newRecord, ...current.attendance.history]
      },
      progress: {
        ...current.progress,
        attendanceRate: updatedPct
      }
    };

    this.saveState(updated);

    const cohortId = this.getActiveBackendCohortId();
    this.enqueueWorkspaceOp(async () => {
      await firstValueFrom(
        this.http.post(
          `${this.workspaceApiUrl}/attendance/check-in`,
          { cohort_id: cohortId, session_title: newRecord.sessionTitle },
          { headers: this.getHeaders() }
        )
      );
      await this.loadWorkspaceFromBackend(cohortId ?? undefined);
    });
    return true;
  }

  submitAssignment(assignmentId: string, submissionUrl: string, notes: string): boolean {
    const current = this.getCohortData();
    const asgIndex = current.assignments.findIndex(a => a.id === assignmentId);
    if (asgIndex === -1) return false;

    const target = current.assignments[asgIndex];
    if (target.status !== 'pending') {
      return false; // Strict one-time assignment submission lock
    }

    const updatedAssignment: CohortAssignment = {
      ...target,
      status: 'submitted',
      submissionDate: new Date().toISOString(),
      submissionUrl,
      submissionNotes: notes,
      dueRelative: 'Submitted — Locked',
      trainerFeedback: 'Submission received and locked for manual trainer evaluation.'
    };

    const newAssignments = [...current.assignments];
    newAssignments[asgIndex] = updatedAssignment;

    const updated: CohortFullData = {
      ...current,
      assignments: newAssignments,
      progress: {
        ...current.progress,
        assignmentsSubmitted: current.progress.assignmentsSubmitted + 1
      }
    };

    this.saveState(updated);

    this.enqueueWorkspaceOp(async () => {
      const numId = this.resolveNumericId(assignmentId);
      if (numId) {
        await firstValueFrom(
          this.http.post(
            `${this.workspaceApiUrl}/assignments/${numId}/submit`,
            { submission_url: submissionUrl, submission_notes: notes },
            { headers: this.getHeaders() }
          )
        );
        await this.loadWorkspaceFromBackend();
      }
    });
    return true;
  }

  async submitAssignmentWithFile(
    assignmentId: string,
    file: File | null,
    submissionUrl: string,
    notes: string
  ): Promise<boolean> {
    if (!this.http) {
      return this.submitAssignment(assignmentId, submissionUrl, notes);
    }
    const current = this.getCohortData();
    const asgIndex = current.assignments.findIndex(a => a.id === assignmentId);
    if (asgIndex === -1) return false;
    const target = current.assignments[asgIndex];
    if (target.status !== 'pending') {
      return false; // Strict one-time assignment submission lock
    }

    const numId = this.resolveNumericId(assignmentId) ?? target.backendId;
    if (!numId) {
      return this.submitAssignment(assignmentId, submissionUrl, notes);
    }

    const formData = new FormData();
    formData.append('submission_url', submissionUrl || '');
    formData.append('submission_notes', notes || '');
    if (file) {
      formData.append('file', file);
    }

    const res: any = await firstValueFrom(
      this.http.post(`${this.workspaceApiUrl}/assignments/${numId}/submit-file`, formData, {
        headers: this.getHeaders()
      })
    );

    const updatedAssignment: CohortAssignment = {
      ...target,
      status: 'submitted',
      submissionId: res?.submission_id ? Number(res.submission_id) : target.submissionId,
      submissionDate: new Date().toISOString(),
      submissionUrl: submissionUrl || target.submissionUrl,
      submissionFileName: file?.name || res?.file_name || target.submissionFileName,
      hasSubmissionFile: Boolean(file || res?.file_name),
      submissionNotes: notes,
      dueRelative: 'Submitted — Locked',
      trainerFeedback: 'Submission received and locked for manual trainer evaluation.'
    };
    const newAssignments = [...current.assignments];
    newAssignments[asgIndex] = updatedAssignment;
    this.saveState({
      ...current,
      assignments: newAssignments,
      progress: {
        ...current.progress,
        assignmentsSubmitted: current.progress.assignmentsSubmitted + 1
      }
    });

    await this.loadWorkspaceFromBackend();
    return true;
  }

  async downloadAssignmentSubmissionFile(
    assignmentId: string | number,
    submissionId: number,
    fallbackName: string = 'submission.zip'
  ): Promise<void> {
    if (!this.http) return;
    const numId = typeof assignmentId === 'number' ? assignmentId : this.resolveNumericId(assignmentId);
    if (!numId || !submissionId) return;
    const blob = await firstValueFrom(
      this.http.get(`${this.workspaceApiUrl}/assignments/${numId}/submissions/${submissionId}/file`, {
        headers: this.getHeaders(),
        responseType: 'blob'
      })
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fallbackName || 'submission.zip';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async uploadDownloadableLesson(
    chapterId: string,
    file: File,
    payload: {
      title: string;
      description?: string;
      departmentId?: number;
      departmentName?: string;
    }
  ): Promise<boolean> {
    if (!this.hasLiveBackend()) {
      const sizeStr = file.size > 1024 * 1024
        ? `${(file.size / (1024 * 1024)).toFixed(2)} MB`
        : `${Math.max(1, Math.round(file.size / 1024))} KB`;
      this.addLessonToChapter(chapterId, {
        title: payload.title,
        type: 'download',
        description: payload.description || '',
        fileName: file.name,
        fileSize: sizeStr,
        departmentId: payload.departmentId,
        departmentName: payload.departmentName
      });
      return true;
    }

    const numChapId = this.resolveNumericId(chapterId);
    if (!numChapId) {
      await this.loadWorkspaceFromBackend();
    }
    const resolvedChapId = this.resolveNumericId(chapterId);
    if (!resolvedChapId) return false;

    const cohortId = this.getActiveBackendCohortId();
    const formData = new FormData();
    if (cohortId != null) formData.append('cohort_id', String(cohortId));
    if (payload.departmentId != null) formData.append('department_id', String(payload.departmentId));
    formData.append('department_name', payload.departmentName || 'All / Common');
    formData.append('title', payload.title);
    formData.append('description', payload.description || '');
    formData.append('file', file);

    await firstValueFrom(
      this.http.post(`${this.workspaceApiUrl}/chapters/${resolvedChapId}/lessons/upload`, formData, {
        headers: this.getHeaders()
      })
    );
    await this.loadWorkspaceFromBackend(cohortId ?? undefined);
    return true;
  }

  async downloadLessonFile(lessonId: string | number, fallbackName: string = 'resource'): Promise<void> {
    if (!this.http) return;
    const numId = typeof lessonId === 'number' ? lessonId : this.resolveNumericId(lessonId);
    if (!numId) return;
    await this.downloadAuthenticatedUrl(`${this.workspaceApiUrl}/lessons/${numId}/file`, fallbackName);
  }

  async fetchAuthenticatedFileBlob(url: string, inline: boolean = false): Promise<Blob> {
    if (!this.http) {
      throw new Error('HTTP client unavailable');
    }
    const targetUrl = inline
      ? `${url}${url.includes('?') ? '&' : '?'}inline=true`
      : url;
    return firstValueFrom(
      this.http.get(targetUrl, {
        headers: this.getHeaders(),
        responseType: 'blob'
      })
    );
  }

  async downloadAuthenticatedUrl(url: string, fallbackName: string = 'resource'): Promise<void> {
    const blob = await this.fetchAuthenticatedFileBlob(url, false);
    const objUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objUrl;
    a.download = fallbackName || 'resource';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(objUrl);
  }

  async createAssignmentWithFile(payload: {
    title: string;
    module: string;
    description: string;
    points: number;
    dueDate: string;
    requirements: string[];
    departmentId?: number;
    departmentName?: string;
    file: File | null;
  }): Promise<boolean> {
    if (!this.hasLiveBackend()) {
      this.addAssignment({
        title: payload.title,
        module: payload.module,
        description: payload.description,
        points: payload.points,
        dueDate: payload.dueDate,
        requirements: payload.requirements,
        departmentId: payload.departmentId,
        departmentName: payload.departmentName
      });
      return true;
    }

    const cohortId = this.getActiveBackendCohortId();
    const formData = new FormData();
    if (cohortId != null) formData.append('cohort_id', String(cohortId));
    if (payload.departmentId != null) formData.append('department_id', String(payload.departmentId));
    formData.append('department_name', payload.departmentName || 'All / Common');
    formData.append('title', payload.title);
    formData.append('module', payload.module || 'General');
    formData.append('description', payload.description || '');
    formData.append('points', String(payload.points || 100));
    formData.append('due_date', payload.dueDate || '');
    formData.append('requirements_json', JSON.stringify(payload.requirements || []));
    if (payload.file) {
      formData.append('file', payload.file);
    }

    await firstValueFrom(
      this.http.post(`${this.workspaceApiUrl}/assignments/with-file`, formData, {
        headers: this.getHeaders()
      })
    );
    await this.loadWorkspaceFromBackend(cohortId ?? undefined);
    return true;
  }

  async downloadAssignmentAttachment(
    assignmentId: string | number,
    fallbackName: string = 'assignment-file.pdf'
  ): Promise<void> {
    if (!this.http) return;
    const numId = typeof assignmentId === 'number' ? assignmentId : this.resolveNumericId(assignmentId);
    if (!numId) return;
    const blob = await firstValueFrom(
      this.http.get(`${this.workspaceApiUrl}/assignments/${numId}/attachment`, {
        headers: this.getHeaders(),
        responseType: 'blob'
      })
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fallbackName || 'assignment-file.pdf';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  submitQuiz(quizId: string, answers: Record<number, number>): { score: number; passed: boolean } {
    const current = this.getCohortData();
    const qIndex = current.quizzes.findIndex(q => q.id === quizId);
    if (qIndex === -1) return { score: 0, passed: false };

    const quiz = current.quizzes[qIndex];
    let correct = 0;
    for (const q of quiz.questions) {
      if (answers[q.id] === q.correctIndex) {
        correct++;
      }
    }

    const total = quiz.questions.length || 1;
    const score = Math.round((correct / total) * 100);
    const passed = score >= quiz.passingScore;

    const user = this.getCurrentUser();
    const newSubmission: CohortQuizSubmission = {
      studentId: user.id || 'curr-learner',
      studentName: user.full_name || 'Learner',
      studentEmail: user.email,
      score,
      passed,
      submittedAt: new Date().toISOString()
    };

    const existingSubmissions = quiz.submissions || [];
    const filteredSubs = existingSubmissions.filter(s => s.studentName !== newSubmission.studentName);
    const updatedSubmissions = [newSubmission, ...filteredSubs];

    const updatedQuiz: CohortQuiz = {
      ...quiz,
      status: 'completed',
      score,
      passed,
      completedAt: new Date().toISOString(),
      submissions: updatedSubmissions
    };

    const newQuizzes = [...current.quizzes];
    newQuizzes[qIndex] = updatedQuiz;

    const newQuizzesPassed = passed && quiz.status !== 'completed'
      ? current.progress.quizzesPassed + 1
      : current.progress.quizzesPassed;

    const updated: CohortFullData = {
      ...current,
      quizzes: newQuizzes,
      progress: {
        ...current.progress,
        quizzesPassed: newQuizzesPassed
      }
    };

    this.saveState(updated);

    this.enqueueWorkspaceOp(async () => {
      const numId = this.resolveNumericId(quizId);
      if (numId) {
        await firstValueFrom(
          this.http.post(
            `${this.workspaceApiUrl}/quizzes/${numId}/submit`,
            { answers },
            { headers: this.getHeaders() }
          )
        );
        await this.loadWorkspaceFromBackend();
      }
    });
    return { score, passed };
  }

  createDiscussionPost(title: string, category: DiscussionPost['category'], content: string): DiscussionPost {
    const current = this.getCohortData();
    const user = this.getCurrentUser();

    const newPost: DiscussionPost = {
      id: `disc-${Date.now()}`,
      title,
      category,
      author: `${user.full_name}`,
      authorRole: user.role === 'teacher' ? 'Staff Instructor' : 'Learner',
      authorAvatar: user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'TR',
      createdAt: 'Just now',
      content,
      likes: 0,
      hasLiked: false,
      isResolved: false,
      replies: []
    };

    const updated: CohortFullData = {
      ...current,
      discussions: [newPost, ...current.discussions]
    };

    this.saveState(updated);

    const cohortId = this.getActiveBackendCohortId();
    this.enqueueWorkspaceOp(async () => {
      const created: any = await firstValueFrom(
        this.http.post(
          `${this.workspaceApiUrl}/discussions`,
          {
            cohort_id: cohortId,
            department_id: current.details.departmentId ?? null,
            title,
            category,
            content
          },
          { headers: this.getHeaders() }
        )
      );
      if (created?.backendId) {
        this.idAliasMap.set(newPost.id, Number(created.backendId));
      }
      await this.loadWorkspaceFromBackend(cohortId ?? undefined);
    });
    return newPost;
  }

  replyToDiscussion(postId: string, content: string): boolean {
    const current = this.getCohortData();
    const postIndex = current.discussions.findIndex(d => d.id === postId);
    if (postIndex === -1) return false;

    const user = this.getCurrentUser();
    const isTeacher = user.role === 'teacher' || user.role === 'admin' || user.role === 'superadmin';

    const newReply: DiscussionReply = {
      id: `rep-${Date.now()}`,
      author: `${user.full_name}`,
      authorRole: isTeacher ? 'Staff Instructor' : 'Learner',
      authorAvatar: user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'TR',
      createdAt: 'Just now',
      content,
      isTrainerReply: isTeacher
    };

    const targetPost = current.discussions[postIndex];
    const updatedPost: DiscussionPost = {
      ...targetPost,
      replies: [...targetPost.replies, newReply]
    };

    const newDiscussions = [...current.discussions];
    newDiscussions[postIndex] = updatedPost;

    const updated: CohortFullData = {
      ...current,
      discussions: newDiscussions
    };

    this.saveState(updated);

    this.enqueueWorkspaceOp(async () => {
      const numId = this.resolveNumericId(postId);
      if (numId) {
        await firstValueFrom(
          this.http.post(
            `${this.workspaceApiUrl}/discussions/${numId}/replies`,
            { content },
            { headers: this.getHeaders() }
          )
        );
        await this.loadWorkspaceFromBackend();
      }
    });
    return true;
  }

  toggleLikePost(postId: string): void {
    const current = this.getCohortData();
    const postIndex = current.discussions.findIndex(d => d.id === postId);
    if (postIndex === -1) return;

    const post = current.discussions[postIndex];
    const hasLiked = !post.hasLiked;
    const likes = hasLiked ? post.likes + 1 : Math.max(0, post.likes - 1);

    const updatedPost: DiscussionPost = {
      ...post,
      hasLiked,
      likes
    };

    const newDiscussions = [...current.discussions];
    newDiscussions[postIndex] = updatedPost;

    this.saveState({
      ...current,
      discussions: newDiscussions
    });

    this.enqueueWorkspaceOp(async () => {
      const numId = this.resolveNumericId(postId);
      if (numId) {
        await firstValueFrom(
          this.http.post(`${this.workspaceApiUrl}/discussions/${numId}/like`, {}, { headers: this.getHeaders() })
        );
      }
    });
  }

  toggleBookmarkMaterial(materialId: string): void {
    const current = this.getCohortData();
    const matIndex = current.materials.findIndex(m => m.id === materialId);
    if (matIndex === -1) return;

    const mat = current.materials[matIndex];
    const updatedMat: LearningMaterialItem = {
      ...mat,
      isBookmarked: !mat.isBookmarked
    };

    const newMaterials = [...current.materials];
    newMaterials[matIndex] = updatedMat;

    this.saveState({
      ...current,
      materials: newMaterials
    });

    this.enqueueWorkspaceOp(async () => {
      await firstValueFrom(
        this.http.post(
          `${this.workspaceApiUrl}/bookmarks/toggle`,
          { material_key: materialId },
          { headers: this.getHeaders() }
        )
      );
    });
  }

  markAnnouncementRead(announcementId: string): void {
    const current = this.getCohortData();
    const annIndex = current.announcements.findIndex(a => a.id === announcementId);
    if (annIndex === -1) return;

    const ann = current.announcements[annIndex];
    if (ann.isRead) return;

    const updatedAnn: CohortAnnouncement = {
      ...ann,
      isRead: true
    };

    const newAnnouncements = [...current.announcements];
    newAnnouncements[annIndex] = updatedAnn;

    this.saveState({
      ...current,
      announcements: newAnnouncements
    });

    this.enqueueWorkspaceOp(async () => {
      const numId = this.resolveNumericId(announcementId);
      if (numId) {
        await firstValueFrom(
          this.http.post(`${this.workspaceApiUrl}/announcements/${numId}/read`, {}, { headers: this.getHeaders() })
        );
      }
    });
  }
}
