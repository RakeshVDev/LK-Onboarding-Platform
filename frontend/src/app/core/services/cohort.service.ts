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
}

export type LessonContentType = 'video' | 'text' | 'download' | 'quiz' | 'live' | 'assignment';

export interface CurriculumLesson {
  id: string;
  title: string;
  type: LessonContentType;
  duration?: string; // e.g. "05:21", "2 Hours"
  description?: string;
  videoUrl?: string;
  textNotes?: string;
  downloadUrl?: string;
  fileSize?: string;
  fileName?: string;
  quizQuestionsCount?: number;
  isPublished?: boolean;
  scheduledDate?: string;
  scheduledTime?: string;
  meetingUrl?: string;
  isLiveNow?: boolean;
  trainer?: string;
  departmentName?: string;
  departmentId?: number;
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
  title: string;
  module: string;
  type: 'pdf' | 'video' | 'code' | 'slides' | 'cheatsheet';
  size: string;
  uploadedAt: string;
  author: string;
  downloadUrl: string;
  videoUrl?: string;
  fileName?: string;
  description: string;
  isBookmarked?: boolean;
  departmentName?: string;
  departmentId?: number;
}

export interface CohortAssignment {
  id: string;
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
  submissionDate?: string;
  submissionUrl?: string;
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
  admissionNo: string;
  name: string;
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
  private readonly storageKey = 'ase_cohort_state_v4';
  private readonly apiUrl = '/training-api/api/v1/cohorts';

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
    } catch {}

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
    } catch {}

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
  static readonly CANONICAL_LEARNERS = [
    {
      id: 2,
      name: 'Aarav Sharma',
      email: 'aarav.sharma@example.com',
      admissionNo: 'SKL/2024/0182',
      specialization: 'Backend & High-Throughput DBs',
      squad: 'Squad Alpha (API & Gateway)',
      avatar: 'AS',
      defaultStatus: {
        '2026-10-27': 'P', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'A', '2026-10-31': 'P',
        '2026-11-01': 'H', '2026-11-02': 'H',
        '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
        '2026-11-08': 'H', '2026-11-09': 'H'
      } as Record<string, 'P' | 'A' | 'L' | 'H'>
    },
    {
      id: 3,
      name: 'Priya Nair',
      email: 'priya.nair@example.com',
      admissionNo: 'SKL/2024/0195',
      specialization: 'Frontend Architecture & Testing',
      squad: 'Squad Beta (UI & Design Systems)',
      avatar: 'PN',
      defaultStatus: {
        '2026-10-27': 'P', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'P',
        '2026-11-01': 'H', '2026-11-02': 'H',
        '2026-11-03': 'L', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
        '2026-11-08': 'H', '2026-11-09': 'H'
      } as Record<string, 'P' | 'A' | 'L' | 'H'>
    },
    {
      id: 6,
      name: 'Diya Verma',
      email: 'diya.verma@example.com',
      admissionNo: 'SKL/2023/0094',
      specialization: 'FastAPI & Async Event Loops',
      squad: 'Squad Alpha (API & Gateway)',
      avatar: 'DV',
      defaultStatus: {
        '2026-10-27': 'P', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'P',
        '2026-11-01': 'H', '2026-11-02': 'H',
        '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
        '2026-11-08': 'H', '2026-11-09': 'H'
      } as Record<string, 'P' | 'A' | 'L' | 'H'>
    },
    {
      id: 7,
      name: 'Ishaan Patel',
      email: 'ishaan.patel@example.com',
      admissionNo: 'SKL/2025/0247',
      specialization: 'PostgreSQL & DB Migrations',
      squad: 'Squad Gamma (DevOps & Telemetry)',
      avatar: 'IP',
      defaultStatus: {
        '2026-10-27': 'P', '2026-10-28': 'A', '2026-10-29': 'A', '2026-10-30': 'A', '2026-10-31': 'P',
        '2026-11-01': 'H', '2026-11-02': 'H',
        '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
        '2026-11-08': 'H', '2026-11-09': 'H'
      } as Record<string, 'P' | 'A' | 'L' | 'H'>
    },
    {
      id: 8,
      name: 'Ananya Kapoor',
      email: 'ananya.kapoor@example.com',
      admissionNo: 'SKL/2022/0038',
      specialization: 'Angular Reactive Architecture',
      squad: 'Squad Beta (UI & Design Systems)',
      avatar: 'AK',
      defaultStatus: {
        '2026-10-27': 'P', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'P',
        '2026-11-01': 'H', '2026-11-02': 'H',
        '2026-11-03': 'P', '2026-11-04': 'A', '2026-11-05': 'A', '2026-11-06': 'P', '2026-11-07': 'P',
        '2026-11-08': 'H', '2026-11-09': 'H'
      } as Record<string, 'P' | 'A' | 'L' | 'H'>
    },
    {
      id: 9,
      name: 'Vihaan Rao',
      email: 'vihaan.rao@example.com',
      admissionNo: 'SKL/2024/0163',
      specialization: 'Full-Stack Integration',
      squad: 'Squad Beta (UI & Design Systems)',
      avatar: 'VR',
      defaultStatus: {
        '2026-10-27': 'P', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'P',
        '2026-11-01': 'H', '2026-11-02': 'H',
        '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
        '2026-11-08': 'H', '2026-11-09': 'H'
      } as Record<string, 'P' | 'A' | 'L' | 'H'>
    },
    {
      id: 10,
      name: 'Saanvi Mehta',
      email: 'saanvi.mehta@example.com',
      admissionNo: 'SKL/2026/0312',
      specialization: 'Cloud Microservices & Testing',
      squad: 'Squad Alpha (API & Gateway)',
      avatar: 'SM',
      defaultStatus: {
        '2026-10-27': 'P', '2026-10-28': 'A', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'A',
        '2026-11-01': 'H', '2026-11-02': 'H',
        '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
        '2026-11-08': 'H', '2026-11-09': 'H'
      } as Record<string, 'P' | 'A' | 'L' | 'H'>
    },
    {
      id: 11,
      name: 'Rohan Iyer',
      email: 'rohan.iyer@example.com',
      admissionNo: 'SKL/2021/0021',
      specialization: 'Distributed Systems & Queues',
      squad: 'Squad Gamma (DevOps & Telemetry)',
      avatar: 'RI',
      defaultStatus: {
        '2026-10-27': 'P', '2026-10-28': 'A', '2026-10-29': 'A', '2026-10-30': 'A', '2026-10-31': 'P',
        '2026-11-01': 'H', '2026-11-02': 'H',
        '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
        '2026-11-08': 'H', '2026-11-09': 'H'
      } as Record<string, 'P' | 'A' | 'L' | 'H'>
    },
    {
      id: 12,
      name: 'Myra Joshi',
      email: 'myra.joshi@example.com',
      admissionNo: 'SKL/2025/0271',
      specialization: 'Data Pipelines & Kafka',
      squad: 'Squad Gamma (DevOps & Telemetry)',
      avatar: 'MJ',
      defaultStatus: {
        '2026-10-27': 'A', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'P',
        '2026-11-01': 'H', '2026-11-02': 'H',
        '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
        '2026-11-08': 'H', '2026-11-09': 'H'
      } as Record<string, 'P' | 'A' | 'L' | 'H'>
    },
    {
      id: 13,
      name: 'Rohan Varma',
      email: 'rohan.varma@example.com',
      admissionNo: 'SKL/2025/0304',
      specialization: 'Full-Stack & Database Optimization',
      squad: 'Squad Alpha (API & Gateway)',
      avatar: 'RV',
      defaultStatus: {
        '2026-10-27': 'P', '2026-10-28': 'P', '2026-10-29': 'A', '2026-10-30': 'P', '2026-10-31': 'P',
        '2026-11-01': 'H', '2026-11-02': 'H',
        '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
        '2026-11-08': 'H', '2026-11-09': 'H'
      } as Record<string, 'P' | 'A' | 'L' | 'H'>
    },
    {
      id: 14,
      name: 'Rahul Pandey',
      email: 'rahul.pandey@example.com',
      admissionNo: 'SKL/2026/0401',
      specialization: 'Full-Stack & Cloud Architecture',
      squad: 'Squad Alpha (API & Gateway)',
      avatar: 'RP',
      defaultStatus: {
        '2026-10-27': 'P', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'P',
        '2026-11-01': 'H', '2026-11-02': 'H',
        '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'L', '2026-11-07': 'P',
        '2026-11-08': 'H', '2026-11-09': 'H'
      } as Record<string, 'P' | 'A' | 'L' | 'H'>
    }
  ];

  readonly canonicalLearners = CohortService.CANONICAL_LEARNERS;

  // ---------------------------------------------------------------------------
  // INITIAL DATA GENERATOR (MATCHING USER SCREENSHOTS & SYNCHRONIZED ROSTER)
  // ---------------------------------------------------------------------------
  private getInitialData(): CohortFullData {
    let data: CohortFullData | undefined;

    if (typeof localStorage !== 'undefined') {
      const stored = localStorage.getItem(this.storageKey);
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          if (parsed.batches && parsed.curriculum && parsed.attendanceMatrix) {
            data = parsed;
          }
        } catch {}
      }
    }

    if (!data) {
      data = this.getDefaultCohortData();
    }

    if (data && data.details) {
      if (data.details.isLiveActive === undefined) {
        data.details.isLiveActive = false;
      }
      if (!data.details.activeLiveSessionTitle) {
        data.details.activeLiveSessionTitle = 'Live Interactive Hands-on Session';
      }
      if (!data.details.activeLiveStartTime) {
        data.details.activeLiveStartTime = '10:00 AM – 12:00 PM IST';
      }
      if (!data.details.activeLiveDuration) {
        data.details.activeLiveDuration = '2 Hours';
      }
      if (data.details.leadTrainer?.name === 'Priya Sharma') {
        const u = this.getCurrentUser();
        data.details.leadTrainer.name = u.full_name || 'Assigned Lead Instructor';
        data.details.leadTrainer.email = u.email || 'instructor@platform.internal';
        data.details.leadTrainer.avatar = (u.full_name?.charAt(0) || 'I').toUpperCase();
      }
      if (!data.details.activeLiveTrainer || data.details.activeLiveTrainer === 'Current User' || data.details.activeLiveTrainer === 'Priya Sharma') {
        data.details.activeLiveTrainer = data.details.leadTrainer?.name || this.getCurrentUser().full_name || 'Assigned Faculty';
      }
    }

    if (data && data.sessions) {
      // Purge any stale hardcoded mock sessions from local storage
      data.sessions = data.sessions.filter(s =>
        !s.id.startsWith('sess-') &&
        s.trainer !== 'Priya Sharma' &&
        s.trainer !== 'Vikram Joshi' &&
        s.trainer !== 'Vikram Joshi (Guest Architect)'
      );
      const defaultTrainer = data.details?.leadTrainer?.name || this.getCurrentUser().full_name || 'Assigned Faculty';
      for (const s of data.sessions) {
        if (!s.trainer || s.trainer === 'Current User' || s.trainer === 'Priya Sharma') {
          s.trainer = defaultTrainer;
        }
      }
    }

    if (data && data.quizzes) {
      const defaultSubs: Record<string, CohortQuizSubmission[]> = {
        'quiz-1': [
          { studentId: 'SKL/2024/0182', studentName: 'Aarav Sharma', score: 90, passed: true, submittedAt: '2026-10-21T16:00:00Z' },
          { studentId: 'SKL/2023/0094', studentName: 'Diya Verma', score: 100, passed: true, submittedAt: '2026-10-21T16:30:00Z' },
          { studentId: 'SKL/2025/0247', studentName: 'Ishaan Patel', score: 80, passed: true, submittedAt: '2026-10-21T17:15:00Z' },
          { studentId: 'SKL/2022/0038', studentName: 'Anaya Kapoor', score: 60, passed: false, submittedAt: '2026-10-21T17:45:00Z' },
          { studentId: 'SKL/2024/0163', studentName: 'Vihaan Rao', score: 90, passed: true, submittedAt: '2026-10-21T18:00:00Z' },
          { studentId: 'SKL/2026/0312', studentName: 'Saanvi Mehta', score: 95, passed: true, submittedAt: '2026-10-21T18:20:00Z' }
        ],
        'quiz-2': [
          { studentId: 'SKL/2024/0182', studentName: 'Aarav Sharma', score: 85, passed: true, submittedAt: '2026-10-29T14:20:00Z' },
          { studentId: 'SKL/2023/0094', studentName: 'Diya Verma', score: 90, passed: true, submittedAt: '2026-10-29T14:45:00Z' },
          { studentId: 'SKL/2025/0247', studentName: 'Ishaan Patel', score: 70, passed: true, submittedAt: '2026-10-29T15:00:00Z' },
          { studentId: 'SKL/2021/0021', studentName: 'Rohan Iyer', score: 65, passed: false, submittedAt: '2026-10-29T15:30:00Z' },
          { studentId: 'SKL/2025/0271', studentName: 'Myra Joshi', score: 85, passed: true, submittedAt: '2026-10-29T16:10:00Z' }
        ],
        'quiz-3': [
          { studentId: 'SKL/2024/0182', studentName: 'Aarav Sharma', score: 80, passed: true, submittedAt: '2026-11-04T11:00:00Z' },
          { studentId: 'SKL/2023/0094', studentName: 'Diya Verma', score: 100, passed: true, submittedAt: '2026-11-04T11:20:00Z' },
          { studentId: 'SKL/2024/0163', studentName: 'Vihaan Rao', score: 60, passed: false, submittedAt: '2026-11-04T11:45:00Z' }
        ]
      };

      for (const qz of data.quizzes) {
        if (!qz.submissions || qz.submissions.length === 0) {
          qz.submissions = defaultSubs[qz.id] || [
            { studentId: 'SKL/2024/0182', studentName: 'Aarav Sharma', score: 85, passed: true, submittedAt: '2026-11-03T10:00:00Z' },
            { studentId: 'SKL/2023/0094', studentName: 'Diya Verma', score: 90, passed: true, submittedAt: '2026-11-03T10:15:00Z' }
          ];
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
    return {
      activeBatchId: 'cohort-python-2026',

      // Screenshot 1: Batches List
      batches: [
        {
          id: 'cohort-python-2026',
          name: 'Python Cloud & Backend Batch 2026',
          learnerCount: 16,
          startDate: '15 Oct 2026',
          endDate: '15 Jan 2027',
          status: 'current',
          description: 'Intensive Python, FastAPI microservices, and asynchronous architecture program.',
          track: 'Python Engineering Track',
          departmentName: 'Python',
          departmentId: 8
        },
        {
          id: 'batch-dotnet-2026',
          name: 'C# & .NET Core Enterprise Systems 2026',
          learnerCount: 12,
          startDate: '03 Jan 2026',
          endDate: '28 Jul 2026',
          status: 'current',
          description: 'Enterprise backend microservices, Entity Framework, and cloud systems.',
          track: '.NET Engineering Track',
          departmentName: '.NET',
          departmentId: 7
        },
        {
          id: 'batch-java-2026',
          name: 'Java & Spring Boot Microservices 2026',
          learnerCount: 18,
          startDate: '30 Jun 2026',
          endDate: '30 Jun 2027',
          status: 'current',
          description: 'Spring Boot 3, Virtual Threads, and distributed reactive architectures.',
          track: 'Java Engineering Track',
          departmentName: 'Java',
          departmentId: 9
        },
        {
          id: 'batch-php-2026',
          name: 'Modern PHP & Laravel Cloud Batch 2026',
          learnerCount: 8,
          startDate: '01 Nov 2026',
          endDate: '28 Feb 2027',
          status: 'current',
          description: 'PHP 8.3 type safety, Laravel 11 microservices, and API performance.',
          track: 'PHP Engineering Track',
          departmentName: 'PHP',
          departmentId: 6
        },
        {
          id: 'batch-db-2026',
          name: 'Database Architecture & Query Engineering 2026',
          learnerCount: 9,
          startDate: '10 Nov 2026',
          endDate: '15 Mar 2027',
          status: 'current',
          description: 'Query planning, clustered index tuning, partitioning, and transactional consistency.',
          track: 'Database Engineering Track',
          departmentName: 'Database Engineer',
          departmentId: 10
        },
        {
          id: 'batch-common-foundations',
          name: 'ASE Foundational Engineering Cohort 2026',
          learnerCount: 25,
          startDate: '01 Oct 2026',
          endDate: '31 Mar 2027',
          status: 'current',
          description: 'Cross-discipline core foundations: Git workflows, Docker, CI/CD, Agile, and UI standards.',
          track: 'Foundational Engineering Track',
          departmentName: 'All / Common',
          departmentId: 11
        }
      ],

      details: {
        id: 'cohort-python-2026',
        name: 'Python Cloud & Backend Batch 2026',
        code: 'ASE-PY-01',
        department: 'Python',
        departmentName: 'Python',
        departmentId: 8,
        track: 'Python Engineering Track',
        status: 'active',
        startDate: '2026-10-15',
        endDate: '2027-01-15',
        durationWeeks: 12,
        currentWeek: 4,
        currentModule: 'Module 3: FastAPI & Angular Reactive Architecture',
        leadTrainer: {
          name: this.getCurrentUser().full_name || 'Assigned Lead Instructor',
          title: 'Staff Engineer & Technical Instructor',
          email: this.getCurrentUser().email || 'instructor@platform.internal',
          avatar: (this.getCurrentUser().full_name?.charAt(0) || 'I').toUpperCase(),
          officeHours: 'Mon & Thu: 4:00 PM – 5:30 PM IST',
          bio: 'Faculty lead overseeing cohort curriculum delivery, interactive code reviews, and enterprise evaluation milestones.'
        },
        mentors: [],
        description: 'Comprehensive 12-week intensive training program equipping Associate Software Engineers with end-to-end full-stack capabilities, cloud-native architecture, production-grade microservices, clean code standards, and agile collaboration.',
        objectives: [
          'Master clean architecture, SOLID principles, and enterprise design patterns.',
          'Build scalable microservices with Python, FastAPI, and PostgreSQL with robust unit & integration tests.',
          'Develop modern reactive single-page applications using Angular 17+ Signals, standalone components, and RxJS.',
          'Design cloud infrastructure with Docker, CI/CD automated pipelines, and Kubernetes deployment specs.',
          'Participate in team-based capstone engineering projects simulating real-world enterprise delivery.'
        ],
        meetingLink: 'https://meet.google.com/ase-cohort-live',
        slackChannel: '#ase-batch-2026-q1',
        githubOrg: 'https://github.com/ase-training-cohorts',
        isLiveActive: false,
        activeLiveSessionTitle: 'Live Interactive Hands-on Session',
        activeLiveStartTime: '10:00 AM – 12:00 PM IST',
        activeLiveDuration: '2 Hours'
      },

      // Screenshots 2 & 3: Curriculum Builder (Chapters & Lessons)
      curriculum: [
        {
          id: 'chap-1',
          title: '1. Engineering Foundations & Dev Workflows',
          sequenceOrder: 1,
          isExpanded: true,
          departmentName: 'All / Common',
          departmentId: 11,
          lessons: [
            {
              id: 'les-1',
              title: 'Welcome to the Course & Onboarding Briefing',
              type: 'text',
              description: 'Orientation to development workflows, code standards, and sprint expectations.',
              textNotes: 'Welcome to the ASE Batch! Please review the developer environment guidelines and clone our starter repository.',
              departmentName: 'All / Common',
              departmentId: 11,
              isPublished: true
            },
            {
              id: 'les-2',
              title: 'Course Overview & System Architecture',
              type: 'video',
              duration: '05:21',
              description: 'High-level walkthrough of the platform microservices architecture and module milestones.',
              videoUrl: 'https://storage.googleapis.com/ase-recordings/course-overview.mp4',
              departmentName: 'All / Common',
              departmentId: 11,
              isPublished: true
            },
            {
              id: 'les-3',
              title: 'Downloadable Resources & Environment Setup Script',
              type: 'download',
              description: 'CLI installation scripts, Docker Compose files, and local database seeds.',
              downloadUrl: '#',
              fileSize: '4.2 MB',
              departmentName: 'All / Common',
              departmentId: 11,
              isPublished: true
            }
          ]
        },
        {
          id: 'chap-2',
          title: '2. Python Core: FastAPI, AsyncIO & Microservices',
          sequenceOrder: 2,
          isExpanded: true,
          departmentName: 'Python',
          departmentId: 8,
          lessons: [
            {
              id: 'les-4',
              title: 'Understanding the Basics: FastAPI & Clean Architecture',
              type: 'video',
              duration: '12:45',
              description: 'Hands-on breakdown of routers, service layers, and repository decoupling.',
              videoUrl: 'https://storage.googleapis.com/ase-recordings/fastapi-basics.mp4',
              departmentName: 'Python',
              departmentId: 8,
              isPublished: true
            },
            {
              id: 'les-5',
              title: 'Asynchronous Programming with Python AsyncIO & Celery',
              type: 'text',
              description: 'Event loop concurrency, coroutines, and distributed background task queues.',
              textNotes: 'AsyncIO event loops manage non-blocking socket I/O efficiently for high-throughput API services.',
              departmentName: 'Python',
              departmentId: 8,
              isPublished: true
            },
            {
              id: 'les-6',
              title: 'Quick Checkpoint Quiz: Python AsyncIO & FastAPI',
              type: 'quiz',
              quizQuestionsCount: 5,
              description: '5-question sprint checkpoint evaluating coroutines, dependency injection, and Pydantic v2.',
              departmentName: 'Python',
              departmentId: 8,
              isPublished: true
            }
          ]
        },
        {
          id: 'chap-3',
          title: '3. .NET Enterprise: C# 12 & ASP.NET Core Clean Architecture',
          sequenceOrder: 3,
          isExpanded: true,
          departmentName: '.NET',
          departmentId: 7,
          lessons: [
            {
              id: 'les-dotnet-1',
              title: 'C# 12 & ASP.NET Core Web API Architecture',
              type: 'video',
              duration: '14:20',
              description: 'Minimal APIs, dependency injection scopes, and Entity Framework Core 8.',
              videoUrl: 'https://storage.googleapis.com/ase-recordings/dotnet-clean-arch.mp4',
              departmentName: '.NET',
              departmentId: 7,
              isPublished: true
            },
            {
              id: 'les-dotnet-2',
              title: 'Resilient Microservices with MediatR, CQRS & Polly',
              type: 'text',
              description: 'Circuit breakers, retry policies, and clean pipeline behaviors in C#.',
              textNotes: 'Use Polly policies for transient fault handling and MediatR pipelines for cross-cutting logging.',
              departmentName: '.NET',
              departmentId: 7,
              isPublished: true
            },
            {
              id: 'les-dotnet-3',
              title: 'Checkpoint Quiz: C# 12 & ASP.NET Core Architecture',
              type: 'quiz',
              quizQuestionsCount: 5,
              description: 'Sprint checkpoint evaluating memory management, async/await, and LINQ performance.',
              departmentName: '.NET',
              departmentId: 7,
              isPublished: true
            }
          ]
        },
        {
          id: 'chap-4',
          title: '4. Java Enterprise: Spring Boot 3 & Virtual Threads',
          sequenceOrder: 4,
          isExpanded: true,
          departmentName: 'Java',
          departmentId: 9,
          lessons: [
            {
              id: 'les-java-1',
              title: 'Modern Java 21: Virtual Threads (Project Loom) & Records',
              type: 'video',
              duration: '15:10',
              description: 'High-concurrency lightweight virtual threads with Spring Boot 3.2.',
              videoUrl: 'https://storage.googleapis.com/ase-recordings/java21-spring3.mp4',
              departmentName: 'Java',
              departmentId: 9,
              isPublished: true
            },
            {
              id: 'les-java-2',
              title: 'Spring Security 6, OAuth2 & JWT Resource Servers',
              type: 'text',
              description: 'Stateless authentication filter chains and method-level authorization.',
              textNotes: 'Configure SecurityFilterChain with stateless session creation and Nimbus JWT decoder.',
              departmentName: 'Java',
              departmentId: 9,
              isPublished: true
            },
            {
              id: 'les-java-3',
              title: 'Checkpoint Quiz: Spring Boot 3 & Java Microservices',
              type: 'quiz',
              quizQuestionsCount: 5,
              description: 'Sprint checkpoint on Spring Data JPA, Hibernate caching, and transaction boundaries.',
              departmentName: 'Java',
              departmentId: 9,
              isPublished: true
            }
          ]
        },
        {
          id: 'chap-5',
          title: '5. Modern PHP: Laravel 11 & High-Volume APIs',
          sequenceOrder: 5,
          isExpanded: true,
          departmentName: 'PHP',
          departmentId: 6,
          lessons: [
            {
              id: 'les-php-1',
              title: 'Modern PHP 8.3 & Laravel 11 Architecture',
              type: 'video',
              duration: '11:50',
              description: 'Strict type safety, Service Container, and Eloquent ORM performance.',
              videoUrl: 'https://storage.googleapis.com/ase-recordings/php-laravel11.mp4',
              departmentName: 'PHP',
              departmentId: 6,
              isPublished: true
            },
            {
              id: 'les-php-2',
              title: 'High-Throughput Queue Workers, Redis & Event Broadcasting',
              type: 'text',
              description: 'Managing asynchronous background jobs and Redis cache tags.',
              textNotes: 'Use Laravel Horizon for queue supervision and Redis cache tags for granular invalidation.',
              departmentName: 'PHP',
              departmentId: 6,
              isPublished: true
            },
            {
              id: 'les-php-3',
              title: 'Checkpoint Quiz: PHP 8.3 & Laravel Clean Architecture',
              type: 'quiz',
              quizQuestionsCount: 5,
              description: 'Sprint checkpoint covering middleware pipelines, Pest testing, and Eloquent optimization.',
              departmentName: 'PHP',
              departmentId: 6,
              isPublished: true
            }
          ]
        },
        {
          id: 'chap-6',
          title: '6. Database Systems: Query Plans, Index Tuning & ACID',
          sequenceOrder: 6,
          isExpanded: true,
          departmentName: 'Database Engineer',
          departmentId: 10,
          lessons: [
            {
              id: 'les-db-1',
              title: 'Deep Dive: Clustered vs Non-Clustered B-Tree Indexes',
              type: 'video',
              duration: '16:30',
              description: 'Physical storage engine internals, page splits, and covering index design.',
              videoUrl: 'https://storage.googleapis.com/ase-recordings/sql-index-deepdive.mp4',
              departmentName: 'Database Engineer',
              departmentId: 10,
              isPublished: true
            },
            {
              id: 'les-db-2',
              title: 'Key Principles of Execution Plans & Deadlock Mitigation',
              type: 'text',
              description: 'Analyzing cost models, table scans, bookmark lookups, and isolation levels.',
              textNotes: 'Index order matters: (tenant_id, created_at) enables prefix range searches while isolating customer records.',
              departmentName: 'Database Engineer',
              departmentId: 10,
              isPublished: true
            },
            {
              id: 'les-db-3',
              title: 'Checkpoint Quiz: Relational Indexing & Concurrency Control',
              type: 'quiz',
              quizQuestionsCount: 5,
              description: 'Sprint checkpoint evaluating query plan analysis, lock escalation, and ACID consistency.',
              departmentName: 'Database Engineer',
              departmentId: 10,
              isPublished: true
            }
          ]
        },
        {
          id: 'chap-7',
          title: '7. Reactive Frontend Architecture & Production Delivery',
          sequenceOrder: 7,
          isExpanded: true,
          departmentName: 'All / Common',
          departmentId: 11,
          lessons: [
            {
              id: 'les-7',
              title: 'Real World Examples: Angular Signals in High-Volume SPAs',
              type: 'video',
              duration: '08:15',
              description: 'Refactoring state services to signals for zero Zone.js overhead.',
              videoUrl: 'https://storage.googleapis.com/ase-recordings/angular-signals-demo.mp4',
              departmentName: 'All / Common',
              departmentId: 11,
              isPublished: true
            },
            {
              id: 'les-8',
              title: 'Practical Case Study: Distributed Cache Invalidation & Telemetry',
              type: 'text',
              description: 'Production war-stories solving cache stampede and OpenTelemetry tracing.',
              textNotes: 'Use probabilistic early expiration (XFetch) or pub/sub cache invalidation over blanket short TTLs.',
              departmentName: 'All / Common',
              departmentId: 11,
              isPublished: true
            },
            {
              id: 'les-9',
              title: 'Live Lab Workshop: Real-Time Telemetry Dashboard',
              type: 'live',
              duration: '2.5 Hours',
              description: 'Interactive live coding session with Lead Trainer Priya Sharma.',
              departmentName: 'All / Common',
              departmentId: 11,
              isPublished: true
            },
            {
              id: 'les-10',
              title: 'Assignment 3: Reactive State Management Implementation',
              type: 'assignment',
              description: 'Build a signal-driven monitoring module with unit tests.',
              departmentName: 'All / Common',
              departmentId: 11,
              isPublished: true
            }
          ]
        }
      ],

      // Screenshot 5: Training Schedule & Live Sessions (Live Today, Upcoming & Completed for all Departments)
      sessions: [],

      // Screenshot 4: Teacher Interactive Attendance Matrix
      attendanceMatrix: {
        dateRangeLabel: '27 Oct - 09 Nov 2026',
        days: [
          { dateStr: '2026-10-27', dayLetter: 'M', dateNum: '27' },
          { dateStr: '2026-10-28', dayLetter: 'T', dateNum: '28' },
          { dateStr: '2026-10-29', dayLetter: 'W', dateNum: '29' },
          { dateStr: '2026-10-30', dayLetter: 'T', dateNum: '30' },
          { dateStr: '2026-10-31', dayLetter: 'F', dateNum: '31' },
          { dateStr: '2026-11-01', dayLetter: 'S', dateNum: '01', isWeekend: true },
          { dateStr: '2026-11-02', dayLetter: 'S', dateNum: '02', isWeekend: true },
          { dateStr: '2026-11-03', dayLetter: 'M', dateNum: '03' },
          { dateStr: '2026-11-04', dayLetter: 'T', dateNum: '04' },
          { dateStr: '2026-11-05', dayLetter: 'W', dateNum: '05' },
          { dateStr: '2026-11-06', dayLetter: 'T', dateNum: '06' },
          { dateStr: '2026-11-07', dayLetter: 'F', dateNum: '07' },
          { dateStr: '2026-11-08', dayLetter: 'S', dateNum: '08', isWeekend: true },
          { dateStr: '2026-11-09', dayLetter: 'S', dateNum: '09', isWeekend: true }
        ],
        students: [
          {
            studentId: 'std-1',
            admissionNo: 'SKL/2024/0182',
            name: 'Aarav Sharma',
            absCount: 1,
            lveCount: 0,
            dailyStatus: {
              '2026-10-27': 'P', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'A', '2026-10-31': 'P',
              '2026-11-01': 'H', '2026-11-02': 'H',
              '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
              '2026-11-08': 'H', '2026-11-09': 'H'
            }
          },
          {
            studentId: 'std-2',
            admissionNo: 'SKL/2023/0094',
            name: 'Diya Verma',
            absCount: 0,
            lveCount: 0,
            dailyStatus: {
              '2026-10-27': 'P', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'P',
              '2026-11-01': 'H', '2026-11-02': 'H',
              '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
              '2026-11-08': 'H', '2026-11-09': 'H'
            }
          },
          {
            studentId: 'std-3',
            admissionNo: 'SKL/2025/0247',
            name: 'Ishaan Patel',
            absCount: 3,
            lveCount: 0,
            dailyStatus: {
              '2026-10-27': 'P', '2026-10-28': 'A', '2026-10-29': 'A', '2026-10-30': 'A', '2026-10-31': 'P',
              '2026-11-01': 'H', '2026-11-02': 'H',
              '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
              '2026-11-08': 'H', '2026-11-09': 'H'
            }
          },
          {
            studentId: 'std-4',
            admissionNo: 'SKL/2022/0038',
            name: 'Ananya Kapoor',
            absCount: 2,
            lveCount: 0,
            dailyStatus: {
              '2026-10-27': 'P', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'P',
              '2026-11-01': 'H', '2026-11-02': 'H',
              '2026-11-03': 'P', '2026-11-04': 'A', '2026-11-05': 'A', '2026-11-06': 'P', '2026-11-07': 'P',
              '2026-11-08': 'H', '2026-11-09': 'H'
            }
          },
          {
            studentId: 'std-5',
            admissionNo: 'SKL/2024/0163',
            name: 'Vihaan Rao',
            absCount: 0,
            lveCount: 0,
            dailyStatus: {
              '2026-10-27': 'P', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'P',
              '2026-11-01': 'H', '2026-11-02': 'H',
              '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
              '2026-11-08': 'H', '2026-11-09': 'H'
            }
          },
          {
            studentId: 'std-6',
            admissionNo: 'SKL/2026/0312',
            name: 'Saanvi Mehta',
            absCount: 2,
            lveCount: 0,
            dailyStatus: {
              '2026-10-27': 'P', '2026-10-28': 'A', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'A',
              '2026-11-01': 'H', '2026-11-02': 'H',
              '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
              '2026-11-08': 'H', '2026-11-09': 'H'
            }
          },
          {
            studentId: 'std-7',
            admissionNo: 'SKL/2021/0021',
            name: 'Rohan Iyer',
            absCount: 3,
            lveCount: 0,
            dailyStatus: {
              '2026-10-27': 'P', '2026-10-28': 'A', '2026-10-29': 'A', '2026-10-30': 'A', '2026-10-31': 'P',
              '2026-11-01': 'H', '2026-11-02': 'H',
              '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
              '2026-11-08': 'H', '2026-11-09': 'H'
            }
          },
          {
            studentId: 'std-8',
            admissionNo: 'SKL/2025/0271',
            name: 'Myra Joshi',
            absCount: 1,
            lveCount: 0,
            dailyStatus: {
              '2026-10-27': 'A', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'P',
              '2026-11-01': 'H', '2026-11-02': 'H',
              '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'P', '2026-11-07': 'P',
              '2026-11-08': 'H', '2026-11-09': 'H'
            }
          },
          {
            studentId: 'std-9',
            admissionNo: 'SKL/2026/0401',
            name: 'Rahul Pandey',
            absCount: 0,
            lveCount: 1,
            dailyStatus: {
              '2026-10-27': 'P', '2026-10-28': 'P', '2026-10-29': 'P', '2026-10-30': 'P', '2026-10-31': 'P',
              '2026-11-01': 'H', '2026-11-02': 'H',
              '2026-11-03': 'P', '2026-11-04': 'P', '2026-11-05': 'P', '2026-11-06': 'L', '2026-11-07': 'P',
              '2026-11-08': 'H', '2026-11-09': 'H'
            }
          }
        ]
      },

      materials: [
        // --- ALL / COMMON MATERIALS ---
        {
          id: 'mat-1',
          title: 'Angular Signals & Reactive State Architecture Slide Deck',
          module: 'Module 3: Frontend Mastery',
          type: 'slides',
          size: '4.8 MB',
          uploadedAt: 'Yesterday',
          author: 'Priya Sharma (Staff Engineer)',
          downloadUrl: '#',
          description: 'Official slide presentation covering signal primitives, equality functions, reactive effects, and performance benchmarks.',
          departmentName: 'All / Common',
          departmentId: 11,
          isBookmarked: true
        },
        {
          id: 'mat-4',
          title: 'Microservices Design Patterns: Sagas, CQRS & Outbox Handout',
          module: 'Module 1: Architecture Foundations',
          type: 'pdf',
          size: '2.4 MB (PDF)',
          uploadedAt: '2 weeks ago',
          author: 'Vikram Joshi (Senior Architect)',
          downloadUrl: '#',
          description: 'Architectural blueprints explaining dual writes prevention, transactional outbox pattern, and distributed event streaming.',
          departmentName: 'All / Common',
          departmentId: 11
        },
        {
          id: 'mat-5',
          title: 'Full Video Walkthrough: Setting Up Docker Multi-Stage Builds',
          module: 'Module 4: Systems & Cloud',
          type: 'video',
          size: '45 mins (1080p HD)',
          uploadedAt: '4 days ago',
          author: 'Vikram Joshi (Senior Architect)',
          downloadUrl: 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4',
          videoUrl: 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4',
          description: '45-minute screencast demonstrating minimal distroless Docker images for enterprise microservices.',
          departmentName: 'All / Common',
          departmentId: 11
        },

        // --- PYTHON MATERIALS ---
        {
          id: 'mat-2',
          title: 'FastAPI Production Starter Kit & Clean Architecture Repo',
          module: 'Module 2: Microservices Backend',
          type: 'code',
          size: '1.2 MB (ZIP)',
          uploadedAt: '3 days ago',
          author: 'Priya Sharma (Staff Engineer)',
          downloadUrl: '#',
          description: 'Ready-to-use repository template with Alembic migrations, SQLAlchemy 2 async session, pytest fixtures, and Docker Compose.',
          departmentName: 'Python',
          departmentId: 8,
          isBookmarked: true
        },
        {
          id: 'mat-py-pdf',
          title: 'Python AsyncIO, Celery & Pydantic v2 Architectural Cheat Sheet',
          module: 'Module 2: Microservices Backend',
          type: 'cheatsheet',
          size: '1.1 MB (PDF)',
          uploadedAt: '2 days ago',
          author: 'Priya Sharma (Staff Engineer)',
          downloadUrl: '#',
          description: 'Summary guide of async context managers, connection pool tuning, Celery retry hooks, and Pydantic validation rules.',
          departmentName: 'Python',
          departmentId: 8
        },
        {
          id: 'mat-py-video',
          title: 'Lecture Video: Building High-Throughput APIs with FastAPI & AsyncIO',
          module: 'Module 2: Microservices Backend',
          type: 'video',
          size: '38 mins (1080p HD)',
          uploadedAt: 'Yesterday',
          author: 'Priya Sharma (Staff Engineer)',
          downloadUrl: 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4',
          videoUrl: 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4',
          description: 'Full video walkthrough decoupling router controllers from data access using dependency injection.',
          departmentName: 'Python',
          departmentId: 8
        },

        // --- .NET MATERIALS ---
        {
          id: 'mat-dotnet',
          title: 'ASP.NET Core Clean Architecture & MediatR Blueprint',
          module: 'Module 2: Microservices Backend',
          type: 'pdf',
          size: '3.1 MB (PDF)',
          uploadedAt: '2 days ago',
          author: 'Vikram Joshi (Senior Architect)',
          downloadUrl: '#',
          description: 'Production blueprint for C# 12 Minimal APIs, CQRS, MediatR, and Polly fault resilience.',
          departmentName: '.NET',
          departmentId: 7,
          isBookmarked: true
        },
        {
          id: 'mat-dotnet-code',
          title: 'C# 12 Minimal APIs & Entity Framework Core 8 Starter Repository',
          module: 'Module 2: Microservices Backend',
          type: 'code',
          size: '2.5 MB (ZIP)',
          uploadedAt: '3 days ago',
          author: 'Vikram Joshi (Senior Architect)',
          downloadUrl: '#',
          description: 'Enterprise solution structure with Domain, Application, Infrastructure, and WebApi projects plus xUnit test suites.',
          departmentName: '.NET',
          departmentId: 7
        },
        {
          id: 'mat-dotnet-video',
          title: 'Lecture Video: Entity Framework Core 8 Performance Tuning & Split Queries',
          module: 'Module 2: Microservices Backend',
          type: 'video',
          size: '42 mins (1080p HD)',
          uploadedAt: '3 days ago',
          author: 'Vikram Joshi (Senior Architect)',
          downloadUrl: 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4',
          videoUrl: 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4',
          description: 'Deep dive into AsNoTracking, compiled queries, and avoiding Cartesian explosions.',
          departmentName: '.NET',
          departmentId: 7
        },

        // --- JAVA MATERIALS ---
        {
          id: 'mat-java',
          title: 'Spring Boot 3 Microservices & Virtual Threads Blueprint',
          module: 'Module 2: Microservices Backend',
          type: 'pdf',
          size: '3.6 MB (PDF)',
          uploadedAt: '3 days ago',
          author: 'Ananya Roy (Principal Engineer)',
          downloadUrl: '#',
          description: 'Guide to high-concurrency Java 21, Project Loom virtual threads, and Spring Security 6.',
          departmentName: 'Java',
          departmentId: 9,
          isBookmarked: true
        },
        {
          id: 'mat-java-code',
          title: 'Java 21 Spring Boot 3.2 Microservice Starter Kit',
          module: 'Module 2: Microservices Backend',
          type: 'code',
          size: '1.8 MB (ZIP)',
          uploadedAt: '4 days ago',
          author: 'Ananya Roy (Principal Engineer)',
          downloadUrl: '#',
          description: 'Maven/Gradle starter template with virtual thread configuration, JPA repositories, and Testcontainers.',
          departmentName: 'Java',
          departmentId: 9
        },
        {
          id: 'mat-java-video',
          title: 'Lecture Video: Stateless OAuth2 & JWT Security in Spring Security 6',
          module: 'Module 2: Microservices Backend',
          type: 'video',
          size: '35 mins (1080p HD)',
          uploadedAt: '4 days ago',
          author: 'Ananya Roy (Principal Engineer)',
          downloadUrl: 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4',
          videoUrl: 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4',
          description: 'Hands-on architectural setup of Nimbus JWT decoders and role-based authority mapping.',
          departmentName: 'Java',
          departmentId: 9
        },

        // --- PHP MATERIALS ---
        {
          id: 'mat-php',
          title: 'Modern PHP 8.3 & Laravel 11 Microservices Guidebook',
          module: 'Module 2: Microservices Backend',
          type: 'slides',
          size: '2.9 MB',
          uploadedAt: '4 days ago',
          author: 'Priya Sharma (Staff Engineer)',
          downloadUrl: '#',
          description: 'Enterprise Laravel 11 architecture, Redis job queues, and high-performance API design.',
          departmentName: 'PHP',
          departmentId: 6,
          isBookmarked: true
        },
        {
          id: 'mat-php-code',
          title: 'Laravel 11 Enterprise REST API & Horizon Queue Worker Starter',
          module: 'Module 2: Microservices Backend',
          type: 'code',
          size: '1.4 MB (ZIP)',
          uploadedAt: '5 days ago',
          author: 'Priya Sharma (Staff Engineer)',
          downloadUrl: '#',
          description: 'Composer project skeleton with Pest 3 test suite, Sanctum auth, and Redis Horizon workers.',
          departmentName: 'PHP',
          departmentId: 6
        },
        {
          id: 'mat-php-video',
          title: 'Lecture Video: High-Throughput Queue Processing with Laravel Horizon',
          module: 'Module 2: Microservices Backend',
          type: 'video',
          size: '40 mins (1080p HD)',
          uploadedAt: '5 days ago',
          author: 'Priya Sharma (Staff Engineer)',
          downloadUrl: 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4',
          videoUrl: 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4',
          description: 'Configuring supervisor workers, metrics monitoring, and handling failed job replays.',
          departmentName: 'PHP',
          departmentId: 6
        },

        // --- DATABASE ENGINEER MATERIALS ---
        {
          id: 'mat-3',
          title: 'PostgreSQL & SQL Server Query Optimization & Indexing Cheat Sheet',
          module: 'Module 2: Database Systems',
          type: 'cheatsheet',
          size: '850 KB (PDF)',
          uploadedAt: '1 week ago',
          author: 'Vikram Joshi (Senior Architect)',
          downloadUrl: '#',
          description: 'Quick-reference guide for reading execution plan cost models, index column order, and lock contention.',
          departmentName: 'Database Engineer',
          departmentId: 10,
          isBookmarked: true
        },
        {
          id: 'mat-db-code',
          title: 'SQL Performance Benchmark & Execution Plan Analysis Tooling',
          module: 'Module 2: Database Systems',
          type: 'code',
          size: '950 KB (ZIP)',
          uploadedAt: '4 days ago',
          author: 'Vikram Joshi (Senior Architect)',
          downloadUrl: '#',
          description: 'Automated DDL scripts, sample 10M-row datasets, index creation benchmarks, and deadlock traces.',
          departmentName: 'Database Engineer',
          departmentId: 10
        },
        {
          id: 'mat-db-video',
          title: 'Lecture Video: Deep Dive into Graphical Execution Plans & Index B-Trees',
          module: 'Module 2: Database Systems',
          type: 'video',
          size: '50 mins (1080p HD)',
          uploadedAt: '3 days ago',
          author: 'Vikram Joshi (Senior Architect)',
          downloadUrl: 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4',
          videoUrl: 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4',
          description: 'Analyzing physical database operators, table scans, bookmark lookups, and plan caching behavior.',
          departmentName: 'Database Engineer',
          departmentId: 10
        }
      ],

      assignments: [
        // --- PYTHON ASSIGNMENTS ---
        {
          id: 'asg-1',
          title: 'Assignment 1: Distributed Caching & Redis Integration',
          module: 'Module 2: Microservices Backend',
          description: 'Implement a resilient distributed caching layer for the Product Catalog microservice with cache-aside pattern, TTL jitter, and transactional invalidation.',
          points: 100,
          dueDate: '2026-10-28',
          dueRelative: 'Completed & Graded',
          status: 'graded',
          submissionDate: '2026-10-27T18:30:00Z',
          submissionUrl: 'https://github.com/learner/ase-distributed-caching',
          submissionNotes: 'Implemented Redis connection pooling, connection retry with exponential backoff, and unit tests covering cache miss/hit scenarios.',
          score: 95,
          trainerFeedback: 'Exceptional submission! Your cache stampede prevention using probabilistic early expiration was a brilliant architectural touch.',
          departmentName: 'Python',
          departmentId: 8,
          requirements: [
            'Cache-aside read/write implementation with Redis',
            'Cache invalidation hook on product mutation',
            'Minimum 90% unit test coverage with pytest-mock',
            'Graceful degradation when Redis cluster is unreachable'
          ]
        },
        {
          id: 'asg-py-pending',
          title: 'Assignment 2: FastAPI Microservices with Asynchronous Celery & RabbitMQ',
          module: 'Module 2: Microservices Backend',
          description: 'Design and deploy asynchronous queue workers handling transactional email dispatch, image processing, and event ingestion.',
          points: 100,
          dueDate: '2026-11-15',
          dueRelative: 'Due in 3 days',
          status: 'pending',
          departmentName: 'Python',
          departmentId: 8,
          requirements: [
            'FastAPI background task decoupling with Celery',
            'RabbitMQ message persistence and dead-letter exchanges',
            'Structured logging with correlation IDs on every task'
          ]
        },
        {
          id: 'asg-py-submitted',
          title: 'Assignment 3: Alembic Database Migrations & SQLAlchemy 2 Async Engine',
          module: 'Module 2: Microservices Backend',
          description: 'Construct idempotent migration scripts and asynchronous database session fixtures for high-throughput concurrency.',
          points: 100,
          dueDate: '2026-11-05',
          dueRelative: 'Submitted — Under Review',
          status: 'submitted',
          submissionDate: '2026-11-04T16:20:00Z',
          submissionUrl: 'https://github.com/learner/ase-fastapi-alembic-models',
          submissionNotes: 'Completed async sessions, relationship eager loading with selectinload, and rollback handlers.',
          trainerFeedback: 'Submission received. Instructor Priya Sharma is currently conducting code review.',
          departmentName: 'Python',
          departmentId: 8,
          requirements: [
            'Asyncpg driver with pooled connections',
            'Alembic auto-generation checks against schema drifts',
            'Pytest suite with transaction rollback after each test'
          ]
        },

        // --- .NET ASSIGNMENTS ---
        {
          id: 'asg-dotnet',
          title: 'Assignment: ASP.NET Core Clean Architecture Web API',
          module: 'Module 2: Microservices Backend',
          description: 'Build a C# 12 ASP.NET Core Web API with MediatR CQRS handlers, FluentValidation, and Entity Framework Core repository patterns.',
          points: 100,
          dueDate: '2026-11-04',
          dueRelative: 'Due soon',
          status: 'pending',
          departmentName: '.NET',
          departmentId: 7,
          requirements: [
            'Clean Architecture project layers (Domain, Application, Infrastructure, API)',
            'MediatR pipeline behaviors for validation and logging',
            'Unit and integration tests with xUnit and WebApplicationFactory'
          ]
        },
        {
          id: 'asg-dotnet-graded',
          title: 'Assignment: MediatR Pipeline Behaviors & FluentValidation Rules',
          module: 'Module 2: Microservices Backend',
          description: 'Construct clean cross-cutting pipelines for incoming command payloads, timing telemetry, and validation failure interception.',
          points: 100,
          dueDate: '2026-10-25',
          dueRelative: 'Completed & Graded',
          status: 'graded',
          submissionDate: '2026-10-24T20:10:00Z',
          submissionUrl: 'https://github.com/learner/ase-dotnet-mediatr-cqrs',
          score: 92,
          trainerFeedback: 'Clean and elegant MediatR pipeline setup. Excellent separation between domain rules and HTTP controllers.',
          departmentName: '.NET',
          departmentId: 7,
          requirements: [
            'Generic IPipelineBehavior for performance logging',
            'FluentValidation automatic registration with dependency injection',
            'Custom ValidationException problem details mapping'
          ]
        },
        {
          id: 'asg-dotnet-sub',
          title: 'Assignment: Entity Framework Core 8 Split Queries & Compiled Models',
          module: 'Module 2: Microservices Backend',
          description: 'Benchmark EF Core 8 queries against SQL Server, implement compiled models, and prevent Cartesian product degradation.',
          points: 100,
          dueDate: '2026-11-08',
          dueRelative: 'Submitted — Under Review',
          status: 'submitted',
          submissionDate: '2026-11-07T14:45:00Z',
          submissionUrl: 'https://github.com/learner/ase-dotnet-efcore-tuning',
          trainerFeedback: 'Under review by Senior Architect Vikram Joshi.',
          departmentName: '.NET',
          departmentId: 7,
          requirements: [
            'AsSplitQuery configuration on deep 1-to-many relationship queries',
            'EF Core SaveChangesAsync interceptors for audit logging',
            'BenchmarkDotNet comparison report'
          ]
        },

        // --- JAVA ASSIGNMENTS ---
        {
          id: 'asg-java',
          title: 'Assignment: Spring Boot 3 Microservices Integration',
          module: 'Module 2: Microservices Backend',
          description: 'Develop a Spring Boot 3 microservice utilizing Java 21 Virtual Threads, Spring Data JPA, and Resilience4j circuit breakers.',
          points: 100,
          dueDate: '2026-11-06',
          dueRelative: 'Due in 2 days',
          status: 'pending',
          departmentName: 'Java',
          departmentId: 9,
          requirements: [
            'Spring Boot 3.2+ with virtual thread executor configuration',
            'Spring Security 6 stateless JWT authentication',
            'MockMvc integration test suite with Testcontainers'
          ]
        },
        {
          id: 'asg-java-graded',
          title: 'Assignment: Spring Security 6 Stateless OAuth2 Resource Server',
          module: 'Module 2: Microservices Backend',
          description: 'Build a secure API gateway microservice verifying asymmetric RSA tokens with custom GrantedAuthoritiesExtractor.',
          points: 100,
          dueDate: '2026-10-26',
          dueRelative: 'Completed & Graded',
          status: 'graded',
          submissionDate: '2026-10-25T17:30:00Z',
          submissionUrl: 'https://github.com/learner/ase-java-spring-security6',
          score: 91,
          trainerFeedback: 'Very robust JWT validation and method security. Good handling of expired token responses.',
          departmentName: 'Java',
          departmentId: 9,
          requirements: [
            'Stateless SecurityFilterChain configuration',
            'NimbusJwtDecoder with JWK Set URI',
            'Integration tests simulating valid and expired bearer tokens'
          ]
        },
        {
          id: 'asg-java-sub',
          title: 'Assignment: Project Loom Virtual Threads Concurrency Benchmark',
          module: 'Module 2: Microservices Backend',
          description: 'Create an asynchronous batch ingestion engine comparing platform carrier threads against Java 21 Virtual Threads under 10k concurrent tasks.',
          points: 100,
          dueDate: '2026-11-09',
          dueRelative: 'Submitted — Under Review',
          status: 'submitted',
          submissionDate: '2026-11-08T18:10:00Z',
          submissionUrl: 'https://github.com/learner/ase-java-loom-benchmark',
          trainerFeedback: 'Under review by Principal Engineer Ananya Roy.',
          departmentName: 'Java',
          departmentId: 9,
          requirements: [
            'StructuredTaskScope for coordinated parallel subtasks',
            'Pinning diagnostics check with -Djdk.tracePinnedThreads=full',
            'Throughput and memory footprint comparative charts'
          ]
        },

        // --- PHP ASSIGNMENTS ---
        {
          id: 'asg-php',
          title: 'Assignment: Laravel 11 RESTful Service with Pest Tests',
          module: 'Module 2: Microservices Backend',
          description: 'Implement a high-throughput REST API using Laravel 11, asynchronous Redis queues, and comprehensive Pest 3 unit/feature tests.',
          points: 100,
          dueDate: '2026-11-08',
          dueRelative: 'Due in 4 days',
          status: 'pending',
          departmentName: 'PHP',
          departmentId: 6,
          requirements: [
            'Form Request validation with custom rules',
            'Queued jobs with exponential retry for external notifications',
            'Pest 3 feature tests with 85%+ code coverage'
          ]
        },
        {
          id: 'asg-php-graded',
          title: 'Assignment: Asynchronous Queue Workers & Redis Optimization',
          module: 'Module 2: Microservices Backend',
          description: 'Deploy Laravel Horizon supervisors, configure failed job dead-letter pruning, and manage atomic locks in Redis.',
          points: 100,
          dueDate: '2026-10-27',
          dueRelative: 'Completed & Graded',
          status: 'graded',
          submissionDate: '2026-10-26T19:00:00Z',
          submissionUrl: 'https://github.com/learner/ase-laravel-horizon-queues',
          score: 94,
          trainerFeedback: 'Superb queue configuration! The auto-scaling worker threshold based on queue wait time was spot on.',
          departmentName: 'PHP',
          departmentId: 6,
          requirements: [
            'Horizon config balancing queue priority',
            'Redis::throttle() rate limiting on external payment webhooks',
            'Pest tests with Queue::fake() assertion assertions'
          ]
        },
        {
          id: 'asg-php-sub',
          title: 'Assignment: Eloquent Repository Pattern with Multi-Tenancy Scopes',
          module: 'Module 2: Microservices Backend',
          description: 'Design global tenant query scopes and repository interfaces ensuring strict data isolation across accounts.',
          points: 100,
          dueDate: '2026-11-10',
          dueRelative: 'Submitted — Under Review',
          status: 'submitted',
          submissionDate: '2026-11-09T15:20:00Z',
          submissionUrl: 'https://github.com/learner/ase-laravel-multitenancy',
          trainerFeedback: 'Under review by Staff Engineer Priya Sharma.',
          departmentName: 'PHP',
          departmentId: 6,
          requirements: [
            'Global Scope automatically filtering by tenant_id',
            'Custom Artisan command for tenant schema migrations',
            'Unit tests asserting cross-tenant data leakage prevention'
          ]
        },

        // --- DATABASE ENGINEER ASSIGNMENTS ---
        {
          id: 'asg-db',
          title: 'Assignment: High-Volume Database Index Optimization & Benchmark',
          module: 'Module 2: Database Systems',
          description: 'Analyze slow query logs, generate execution plans, design composite covering indexes, and verify performance improvements.',
          points: 100,
          dueDate: '2026-11-10',
          dueRelative: 'Due in 6 days',
          status: 'pending',
          departmentName: 'Database Engineer',
          departmentId: 10,
          requirements: [
            'Identify table scan bottlenecks using EXPLAIN ANALYZE',
            'Construct covering indexes eliminating key lookups',
            'Demonstrate 5x+ throughput improvement in benchmark report'
          ]
        },
        {
          id: 'asg-db-graded',
          title: 'Assignment: Deadlock Analysis & Snapshot Isolation Architecture',
          module: 'Module 2: Database Systems',
          description: 'Reproduce concurrent lock escalation scenarios, capture XML deadlock graphs, and refactor transaction ordering.',
          points: 100,
          dueDate: '2026-10-29',
          dueRelative: 'Completed & Graded',
          status: 'graded',
          submissionDate: '2026-10-28T21:15:00Z',
          submissionUrl: 'https://github.com/learner/ase-db-deadlock-mitigation',
          score: 96,
          trainerFeedback: 'Outstanding deadlock resolution analysis! Enabling RCSI with proper index hints solved the concurrent contention cleanly.',
          departmentName: 'Database Engineer',
          departmentId: 10,
          requirements: [
            'Simulate concurrent conflicting transactions in test harness',
            'Extract deadlock graphs using Extended Events session',
            'Implement Read Committed Snapshot Isolation (RCSI) with benchmark'
          ]
        },
        {
          id: 'asg-db-sub',
          title: 'Assignment: Sliding-Window Table Partitioning & Columnstore Indexes',
          module: 'Module 2: Database Systems',
          description: 'Implement monthly sliding-window partitions on a 50-million-row telemetry table with Clustered Columnstore archiving.',
          points: 100,
          dueDate: '2026-11-11',
          dueRelative: 'Submitted — Under Review',
          status: 'submitted',
          submissionDate: '2026-11-10T12:00:00Z',
          submissionUrl: 'https://github.com/learner/ase-db-partitioning-columnstore',
          trainerFeedback: 'Under review by Senior Architect Vikram Joshi.',
          departmentName: 'Database Engineer',
          departmentId: 10,
          requirements: [
            'Partition function and partition scheme with date ranges',
            'SWITCH PARTITION staging scripts for zero-downtime data archiving',
            'Query performance comparison before and after partitioning'
          ]
        },

        // --- ALL / COMMON ASSIGNMENTS ---
        {
          id: 'asg-3',
          title: 'Assignment 3: Reactive State Management with Angular Signals',
          module: 'Module 3: Frontend Mastery',
          description: 'Build an interactive dashboard module that consumes real-time telemetry updates using Angular 17+ Signals, computed metrics, and clean component decomposition.',
          points: 100,
          dueDate: '2026-11-12',
          dueRelative: 'Due in 8 days',
          status: 'submitted',
          submissionDate: '2026-11-04T19:40:00Z',
          submissionUrl: 'https://github.com/learner/ase-angular-telemetry-dashboard',
          submissionNotes: 'Completed all core criteria: signal stores, computed summaries, offline fallback, and 0 zone.js overhead.',
          trainerFeedback: 'Submission received and currently under review by Priya Sharma.',
          departmentName: 'All / Common',
          departmentId: 11,
          requirements: [
            'Use Angular standalone components and Signals exclusively',
            'Reactive search input with debounce and distinctUntilChanged',
            'Optimistic mutation with rollback on API failure',
            'Responsive design tested on desktop and mobile viewports'
          ]
        },
        {
          id: 'asg-4',
          title: 'Assignment 4: Microservice Containerization & CI/CD GitHub Actions',
          module: 'Module 4: Systems & Cloud',
          description: 'Create multi-stage production Dockerfiles, compose setups with healthchecks, and a GitHub Actions workflow that executes linting, tests, and security scans on PRs.',
          points: 100,
          dueDate: '2026-11-14',
          dueRelative: 'Due in 10 days',
          status: 'pending',
          departmentName: 'All / Common',
          departmentId: 11,
          requirements: [
            'Multi-stage Dockerfile producing < 100MB container',
            'Non-root user execution inside container',
            'Docker Compose with healthcheck dependency ordering',
            'GitHub Actions pipeline with caching and test reporting'
          ]
        },
        {
          id: 'asg-common-graded',
          title: 'Assignment 0: Git Flow, Code Review & Architectural Standards',
          module: 'Module 1: Architecture Foundations',
          description: 'Demonstrate trunk-based branching, conventional commit messages, pre-commit hooks, and peer code review standards.',
          points: 100,
          dueDate: '2026-10-20',
          dueRelative: 'Completed & Graded',
          status: 'graded',
          submissionDate: '2026-10-19T14:10:00Z',
          submissionUrl: 'https://github.com/learner/ase-git-standards',
          score: 98,
          trainerFeedback: 'Exemplary git hygiene and thorough review feedback provided to squad teammates.',
          departmentName: 'All / Common',
          departmentId: 11,
          requirements: [
            'Configure Husky pre-commit hooks with commitlint',
            'Open PR with conventional semantic commits (feat, fix, docs)',
            'Conduct constructive line-by-line review on squad peer PR'
          ]
        }
      ],

      attendance: {
        percentage: 94,
        totalSessions: 17,
        attended: 16,
        missed: 1,
        excused: 1,
        late: 0,
        minimumRequired: 85,
        checkedInToday: true,
        history: [
          {
            sessionId: 'sess-today',
            sessionTitle: 'Angular Signals & Reactive State Architecture',
            date: 'Today, Nov 05',
            status: 'present',
            recordedAt: '10:02 AM IST',
            recordedBy: 'Auto Check-in & Priya Sharma'
          },
          {
            sessionId: 'sess-4',
            sessionTitle: 'FastAPI Clean Architecture & Dependency Injection',
            date: 'Nov 03, 2026',
            status: 'present',
            recordedAt: '10:00 AM IST',
            recordedBy: 'Priya Sharma'
          },
          {
            sessionId: 'sess-5',
            sessionTitle: 'SQL Mastery: Execution Plans & Index Tuning',
            date: 'Oct 31, 2026',
            status: 'present',
            recordedAt: '10:01 AM IST',
            recordedBy: 'Vikram Joshi'
          },
          {
            sessionId: 'sess-prev-1',
            sessionTitle: 'Asyncio Event Loops & Network I/O Internals',
            date: 'Oct 28, 2026',
            status: 'present',
            recordedAt: '10:05 AM IST',
            recordedBy: 'Priya Sharma'
          },
          {
            sessionId: 'sess-prev-2',
            sessionTitle: 'Unit Testing Strategies & Mocking Best Practices',
            date: 'Oct 26, 2026',
            status: 'excused',
            recordedAt: 'Prior Approval',
            recordedBy: 'Academic Coordinator'
          },
          {
            sessionId: 'sess-prev-3',
            sessionTitle: 'SOLID Principles in Modern Backend Development',
            date: 'Oct 24, 2026',
            status: 'present',
            recordedAt: '09:59 AM IST',
            recordedBy: 'Priya Sharma'
          }
        ]
      },

      quizzes: [
        // --- ALL / COMMON QUIZZES ---
        {
          id: 'quiz-common-0',
          title: 'Sprint 0: Engineering Onboarding & Clean Code Standards',
          module: 'Module 1: Architecture Foundations',
          questionsCount: 5,
          durationMinutes: 10,
          dueDate: 'Oct 18, 2026',
          passingScore: 70,
          status: 'completed',
          score: 100,
          passed: true,
          completedAt: '2026-10-18T14:00:00Z',
          departmentName: 'All / Common',
          departmentId: 11,
          questions: [
            {
              id: 1,
              text: 'According to SOLID principles, what is the core mandate of the Single Responsibility Principle (SRP)?',
              options: [
                'A class should have only one reason to change, encapsulating a single cohesive responsibility',
                'A function should never exceed 10 lines of code',
                'Every database table must map to exactly one model class',
                'All APIs must be RESTful'
              ],
              correctIndex: 0,
              explanation: 'SRP states that a software module should be responsible to one, and only one, actor or business reason to change.'
            },
            {
              id: 2,
              text: 'What is the primary benefit of Trunk-Based Development over long-lived feature branches?',
              options: [
                'It avoids merge hell by integrating small, atomic commits frequently into the mainline',
                'It completely eliminates the need for unit testing',
                'It allows developers to commit without compiling',
                'It bypasses code review'
              ],
              correctIndex: 0,
              explanation: 'Trunk-based development encourages frequent small merges into trunk, drastically lowering merge conflicts and accelerating CI/CD velocity.'
            },
            {
              id: 3,
              text: 'What distinguishes Dependency Injection (DI) from the Service Locator anti-pattern?',
              options: [
                'DI explicitly declares dependencies in constructors, while Service Locator hides dependencies behind a global registry',
                'DI only works with Java',
                'Service Locator is faster in all scenarios',
                'DI requires global mutable variables'
              ],
              correctIndex: 0,
              explanation: 'Constructor DI makes dependencies explicit and testable, whereas Service Locator obscures dependencies and complicates unit testing.'
            },
            {
              id: 4,
              text: 'In conventional commit messages, what does a commit titled "feat(auth): add JWT refresh endpoint" communicate?',
              options: [
                'A new user-facing feature in the auth scope adding a JWT refresh endpoint',
                'A bug fix in the database',
                'A documentation change',
                'A CI/CD script update'
              ],
              correctIndex: 0,
              explanation: '"feat" signals a new capability, while the scope "(auth)" defines the affected module in the semantic changelog.'
            },
            {
              id: 5,
              text: 'Why should sensitive secrets (passwords, JWT signing keys) never be committed to source code repositories?',
              options: [
                'Git history permanently preserves committed files even if deleted in a later commit, creating severe credential leaks',
                'Secrets make git push commands 10x slower',
                'Compilers reject files containing passwords',
                'Git cannot track files with alphanumeric strings'
              ],
              correctIndex: 0,
              explanation: 'Committed secrets remain in Git packfiles and commit history forever unless purged via history rewriting, risking credential compromise.'
            }
          ]
        },
        {
          id: 'quiz-3',
          title: 'Sprint 3 Checkpoint: Angular Signals & Modern Frontend',
          module: 'Module 3: Frontend Mastery',
          questionsCount: 5,
          durationMinutes: 10,
          dueDate: 'Nov 09, 2026',
          passingScore: 70,
          status: 'available',
          departmentName: 'All / Common',
          departmentId: 11,
          questions: [
            {
              id: 1,
              text: 'What is the primary advantage of Angular Signals over traditional Zone.js-based change detection?',
              options: [
                'Signals eliminate the need for TypeScript interfaces entirely',
                'Signals provide fine-grained reactivity, notifying only the specific views that read the changed signal',
                'Signals force every component in the tree to re-render simultaneously',
                'Signals replace CSS styling with programmatic animations'
              ],
              correctIndex: 1,
              explanation: 'Angular Signals track exact data dependencies at runtime. When a signal updates, only the precise DOM nodes or computations that read it are recalculated, eliminating coarse-grained tree traversals.'
            },
            {
              id: 2,
              text: 'Which function should be used to create a read-only signal derived from one or more other signals?',
              options: [
                'computed()',
                'effect()',
                'signal.mutate()',
                'derivedStore()'
              ],
              correctIndex: 0,
              explanation: 'computed() creates a memoized read-only signal whose value is derived from other signals and only re-evaluates when its dependencies change.'
            },
            {
              id: 3,
              text: 'When should an effect() be utilized in an Angular application?',
              options: [
                'To transform state before rendering in a template',
                'To perform side effects such as logging, analytics, or syncing with external browser APIs',
                'To define HTTP route handlers inside the router',
                'To declare dependency injection providers inside main.ts'
              ],
              correctIndex: 1,
              explanation: 'effects are designed for side-effect operations that need to react to signal changes (such as writing to localStorage, logging, or interacting with a canvas or charting library).'
            },
            {
              id: 4,
              text: 'How can an Angular service expose state to components safely without permitting uncontrolled writes?',
              options: [
                'Expose a public writable signal directly without encapsulation',
                'Store state in window.globalState',
                'Keep the writable signal private and expose a read-only signal via asReadonly()',
                'Convert the signal to a Promise on every click'
              ],
              correctIndex: 2,
              explanation: 'Best practice is to keep the writable signal private inside the service (e.g. private count = signal(0)) and expose a read-only view using count.asReadonly() alongside explicit update methods.'
            },
            {
              id: 5,
              text: 'What happens when you read a Signal inside a computed() expression conditionally, and the condition becomes false?',
              options: [
                'The unused signal remains a permanent dependency forever',
                'Angular automatically drops the unread signal from the active dependency graph',
                'A runtime exception is thrown',
                'The application reloads the entire page'
              ],
              correctIndex: 1,
              explanation: 'Signals perform dynamic dependency tracking. Each time the computed function executes, only the signals that were actually read during that execution are subscribed to.'
            }
          ]
        },

        // --- PYTHON QUIZZES ---
        {
          id: 'quiz-py-available',
          title: 'Sprint 2 Knowledge Check: FastAPI, Pydantic & SQLAlchemy',
          module: 'Module 2: Microservices Backend',
          questionsCount: 5,
          durationMinutes: 10,
          dueDate: 'Nov 12, 2026',
          passingScore: 70,
          status: 'available',
          departmentName: 'Python',
          departmentId: 8,
          questions: [
            {
              id: 1,
              text: 'In FastAPI, what is the primary role of the Depends() dependency injection mechanism?',
              options: [
                'To automatically install pip packages at runtime',
                'To provide reusable database sessions, authentication context, and request-scoped services to route handlers',
                'To force synchronous execution on CPU-bound endpoints',
                'To render Jinja2 HTML templates'
              ],
              correctIndex: 1,
              explanation: 'Depends() allows FastAPI to manage hierarchical dependencies such as database sessions and auth claims with automatic resource cleanup.'
            },
            {
              id: 2,
              text: 'How does Pydantic v2 achieve significantly faster schema validation compared to Pydantic v1?',
              options: [
                'By compiling validation logic in Rust via the pydantic-core engine',
                'By disabling type validation in production mode',
                'By converting all numbers to strings',
                'By skipping nested models'
              ],
              correctIndex: 0,
              explanation: 'Pydantic v2 is rebuilt on pydantic-core, an optimized Rust engine that delivers 5x to 50x throughput improvements over pure Python validation.'
            },
            {
              id: 3,
              text: 'Why is it critical to use AsyncSession and selectinload / joinedload in SQLAlchemy 2 async code?',
              options: [
                'Async drivers cannot perform lazy loading implicitly on relationship attributes outside the active event loop',
                'SQLAlchemy 2 does not support SQL SELECT statements',
                'Async drivers only work with NoSQL databases',
                'Relationships must always be stored in memory'
              ],
              correctIndex: 0,
              explanation: 'In async SQLAlchemy, accessing an un-loaded relationship triggers an error because lazy loading would require blocking I/O on an async engine.'
            },
            {
              id: 4,
              text: 'What occurs when an unhandled exception is raised in a FastAPI endpoint without a custom exception handler?',
              options: [
                'The server crashes and exits',
                'FastAPI catches the exception and returns a standard HTTP 500 Internal Server Error response',
                'FastAPI redirects the user to Google',
                'FastAPI deletes the affected database record'
              ],
              correctIndex: 1,
              explanation: 'FastAPI uses Starlettes exception middleware to catch unhandled errors, returning an HTTP 500 with {"detail": "Internal Server Error"}.'
            },
            {
              id: 5,
              text: 'When should a background task be delegated to Celery instead of using FastAPIs built-in BackgroundTasks?',
              options: [
                'When the task is long-running, CPU-intensive, or requires retries and distributed broker reliability',
                'Never; BackgroundTasks is always superior to Celery',
                'Only when sending simple emails',
                'Only for GET requests'
              ],
              correctIndex: 0,
              explanation: 'FastAPIs BackgroundTasks runs inside the same process memory; for tasks that need distributed worker queues, persistence, or high reliability, Celery is required.'
            }
          ]
        },
        {
          id: 'quiz-py-completed',
          title: 'Sprint 1 Knowledge Check: Python Internals & OOP',
          module: 'Module 1: Architecture Foundations',
          questionsCount: 5,
          durationMinutes: 10,
          dueDate: 'Oct 22, 2026',
          passingScore: 70,
          status: 'completed',
          score: 90,
          passed: true,
          completedAt: '2026-10-21T16:00:00Z',
          departmentName: 'Python',
          departmentId: 8,
          questions: [
            {
              id: 1,
              text: 'What is the purpose of the Python Global Interpreter Lock (GIL) in standard CPython?',
              options: [
                'It prevents multiple native threads from executing Python bytecodes simultaneously to protect memory management',
                'It encrypts Python source files on disk',
                'It stops unauthorized network connections',
                'It locks class attributes from modification'
              ],
              correctIndex: 0,
              explanation: 'The GIL synchronizes memory access in CPython, ensuring thread-safe reference counting at the cost of single-core execution for CPU-bound Python threads.'
            },
            {
              id: 2,
              text: 'What memory optimization does declaring __slots__ provide on a Python class?',
              options: [
                'It prevents the creation of an instance __dict__, saving significant RAM when creating millions of instances',
                'It converts Python objects to C structs permanently',
                'It disables garbage collection',
                'It compresses string attributes using gzip'
              ],
              correctIndex: 0,
              explanation: '__slots__ reserves space for a fixed set of attributes, avoiding the overhead of an individual dictionary for every instance.'
            },
            {
              id: 3,
              text: 'What is the key difference between a list comprehension and a generator expression?',
              options: [
                'A list comprehension produces an in-memory list eagerly, while a generator yields items lazily on demand',
                'Generator expressions cannot be iterated over',
                'List comprehensions can only contain integers',
                'Generator expressions are always slower'
              ],
              correctIndex: 0,
              explanation: 'Generators compute values lazily using iterators, consuming minimal memory regardless of sequence length.'
            },
            {
              id: 4,
              text: 'Which dunder methods must a class implement to support the context manager protocol (with statement)?',
              options: [
                '__enter__() and __exit__()',
                '__start__() and __stop__()',
                '__open__() and __close__()',
                '__init__() and __del__()'
              ],
              correctIndex: 0,
              explanation: '__enter__ is called when entering the with block, and __exit__ guarantees cleanup even if an exception occurs.'
            },
            {
              id: 5,
              text: 'What is Method Resolution Order (MRO) in Python multiple inheritance?',
              options: [
                'The deterministic C3 Linearization order in which Python searches base classes for methods and attributes',
                'The speed at which a function compiles to bytecode',
                'The alphabetical ordering of module imports',
                'The operating system thread priority'
              ],
              correctIndex: 0,
              explanation: 'Python uses the C3 linearization algorithm to guarantee a consistent, monotonic Method Resolution Order across complex inheritance hierarchies.'
            }
          ]
        },

        // --- .NET QUIZZES ---
        {
          id: 'quiz-dotnet',
          title: 'Sprint Checkpoint: C# 12 & ASP.NET Core Concurrency',
          module: 'Module 2: Microservices Backend',
          questionsCount: 5,
          durationMinutes: 10,
          dueDate: 'Nov 12, 2026',
          passingScore: 70,
          status: 'available',
          departmentName: '.NET',
          departmentId: 7,
          questions: [
            {
              id: 1,
              text: 'Which feature in C# 12 provides immutable shallow value-semantics with concise constructor syntax?',
              options: [
                'Primary Constructors on Records and Classes',
                'Extension Properties',
                'Global Using Directives',
                'Tuple Deconstruction'
              ],
              correctIndex: 0,
              explanation: 'Primary constructors in C# 12 allow declaring parameters directly on the class or record header, initializing properties directly.'
            },
            {
              id: 2,
              text: 'In ASP.NET Core Clean Architecture, how does MediatR decouple command handlers from controllers?',
              options: [
                'By dispatching IRequest<T> objects through an in-memory mediator without direct handler references',
                'By writing all payloads to a disk queue',
                'By compiling controllers into background windows services',
                'By replacing dependency injection with static singletons'
              ],
              correctIndex: 0,
              explanation: 'MediatR acts as an in-process dispatcher; controllers only know the request model, and MediatR resolves the registered handler.'
            },
            {
              id: 3,
              text: 'What is the primary benefit of EF Core AsNoTracking() queries on read-only endpoints?',
              options: [
                'It bypasses the change tracker, significantly reducing memory allocations and CPU overhead',
                'It allows reading from encrypted files without keys',
                'It automatically creates database indexes',
                'It converts SQL queries into GraphQL'
              ],
              correctIndex: 0,
              explanation: 'AsNoTracking informs Entity Framework not to maintain identity maps or tracking snapshots for returned entities, speeding up queries.'
            },
            {
              id: 4,
              text: 'In Polly resilience policies, what is the role of a Circuit Breaker?',
              options: [
                'To temporarily halt requests to a failing downstream service, preventing cascading exhaustion of threads and resources',
                'To restart the web server automatically on exceptions',
                'To encrypt network traffic with TLS 1.3',
                'To compress JSON responses'
              ],
              correctIndex: 0,
              explanation: 'Circuit breakers open after a threshold of failures, failing fast to allow downstream systems time to recover before retrying.'
            },
            {
              id: 5,
              text: 'What is the advantage of using IAsyncEnumerable<T> in ASP.NET Core Web APIs?',
              options: [
                'It streams data asynchronously chunk-by-chunk to the HTTP client as it arrives from the database',
                'It requires all data to be loaded into an array first',
                'It only works with synchronous socket calls',
                'It disables HTTP compression'
              ],
              correctIndex: 0,
              explanation: 'IAsyncEnumerable enables streaming responses, reducing server memory buffers when processing large result sets.'
            }
          ]
        },
        {
          id: 'quiz-dotnet-completed',
          title: 'Sprint 1 Checkpoint: C# 12 Type System & Memory Management',
          module: 'Module 1: Architecture Foundations',
          questionsCount: 5,
          durationMinutes: 10,
          dueDate: 'Oct 25, 2026',
          passingScore: 70,
          status: 'completed',
          score: 95,
          passed: true,
          completedAt: '2026-10-24T18:00:00Z',
          departmentName: '.NET',
          departmentId: 7,
          questions: [
            {
              id: 1,
              text: 'What distinguishes a struct (value type) from a class (reference type) in .NET memory allocation?',
              options: [
                'Structs are allocated on the stack (or inline in containing types), while classes are allocated on the managed heap',
                'Structs cannot contain methods',
                'Classes cannot implement interfaces',
                'Structs can be inherited by other classes'
              ],
              correctIndex: 0,
              explanation: 'Value types reside on the stack or inline within their parent object, avoiding garbage collector overhead for short-lived data.'
            },
            {
              id: 2,
              text: 'What does the Span<T> and ReadOnlySpan<T> struct provide in high-performance C# code?',
              options: [
                'A type-safe, contiguous view of arbitrary memory (stack, heap, unmanaged) with zero allocations',
                'A thread-safe concurrent queue',
                'A database connection pool',
                'A dynamic JSON serializer'
              ],
              correctIndex: 0,
              explanation: 'Span<T> enables zero-copy memory slicing across arrays, strings, or unmanaged buffers without creating new heap objects.'
            },
            {
              id: 3,
              text: 'How does the .NET Garbage Collector organize objects across generations?',
              options: [
                'Gen 0 (short-lived), Gen 1 (buffer), Gen 2 (long-lived), and LOH (Large Object Heap for objects > 85,000 bytes)',
                'Alphabetically by class name',
                'By thread priority',
                'By file size on disk'
              ],
              correctIndex: 0,
              explanation: 'The generational GC leverages the hypothesis that newly allocated objects die young, collecting Gen 0 very cheaply.'
            },
            {
              id: 4,
              text: 'What is the purpose of the IDisposable interface and the using statement in C#?',
              options: [
                'To provide deterministic release of unmanaged resources (file handles, database connections, sockets)',
                'To delete objects from hard drive',
                'To terminate the application process',
                'To convert objects to XML'
              ],
              correctIndex: 0,
              explanation: 'IDisposable ensures unmanaged OS handles and pooled connections are released deterministically rather than waiting for GC finalization.'
            },
            {
              id: 5,
              text: 'What does ConfigureAwait(false) do in non-UI backend .NET code?',
              options: [
                'It instructs the task continuation not to capture the original SynchronizationContext, avoiding unnecessary thread marshaling',
                'It forces the task to execute synchronously on the main thread',
                'It disables task exception handling',
                'It cancels the task after 5 seconds'
              ],
              correctIndex: 0,
              explanation: 'In ASP.NET Core and backend services, ConfigureAwait(false) prevents context switching overhead and avoids synchronization deadlocks.'
            }
          ]
        },

        // --- JAVA QUIZZES ---
        {
          id: 'quiz-java',
          title: 'Sprint Checkpoint: Java 21 Virtual Threads & Spring Security',
          module: 'Module 2: Microservices Backend',
          questionsCount: 5,
          durationMinutes: 10,
          dueDate: 'Nov 12, 2026',
          passingScore: 70,
          status: 'available',
          departmentName: 'Java',
          departmentId: 9,
          questions: [
            {
              id: 1,
              text: 'How do Java 21 Virtual Threads reduce server resource utilization under high I/O concurrency?',
              options: [
                'By compiling bytecode to native C++ binaries',
                'By parking lightweight virtual threads off carrier threads during blocking socket operations',
                'By forcing all requests to execute on a single core',
                'By disabling garbage collection'
              ],
              correctIndex: 1,
              explanation: 'Virtual threads yield their underlying carrier OS thread when blocked on I/O, allowing millions of concurrent requests.'
            },
            {
              id: 2,
              text: 'What is thread pinning in Project Loom, and what causes it?',
              options: [
                'When a virtual thread cannot be unmounted from its carrier thread due to being inside a synchronized block or native method',
                'When a thread is pinned to CPU core 0',
                'When a thread runs out of heap memory',
                'When a thread is locked by an IDE debugger'
              ],
              correctIndex: 0,
              explanation: 'Holding a synchronized monitor or calling native JNI code pins the virtual thread to its carrier OS thread, preventing unmounting.'
            },
            {
              id: 3,
              text: 'In Spring Security 6, how are security rules configured following the deprecation of WebSecurityConfigurerAdapter?',
              options: [
                'By declaring a @Bean of type SecurityFilterChain that configures HttpSecurity programmatically',
                'In web.xml deployment descriptors',
                'Through static Java properties in application.properties',
                'By annotating every class with @Secure'
              ],
              correctIndex: 0,
              explanation: 'Spring Security 6 utilizes component-based configuration exposing SecurityFilterChain beans with lambda DSL expressions.'
            },
            {
              id: 4,
              text: 'What is the purpose of Spring Data JPA Second-Level Cache (L2 Cache) with Ehcache or Redis?',
              options: [
                'To share entity and query cache state across multiple EntityManager sessions and application instances',
                'To replace primary database storage entirely',
                'To compile SQL queries to machine code',
                'To format JSON API responses'
              ],
              correctIndex: 0,
              explanation: 'First-level cache is scoped to a single transaction/EntityManager; L2 cache shares entity data across sessions, drastically reducing DB queries.'
            },
            {
              id: 5,
              text: 'Why are Testcontainers preferred over in-memory databases (like H2) for testing Spring Boot microservices?',
              options: [
                'They run real production database containers (Postgres, SQL Server, Redis), ensuring exact dialect, index, and constraint compatibility',
                'They require zero Docker installation',
                'They run without JVM bytecode compilation',
                'They make tests run 100x faster than mockito'
              ],
              correctIndex: 0,
              explanation: 'H2 lacks support for proprietary vendor functions, JSON operators, and dialect-specific locking behavior that real containers provide.'
            }
          ]
        },
        {
          id: 'quiz-java-completed',
          title: 'Sprint 1 Checkpoint: Modern Java OOP, Records & Streams',
          module: 'Module 1: Architecture Foundations',
          questionsCount: 5,
          durationMinutes: 10,
          dueDate: 'Oct 26, 2026',
          passingScore: 70,
          status: 'completed',
          score: 90,
          passed: true,
          completedAt: '2026-10-25T15:00:00Z',
          departmentName: 'Java',
          departmentId: 9,
          questions: [
            {
              id: 1,
              text: 'What does declaring a Java record provide automatically?',
              options: [
                'An immutable carrier class with canonical constructor, getters, equals(), hashCode(), and toString()',
                'A mutable database table representation',
                'An asynchronous thread pool',
                'An auto-scaling cloud cluster'
              ],
              correctIndex: 0,
              explanation: 'Records are transparent, immutable carriers for data that eliminate boilerplate code for POJO definitions.'
            },
            {
              id: 2,
              text: 'What is the key difference between intermediate and terminal operations in the Java Stream API?',
              options: [
                'Intermediate operations return a new Stream and are executed lazily; terminal operations trigger pipeline execution and produce a result',
                'Intermediate operations print to console immediately',
                'Terminal operations can only be executed once per day',
                'Intermediate operations can only operate on strings'
              ],
              correctIndex: 0,
              explanation: 'Streams are lazy; no computation occurs until a terminal operation (like collect, count, or forEach) is invoked.'
            },
            {
              id: 3,
              text: 'What is pattern matching for switch in modern Java (Java 21)?',
              options: [
                'It allows switching on object types with pattern variables and guarded when clauses',
                'It regex matches string patterns in SQL queries',
                'It replaces if-statements across all classes automatically',
                'It searches files in directories'
              ],
              correctIndex: 0,
              explanation: 'Pattern matching for switch enables expressive, type-safe branch inspection with automatic casting and guard conditions.'
            },
            {
              id: 4,
              text: 'Why should Optional<T> never be used as a method parameter or field type in Java?',
              options: [
                'It is designed strictly as a method return type to signify potential absence without throwing NullPointerException',
                'Optional is deprecated in Java 21',
                'Optional doubles garbage collection time',
                'Optional can only contain numbers'
              ],
              correctIndex: 0,
              explanation: 'Using Optional as fields or parameters increases memory allocations and forces callers to wrap values unnecessarily.'
            },
            {
              id: 5,
              text: 'What is the contract between equals() and hashCode() in Java?',
              options: [
                'If two objects are equal according to equals(), they must produce the exact same integer hashCode()',
                'If two objects have the same hashCode(), they must always be equal',
                'hashCode() must always return 0',
                'equals() must only check memory addresses'
              ],
              correctIndex: 0,
              explanation: 'Maintaining this contract is essential for hash-based collections (HashMap, HashSet) to look up objects accurately.'
            }
          ]
        },

        // --- PHP QUIZZES ---
        {
          id: 'quiz-php',
          title: 'Sprint Checkpoint: PHP 8.3 Types & Laravel Architecture',
          module: 'Module 2: Microservices Backend',
          questionsCount: 5,
          durationMinutes: 10,
          dueDate: 'Nov 12, 2026',
          passingScore: 70,
          status: 'available',
          departmentName: 'PHP',
          departmentId: 6,
          questions: [
            {
              id: 1,
              text: 'What is the purpose of Laravel Form Requests in clean architecture?',
              options: [
                'To isolate incoming HTTP payload validation and authorization away from controller logic',
                'To automatically generate frontend HTML forms',
                'To manage database transactions',
                'To compile Blade templates'
              ],
              correctIndex: 0,
              explanation: 'Form Requests encapsulate authorization and validation rules before the controller method executes, maintaining slim controllers.'
            },
            {
              id: 2,
              text: 'How does Laravel Horizon improve queue monitoring in production applications?',
              options: [
                'It provides real-time dashboard metrics, auto-scaling worker balancing, and failed job management for Redis queues',
                'It replaces Redis with MySQL queues',
                'It compiles PHP code to WebAssembly',
                'It automatically fixes broken code'
              ],
              correctIndex: 0,
              explanation: 'Horizon provides code-driven configuration, throughput metrics, runtime latency insights, and retry tools for Redis queues.'
            },
            {
              id: 3,
              text: 'How do PHP 8.3 typed class constants and readonly properties strengthen domain models?',
              options: [
                'They enforce strict static typing and prevent accidental mutation after constructor initialization',
                'They convert PHP scripts into binary executables',
                'They remove the need for database migrations',
                'They allow classes to have dynamic property names'
              ],
              correctIndex: 0,
              explanation: 'Readonly properties guarantee immutability, while typed constants ensure domain constants cannot be assigned invalid types.'
            },
            {
              id: 4,
              text: 'What causes the classic N+1 query problem in Eloquent ORM, and how is it resolved?',
              options: [
                'Accessing relationships in loops without eager loading; resolved by using with() or load()',
                'Running more than N database queries in one minute',
                'Using composite primary keys in MySQL',
                'Storing passwords without hashing'
              ],
              correctIndex: 0,
              explanation: 'Lazy loading inside loops executes 1 query for the parent and N queries for each child; eager loading with() runs exactly 2 queries.'
            },
            {
              id: 5,
              text: 'What is the advantage of using Pest 3 over traditional PHPUnit test syntax?',
              options: [
                'Expressive expectation chaining, higher-order tests, built-in architecture tests, and cleaner syntax',
                'Pest runs without a PHP interpreter',
                'Pest eliminates all database migrations',
                'Pest can only test Laravel applications'
              ],
              correctIndex: 0,
              explanation: 'Pest provides concise expectations (expect($val)->toBe(...)) and architecture testing presets while retaining full PHPUnit interoperability.'
            }
          ]
        },
        {
          id: 'quiz-php-completed',
          title: 'Sprint 1 Checkpoint: PHP 8.3 Modern Language Features',
          module: 'Module 1: Architecture Foundations',
          questionsCount: 5,
          durationMinutes: 10,
          dueDate: 'Oct 27, 2026',
          passingScore: 70,
          status: 'completed',
          score: 85,
          passed: true,
          completedAt: '2026-10-26T17:00:00Z',
          departmentName: 'PHP',
          departmentId: 6,
          questions: [
            {
              id: 1,
              text: 'What does declare(strict_types=1); enforce at the top of a PHP file?',
              options: [
                'Scalar type declarations are strictly validated without automatic type coercion',
                'The script cannot use external packages',
                'Variables must be declared before use',
                'All functions must be static'
              ],
              correctIndex: 0,
              explanation: 'strict_types=1 ensures PHP throws a TypeError if passed arguments do not match the declared parameter types exactly.'
            },
            {
              id: 2,
              text: 'What is the difference between switch and the match expression introduced in PHP 8.0?',
              options: [
                'match uses strict identity checks (===), returns a value directly, and does not require break statements',
                'match only works with integers',
                'switch is deprecated in PHP 8.3',
                'match can only have two branches'
              ],
              correctIndex: 0,
              explanation: 'match returns an evaluated expression, prevents fallthrough bugs, and enforces strict type equality.'
            },
            {
              id: 3,
              text: 'What are PHP 8.1 Backed Enums?',
              options: [
                'Enumerated types whose cases are backed by an internal scalar value (string or int)',
                'Enums that store data in database tables',
                'Arrays with string keys only',
                'Anonymous classes'
              ],
              correctIndex: 0,
              explanation: 'Backed enums (e.g. enum Status: string) map each case to a distinct string or integer scalar, perfect for database storage.'
            },
            {
              id: 4,
              text: 'What is Constructor Property Promotion in modern PHP?',
              options: [
                'Declaring visibility (public, private) directly on constructor arguments to automatically define and assign properties',
                'Promoting class properties to global variables',
                'Promoting junior developers to senior roles',
                'Creating constructors dynamically'
              ],
              correctIndex: 0,
              explanation: 'Property promotion avoids redundant property declarations and assignment boilerplate inside constructors.'
            },
            {
              id: 5,
              text: 'What does the nullsafe operator (?->) accomplish in PHP?',
              options: [
                'It short-circuits evaluation and returns null if any link in the method or property chain evaluates to null',
                'It replaces null values with empty strings',
                'It converts null to integer 0',
                'It triggers an exception whenever null is encountered'
              ],
              correctIndex: 0,
              explanation: 'The nullsafe operator avoids verbose nested if (!is_null(...)) checks when navigating deep object graphs.'
            }
          ]
        },

        // --- DATABASE ENGINEER QUIZZES ---
        {
          id: 'quiz-db',
          title: 'Sprint Checkpoint: Relational Database Indexing & ACID Isolation',
          module: 'Module 2: Database Systems',
          questionsCount: 5,
          durationMinutes: 10,
          dueDate: 'Nov 12, 2026',
          passingScore: 70,
          status: 'available',
          departmentName: 'Database Engineer',
          departmentId: 10,
          questions: [
            {
              id: 1,
              text: 'Why does composite index column order matter in relational query planning?',
              options: [
                'B-Tree index traversal follows the leftmost prefix principle',
                'SQL Server reverses the column order randomly',
                'Column order only affects storage size, not seek performance',
                'Only the last column in the composite index is indexed'
              ],
              correctIndex: 0,
              explanation: 'The query optimizer can only use composite indexes for range seeks if predicates match leading columns in order.'
            },
            {
              id: 2,
              text: 'What causes a RID Lookup or Key Lookup in a query execution plan, and how is it eliminated?',
              options: [
                'The non-clustered index does not contain all projected columns; eliminated by creating a covering index with INCLUDE columns',
                'The table has too many primary keys',
                'The query uses WHERE instead of HAVING',
                'The database is corrupted'
              ],
              correctIndex: 0,
              explanation: 'When columns are missing from a non-clustered index, the engine must look up data in the clustered index; INCLUDE columns provide a covering index.'
            },
            {
              id: 3,
              text: 'What is the key advantage of Snapshot Isolation over standard Read Committed isolation?',
              options: [
                'Readers do not block writers, and writers do not block readers, preventing concurrency lock contention via row versioning',
                'Snapshot isolation disables all database transactions',
                'Snapshot isolation requires zero disk space',
                'Snapshot isolation only works on read-only databases'
              ],
              correctIndex: 0,
              explanation: 'Snapshot isolation uses row versioning in tempdb to provide point-in-time consistency without shared read locks.'
            },
            {
              id: 4,
              text: 'In SQL Server or PostgreSQL, what is a Deadlock and how does the engine resolve it?',
              options: [
                'Two transactions each hold locks that the other needs in a circular dependency; the engine terminates the lower-cost victim transaction',
                'The database server runs out of disk space',
                'A query takes more than 30 seconds to run',
                'The network connection drops'
              ],
              correctIndex: 0,
              explanation: 'A background deadlock detector monitors lock wait graphs, identifying circular lock wait loops and rolling back the least expensive victim.'
            },
            {
              id: 5,
              text: 'Why are Clustered Columnstore Indexes ideal for data warehousing and analytics queries on large tables?',
              options: [
                'They store data column-by-column in compressed rowgroups, reading only the specific columns referenced in aggregate queries',
                'They prevent any data from ever being updated',
                'They replace SQL with JSON document storage',
                'They store all data in the client browser'
              ],
              correctIndex: 0,
              explanation: 'Columnar storage provides 10x compression and segment elimination, speeding up analytical aggregation queries exponentially.'
            }
          ]
        },
        {
          id: 'quiz-db-completed',
          title: 'Sprint 1 Checkpoint: Relational Normalization & SQL Tuning',
          module: 'Module 1: Architecture Foundations',
          questionsCount: 5,
          durationMinutes: 10,
          dueDate: 'Oct 28, 2026',
          passingScore: 70,
          status: 'completed',
          score: 95,
          passed: true,
          completedAt: '2026-10-27T16:00:00Z',
          departmentName: 'Database Engineer',
          departmentId: 10,
          questions: [
            {
              id: 1,
              text: 'What is required for a relational database table to be in Third Normal Form (3NF)?',
              options: [
                'It is in 2NF and contains no transitive functional dependencies (every non-key attribute depends only on the primary key)',
                'It contains exactly 3 columns',
                'It must have 3 foreign keys',
                'It cannot contain NULL values'
              ],
              correctIndex: 0,
              explanation: '3NF ensures that non-key columns depend on "the key, the whole key, and nothing but the key" to eliminate update anomalies.'
            },
            {
              id: 2,
              text: 'What is parameter sniffing in relational database engines?',
              options: [
                'When the optimizer compiles a query plan based on initial parameter values that may be suboptimal for future parameter calls',
                'A network security packet inspection tool',
                'A feature that checks user input for SQL injection',
                'A tool that converts stored procedures to functions'
              ],
              correctIndex: 0,
              explanation: 'Parameter sniffing can cause erratic performance when data distribution is skewed, requiring query hints or RECOMPILE options.'
            },
            {
              id: 3,
              text: 'What distinguishes an S-lock (Shared Lock) from an X-lock (Exclusive Lock)?',
              options: [
                'Multiple transactions can hold S-locks concurrently for reading, while an X-lock grants exclusive modification rights and blocks all other locks',
                'X-locks are only used on weekends',
                'S-locks permanently delete records',
                'X-locks can only be held for 1 second'
              ],
              correctIndex: 0,
              explanation: 'Shared locks allow concurrent reads, whereas Exclusive locks ensure no other transaction can read or write the locked resource.'
            },
            {
              id: 4,
              text: 'What is the purpose of Database Table Partitioning?',
              options: [
                'Dividing very large tables into smaller, manageable physical subsets while maintaining a single logical table view',
                'Splitting a database across two different companies',
                'Creating backup copies of every table',
                'Compressing tables into ZIP files'
              ],
              correctIndex: 0,
              explanation: 'Partitioning enables partition elimination during queries and fast sliding-window data archiving via metadata partition switches.'
            },
            {
              id: 5,
              text: 'Why should SELECT * be avoided in production application queries?',
              options: [
                'It invalidates covering indexes, increases network I/O, prevents columnar compression, and breaks contracts on schema additions',
                'SQL Server disallows SELECT * in stored procedures',
                'SELECT * is deprecated in ANSI SQL',
                'It causes immediate deadlocks'
              ],
              correctIndex: 0,
              explanation: 'Selecting all columns prevents index-only scans, increases memory grant requirements, and wastes network bandwidth.'
            }
          ]
        }
      ],

      announcements: [
        {
          id: 'ann-1',
          title: 'Schedule Update: Friday Guest Lecture on Cloud Observability',
          author: 'Priya Sharma (Staff Engineer)',
          authorRole: 'Lead Trainer',
          authorAvatar: 'PS',
          date: 'Yesterday at 3:30 PM',
          priority: 'urgent',
          isPinned: true,
          isRead: false,
          content: 'Team, please note that our guest lecture with Principal Architect Vikram Joshi on "Distributed Tracing and Observability" will take place this Friday at 2:00 PM IST. Please review the pre-reading slides in Learning Materials before the session.',
          tags: ['Schedule', 'Guest Lecture', 'Module 4']
        },
        {
          id: 'ann-2',
          title: 'Office Hours & Assignment 3 Live Q&A Session',
          author: 'Ananya Roy (Principal Engineer)',
          authorRole: 'Teaching Assistant & Mentor',
          authorAvatar: 'AR',
          date: 'Nov 03, 2026',
          priority: 'important',
          isPinned: false,
          isRead: true,
          content: 'We will be hosting a dedicated debugging session tomorrow at 4:30 PM IST to help anyone having questions on Angular Signals or reactive form validation. Bring your repositories!',
          tags: ['Office Hours', 'Assignment 3', 'Mentorship']
        },
        {
          id: 'ann-3',
          title: 'Mid-Cohort Capstone Hackathon Announcement',
          author: 'Vikram Joshi (Senior Architect)',
          authorRole: 'Program Mentor',
          authorAvatar: 'VJ',
          date: 'Oct 30, 2026',
          priority: 'notice',
          isPinned: false,
          isRead: true,
          content: 'Get ready! At the conclusion of Week 6, our cohort will participate in a 36-hour internal Hackathon solving high-throughput fintech and logistics use cases. Squads have been finalized in the Members tab.',
          tags: ['Hackathon', 'Capstone', 'Squads']
        }
      ],

      members: [
        {
          id: 'm-trainer-1',
          name: 'Priya Sharma',
          email: 'priya.sharma@example.com',
          role: 'lead_trainer',
          specialization: 'Staff Engineer & Microservices Lead',
          squad: 'Faculty',
          avatar: 'PS',
          status: 'online',
          progressPercentage: 100
        },
        {
          id: 'm-mentor-1',
          name: 'Vikram Joshi',
          email: 'vikram.j@example.com',
          role: 'mentor',
          specialization: 'Principal Cloud & DevOps Architect',
          squad: 'Faculty',
          avatar: 'VJ',
          status: 'online',
          progressPercentage: 100
        },
        {
          id: 'm-mentor-2',
          name: 'Ananya Roy',
          email: 'ananya.r@example.com',
          role: 'assistant_trainer',
          specialization: 'Frontend Architect & Angular Lead',
          squad: 'Faculty',
          avatar: 'AR',
          status: 'in_session',
          progressPercentage: 100
        },
        {
          id: 'm-learner-1',
          name: 'Aarav Sharma',
          email: 'aarav.sharma@example.com',
          role: 'learner',
          specialization: 'Backend & High-Throughput DBs',
          squad: 'Squad Alpha (API & Gateway)',
          avatar: 'AS',
          status: 'online',
          progressPercentage: 72
        },
        {
          id: 'm-learner-2',
          name: 'Diya Verma',
          email: 'diya.verma@example.com',
          role: 'learner',
          specialization: 'FastAPI & Async Event Loops',
          squad: 'Squad Alpha (API & Gateway)',
          avatar: 'DV',
          status: 'online',
          progressPercentage: 80
        },
        {
          id: 'm-learner-3',
          name: 'Ishaan Patel',
          email: 'ishaan.patel@example.com',
          role: 'learner',
          specialization: 'PostgreSQL & DB Migrations',
          squad: 'Squad Gamma (DevOps & Telemetry)',
          avatar: 'IP',
          status: 'online',
          progressPercentage: 66
        },
        {
          id: 'm-learner-4',
          name: 'Ananya Kapoor',
          email: 'ananya.k@example.com',
          role: 'learner',
          specialization: 'Angular Reactive Architecture',
          squad: 'Squad Beta (UI & Design Systems)',
          avatar: 'AK',
          status: 'in_session',
          progressPercentage: 75
        },
        {
          id: 'm-learner-5',
          name: 'Vihaan Rao',
          email: 'vihaan.rao@example.com',
          role: 'learner',
          specialization: 'Full-Stack Integration',
          squad: 'Squad Beta (UI & Design Systems)',
          avatar: 'VR',
          status: 'online',
          progressPercentage: 82
        },
        {
          id: 'm-learner-6',
          name: 'Rahul Pandey (Learner)',
          email: 'rahul.pandey@example.com',
          role: 'learner',
          specialization: 'Full-Stack & Cloud Architecture',
          squad: 'Squad Alpha (API & Gateway)',
          avatar: 'RP',
          status: 'online',
          progressPercentage: 68
        }
      ],

      progress: {
        overallPercentage: 68,
        modulesCompleted: 2,
        totalModules: 5,
        assignmentsSubmitted: 3,
        totalAssignments: 4,
        quizzesPassed: 2,
        totalQuizzes: 4,
        attendanceRate: 94,
        milestones: [
          {
            week: 'Week 1–2',
            title: 'Clean Architecture, SOLID & Code Quality',
            description: 'Mastered modular code structuring, unit testing with pytest, and design patterns.',
            status: 'completed',
            completedDate: 'Oct 28, 2026'
          },
          {
            week: 'Week 3–4',
            title: 'Microservices with FastAPI, Asyncio & PostgreSQL',
            description: 'Built high-concurrency microservices, DB connection pools, migrations, and query optimization.',
            status: 'completed',
            completedDate: 'Nov 04, 2026'
          },
          {
            week: 'Week 5–6',
            title: 'Frontend Mastery: Angular 17+ Signals & RxJS',
            description: 'Active sprint building responsive reactive SPAs with zero Zone.js overhead and typed state.',
            status: 'current'
          },
          {
            week: 'Week 7–8',
            title: 'Cloud Infrastructure, Docker & CI/CD Pipelines',
            description: 'Containerizing multi-service stacks, writing automated test pipelines and security scanners.',
            status: 'upcoming'
          },
          {
            week: 'Week 9–10',
            title: 'Enterprise Capstone Engineering Project',
            description: 'Team delivery of an enterprise-grade fintech orchestration system with full SLA resilience.',
            status: 'upcoming'
          },
          {
            week: 'Week 11–12',
            title: 'System Design Reviews & Industry Placement',
            description: 'Live architecture defense, mock engineering interviews, and project graduation demo.',
            status: 'upcoming'
          }
        ],
        earnedBadges: [
          {
            id: 'b-python',
            title: 'Python Core & Asyncio Pro',
            icon: '🐍',
            description: 'Demonstrated mastery in asynchronous concurrency, event loops, and clean design.',
            earnedDate: 'Oct 25, 2026'
          },
          {
            id: 'b-fastapi',
            title: 'FastAPI Microservice Specialist',
            icon: '⚡',
            description: 'Constructed production REST APIs with automated OpenAPI documentation and validation.',
            earnedDate: 'Nov 01, 2026'
          },
          {
            id: 'b-clean-code',
            title: 'Clean Architecture Certified',
            icon: '💎',
            description: 'Scored 95%+ in architectural decoupling and repository design patterns.',
            earnedDate: 'Oct 29, 2026'
          },
          {
            id: 'b-attendance',
            title: 'High Attendance Honor (94%)',
            icon: '🎯',
            description: 'Maintained 90%+ prompt session attendance throughout active cohort phases.',
            earnedDate: 'Nov 04, 2026'
          }
        ]
      },

      discussions: [
        {
          id: 'disc-1',
          title: 'How should we handle unhandled Promise rejections inside Angular Signals effects?',
          category: 'Technical Q&A',
          author: 'Rahul Pandey',
          authorRole: 'Learner',
          authorAvatar: 'RP',
          createdAt: '2 hours ago',
          content: 'When writing an effect() that triggers an asynchronous async/await operation, what is the best practice for capturing and dispatching errors without breaking the effect lifecycle?',
          likes: 4,
          hasLiked: true,
          isResolved: true,
          replies: [
            {
              id: 'rep-1',
              author: 'Priya Sharma (Staff Engineer)',
              authorRole: 'Lead Trainer',
              authorAvatar: 'PS',
              createdAt: '1 hour ago',
              isTrainerReply: true,
              content: 'Great question Rahul! Inside an effect(), wrap the async call in a try/catch block and pipe errors to a dedicated error signal (e.g. errorSignal.set(err.message)). Avoid unhandled async throws inside effects since they can cause unexpected teardown in dev mode.'
            },
            {
              id: 'rep-2',
              author: 'Aarav Sharma',
              authorRole: 'Learner',
              authorAvatar: 'AS',
              createdAt: '45 mins ago',
              content: 'I did the same for Assignment 3 and created an ErrorBannerComponent that subscribes to errorSignal. Works very smoothly!'
            }
          ]
        },
        {
          id: 'disc-2',
          title: 'Tips for Assignment 4: Minimizing Docker image sizes with multi-stage builds',
          category: 'Assignments',
          author: 'Rohan Verma',
          authorRole: 'Learner',
          authorAvatar: 'RV',
          createdAt: 'Yesterday',
          content: 'Has anyone compared python:3.11-slim versus alpine for FastAPI? Any dependency issues with psycopg or cryptography?',
          likes: 6,
          hasLiked: false,
          isResolved: true,
          replies: [
            {
              id: 'rep-3',
              author: 'Vikram Joshi (Senior Architect)',
              authorRole: 'Program Mentor',
              authorAvatar: 'VJ',
              createdAt: 'Yesterday',
              isTrainerReply: true,
              content: 'Always prefer python:3.11-slim or distroless over alpine for Python. Alpine uses musl libc, which forces pip to compile wheels from source instead of using pre-built manylinux wheels, slowing your CI/CD by up to 10x.'
            }
          ]
        }
      ]
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
        } catch {}
      }

      // Merge canonical learners into managedUsers if not present
      const existingEmails = new Set(managedUsers.map((u: any) => u.email?.toLowerCase().trim()));
      for (const cl of CohortService.CANONICAL_LEARNERS) {
        if (!existingEmails.has(cl.email.toLowerCase().trim())) {
          managedUsers.push({
            id: cl.id,
            full_name: cl.name,
            email: cl.email,
            role: 'learner',
            is_active: true,
            created_at: '2026-10-25T10:00:00Z',
            temporary_password: 'Welcome@2026'
          });
          existingEmails.add(cl.email.toLowerCase().trim());
        }
      }

      // Check logged in user in sessionStorage
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
        } catch {}
      }

      const platformLearners = managedUsers.filter((u: any) => u.role === 'learner' && u.is_active !== false);

      const matrix = data.attendanceMatrix;
      const days = matrix.days || [];
      const existingRows = matrix.students || [];

      // Map each platform learner to AttendanceStudentRow
      const updatedStudents: AttendanceStudentRow[] = platformLearners.map((learner: any, index: number) => {
        const email = learner.email?.toLowerCase().trim();
        const name = learner.full_name?.trim();
        const canon = CohortService.CANONICAL_LEARNERS.find(c => c.email.toLowerCase() === email || c.name.toLowerCase() === name.toLowerCase());

        // Look for existing row in current matrix
        const existing = existingRows.find(s =>
          s.studentId === `std-${learner.id}` ||
          s.studentId === `std-${canon?.id}` ||
          s.studentId === String(learner.id) ||
          s.name.toLowerCase().trim() === name.toLowerCase() ||
          (canon && s.name.toLowerCase().trim() === canon.name.toLowerCase().trim())
        );

        const admissionNo = existing?.admissionNo || canon?.admissionNo || `SKL/2026/${String(learner.id || 100 + index).slice(-4).padStart(4, '0')}`;

        // Build daily status
        const dailyStatus: Record<string, 'P' | 'A' | 'L' | 'H'> = {};
        let absCount = 0;
        let lveCount = 0;

        for (const d of days) {
          const dateKey = d.dateStr;
          let status: 'P' | 'A' | 'L' | 'H';

          if (existing && existing.dailyStatus && existing.dailyStatus[dateKey]) {
            status = existing.dailyStatus[dateKey];
          } else if (canon && canon.defaultStatus && canon.defaultStatus[dateKey]) {
            status = canon.defaultStatus[dateKey];
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
          studentId: existing?.studentId || `std-${learner.id || canon?.id || index + 1}`,
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

      const updatedMembers: CohortMemberProfile[] = platformLearners.map((learner: any, idx: number) => {
        const email = learner.email?.toLowerCase().trim();
        const canon = CohortService.CANONICAL_LEARNERS.find(c => c.email.toLowerCase() === email || c.name.toLowerCase() === learner.full_name?.toLowerCase().trim());
        const existingMember = (data.members || []).find(m => m.email?.toLowerCase().trim() === email || m.name.toLowerCase().trim() === learner.full_name?.toLowerCase().trim());

        const initials = learner.full_name
          ? learner.full_name.split(' ').map((n: string) => n.charAt(0)).join('').toUpperCase().slice(0, 2)
          : 'LN';

        return {
          id: existingMember?.id || `m-learner-${learner.id || idx + 1}`,
          name: learner.full_name,
          email: learner.email,
          role: 'learner',
          specialization: existingMember?.specialization || canon?.specialization || specs[idx % specs.length],
          squad: existingMember?.squad || canon?.squad || squads[idx % squads.length],
          avatar: existingMember?.avatar || canon?.avatar || initials,
          status: existingMember?.status || 'online',
          progressPercentage: existingMember?.progressPercentage || (68 + (idx % 4) * 4)
        };
      });

      data.members = [...faculty, ...updatedMembers];

      // Synchronize Batches Learner Count
      if (data.batches && data.batches.length > 0) {
        data.batches[0].learnerCount = updatedStudents.length;
      }

      // Save and emit
      if (typeof localStorage !== 'undefined') {
        try {
          localStorage.setItem(this.storageKey, JSON.stringify(data));
        } catch {}
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
    if (typeof localStorage !== 'undefined') {
      try {
        localStorage.setItem(this.storageKey, JSON.stringify(data));
      } catch {}
    }
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
    departmentId?: number
  ): CohortBatchCard {
    const current = this.getCohortData();
    const count = learnerIds.length > 0 ? learnerIds.length : learnerCount;
    const newBatch: CohortBatchCard = {
      id: `batch-${Date.now()}`,
      name,
      learnerCount: count,
      startDate,
      endDate,
      status: 'current',
      track: track || `${departmentName} Track`,
      departmentName: departmentName || 'All / Common',
      departmentId,
      learnerIds,
      learnerNames
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
    if (current.batches.length <= 1) return false;

    const remaining = current.batches.filter(b => b.id !== batchId);
    const updated: CohortFullData = {
      ...current,
      batches: remaining,
      activeBatchId: remaining[0].id
    };
    this.saveState(updated);
    return true;
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
    return newChap;
  }

  deleteChapter(chapterId: string): void {
    const current = this.getCohortData();
    this.saveState({
      ...current,
      curriculum: current.curriculum.filter(c => c.id !== chapterId)
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
      departmentId: (lesson as any).departmentId || targetChap.departmentId
    };

    const updatedChap = {
      ...current.curriculum[cIdx],
      lessons: [...current.curriculum[cIdx].lessons, newLesson]
    };

    const updatedCurriculum = [...current.curriculum];
    updatedCurriculum[cIdx] = updatedChap;

    // Synchronize to materials simultaneously
    let updatedMaterials = [...current.materials];
    if (lesson.type === 'download' || lesson.type === 'text' || lesson.type === 'video' || lesson.type === 'live' || ((lesson.type === 'quiz' || lesson.type === 'assignment') && lesson.fileName)) {
      let matType: 'pdf' | 'video' | 'code' | 'slides' | 'cheatsheet' = 'code';
      if (lesson.type === 'video') {
        matType = 'video';
      } else if (lesson.type === 'text') {
        matType = 'pdf';
      } else if (lesson.type === 'live') {
        matType = 'slides';
      } else {
        const ext = (lesson.fileName || '').split('.').pop()?.toLowerCase();
        if (ext === 'pdf') matType = 'pdf';
        else if (ext === 'pptx' || ext === 'ppt') matType = 'slides';
        else if (ext === 'zip' || ext === 'tar' || ext === 'gz' || ext === 'py' || ext === 'ts' || ext === 'js' || ext === 'json' || ext === 'sql') matType = 'code';
        else matType = 'code';
      }

      const resUrl = lesson.type === 'video'
        ? (newLesson.videoUrl || lesson.videoUrl || 'https://storage.googleapis.com/ase-recordings/demo-lecture.mp4')
        : (newLesson.downloadUrl && newLesson.downloadUrl !== '#' ? newLesson.downloadUrl : meetingUrl);

      const displaySize = lesson.type === 'video'
        ? (newLesson.duration || '15 mins')
        : (newLesson.fileSize || '2.5 MB');

      const titleSuffix = lesson.type === 'live'
        ? ' (Session Handout & Notes)'
        : lesson.type === 'quiz'
          ? ' (Quiz Reference Assets)'
          : lesson.type === 'assignment'
            ? ' (Assignment Starter Kit)'
            : '';

      const deptName = newLesson.departmentName || updatedChap.departmentName || 'All / Common';
      const deptId = newLesson.departmentId || updatedChap.departmentId;

      updatedMaterials.unshift({
        id: `mat-${newLesson.id}`,
        title: newLesson.title + titleSuffix,
        module: updatedChap.title,
        type: matType,
        size: displaySize,
        uploadedAt: 'Just now',
        author: this.getCurrentUser().full_name + ' (Teacher)',
        downloadUrl: resUrl,
        videoUrl: lesson.type === 'video' ? resUrl : undefined,
        fileName: lesson.fileName,
        description: newLesson.description || newLesson.textNotes || 'Curriculum resource provided by instructor.',
        isBookmarked: false,
        departmentName: deptName,
        departmentId: deptId
      });
    }

    // Synchronize to training sessions (timetable) simultaneously
    let updatedSessions = [...current.sessions];
    if (lesson.type === 'live') {
      const liveTrainer = (lesson as any).trainer || this.getCurrentUser().full_name;
      const deptName = newLesson.departmentName || updatedChap.departmentName || 'All / Common';
      const deptId = newLesson.departmentId || updatedChap.departmentId;
      updatedSessions.unshift({
        id: `sess-${newLesson.id}`,
        title: newLesson.title,
        module: updatedChap.title,
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
      const deptName = newLesson.departmentName || updatedChap.departmentName || 'All / Common';
      const deptId = newLesson.departmentId || updatedChap.departmentId;
      updatedAssignments.unshift({
        id: `asg-${newLesson.id}`,
        title: newLesson.title,
        module: updatedChap.title,
        description: newLesson.description || 'Complete the practical task according to rubric.',
        points: 100,
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
      const deptName = newLesson.departmentName || updatedChap.departmentName || 'All / Common';
      const deptId = newLesson.departmentId || updatedChap.departmentId;
      updatedQuizzes.unshift({
        id: `quiz-${newLesson.id}`,
        title: newLesson.title,
        module: updatedChap.title,
        questionsCount: 5,
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

    const teacherName = startedByTrainerName || this.getCurrentUser().full_name || current.details.leadTrainer?.name || 'Priya Sharma';

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
        updatedDetails.activeLiveTrainer = (nextUp.trainer && nextUp.trainer !== 'Current User') ? nextUp.trainer : (current.details.leadTrainer?.name || 'Priya Sharma');
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
    const defaultTrainer = this.getCurrentUser().full_name || current.details.leadTrainer?.name || 'Priya Sharma';

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
    this.saveState({
      ...current,
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
  }): void {
    const current = this.getCohortData();
    const newQuiz: CohortQuiz = {
      id: `quiz-${Date.now()}`,
      title: quiz.title,
      module: quiz.module,
      questionsCount: quiz.questionsCount || 5,
      durationMinutes: quiz.durationMinutes || 15,
      dueDate: 'Scheduled by Instructor',
      passingScore: quiz.passingScore || 70,
      status: 'available',
      questions: [
        {
          id: 1,
          text: `Sample Checkpoint question for ${quiz.title}?`,
          options: ['Option A (Correct standard)', 'Option B', 'Option C', 'Option D'],
          correctIndex: 0,
          explanation: 'Demonstrates baseline comprehension of module principles.'
        }
      ]
    };

    this.saveState({
      ...current,
      quizzes: [...current.quizzes, newQuiz],
      progress: {
        ...current.progress,
        totalQuizzes: current.progress.totalQuizzes + 1
      }
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
  }

  deleteAnnouncement(annId: string): void {
    const current = this.getCohortData();
    this.saveState({
      ...current,
      announcements: current.announcements.filter(a => a.id !== annId)
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
    return true;
  }

  submitAssignment(assignmentId: string, submissionUrl: string, notes: string): boolean {
    const current = this.getCohortData();
    const asgIndex = current.assignments.findIndex(a => a.id === assignmentId);
    if (asgIndex === -1) return false;

    const target = current.assignments[asgIndex];
    const isFirstSubmission = target.status === 'pending';

    const updatedAssignment: CohortAssignment = {
      ...target,
      status: 'submitted',
      submissionDate: new Date().toISOString(),
      submissionUrl,
      submissionNotes: notes,
      dueRelative: 'Submitted — Under Review',
      trainerFeedback: 'Submission received successfully and queued for trainer evaluation.'
    };

    const newAssignments = [...current.assignments];
    newAssignments[asgIndex] = updatedAssignment;

    const newSubmittedCount = isFirstSubmission
      ? current.progress.assignmentsSubmitted + 1
      : current.progress.assignmentsSubmitted;

    const updated: CohortFullData = {
      ...current,
      assignments: newAssignments,
      progress: {
        ...current.progress,
        assignmentsSubmitted: newSubmittedCount
      }
    };

    this.saveState(updated);
    return true;
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
  }
}
