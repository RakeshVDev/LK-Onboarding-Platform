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
}

export interface CurriculumChapter {
  id: string;
  title: string;
  sequenceOrder: number;
  isExpanded?: boolean;
  lessons: CurriculumLesson[];
}

export interface TrainingSession {
  id: string;
  title: string;
  module: string;
  trainer: string;
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
  private readonly storageKey = 'ase_cohort_state_v2';
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
      id: 15,
      full_name: 'Priya Sharma',
      email: 'priya.sharma@example.com',
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
      if (!data.details.activeLiveTrainer || data.details.activeLiveTrainer === 'Current User') {
        data.details.activeLiveTrainer = data.details.leadTrainer?.name || 'Priya Sharma';
      }
    }

    if (data && data.sessions) {
      const defaultTrainer = data.details?.leadTrainer?.name || 'Priya Sharma';
      for (const s of data.sessions) {
        if (!s.trainer || s.trainer === 'Current User') {
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
      activeBatchId: 'cohort-ase-2026-q1',

      // Screenshot 1: Batches List
      batches: [
        {
          id: 'cohort-ase-2026-q1',
          name: 'ASE Full-Stack Batch 2026-Q1',
          learnerCount: 16,
          startDate: '15 Oct 2026',
          endDate: '15 Jan 2027',
          status: 'current',
          description: 'Intensive Full-Stack & Cloud Architecture program for ASE joinees.',
          track: 'Associate Software Engineer — Full-Stack'
        },
        {
          id: 'batch-demo-28',
          name: 'Demo Batch 28',
          learnerCount: 6,
          startDate: '03 Jan 2026',
          endDate: '28 Jul 2026',
          status: 'current',
          description: 'Specialized backend microservices sprint track.',
          track: 'Backend Engineering'
        },
        {
          id: 'batch-bright-future',
          name: 'Bright Future',
          learnerCount: 18,
          startDate: '30 Jun 2026',
          endDate: '30 Jun 2027',
          status: 'current',
          description: 'Graduate engineering trainee cohort for foundational software development.',
          track: 'GET Enterprise Onboarding'
        },
        {
          id: 'batch-june-19',
          name: "June '25 - November '25",
          learnerCount: 10,
          startDate: '01 Jun 2025',
          endDate: '30 Nov 2025',
          status: 'alumni',
          description: 'Completed alumni engineering batch.',
          track: 'Cloud & Full-Stack'
        }
      ],

      details: {
        id: 'cohort-ase-2026-q1',
        name: 'Full-Stack Engineering ASE Batch 2026-Q1',
        code: 'ASE-FS-01',
        department: 'Engineering & Technology',
        track: 'Associate Software Engineer — Full-Stack & Cloud',
        status: 'active',
        startDate: '2026-10-15',
        endDate: '2027-01-15',
        durationWeeks: 12,
        currentWeek: 4,
        currentModule: 'Module 3: Angular Reactive Architecture & State Management',
        leadTrainer: {
          name: 'Priya Sharma',
          title: 'Staff Engineer & Lead Technical Instructor',
          email: 'priya.sharma@example.com',
          avatar: 'PS',
          officeHours: 'Mon & Thu: 4:00 PM – 5:30 PM IST',
          bio: '10+ years designing distributed systems, high-throughput microservices, and leading enterprise software engineering teams.'
        },
        mentors: [
          {
            name: 'Vikram Joshi',
            title: 'Senior Cloud Architect',
            email: 'vikram.j@example.com',
            avatar: 'VJ'
          },
          {
            name: 'Ananya Roy',
            title: 'Principal Frontend Engineer',
            email: 'ananya.r@example.com',
            avatar: 'AR'
          }
        ],
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
          title: '1. Getting Started',
          sequenceOrder: 1,
          isExpanded: true,
          lessons: [
            {
              id: 'les-1',
              title: 'Welcome to the Course & Onboarding Briefing',
              type: 'text',
              description: 'Orientation to development workflows, code standards, and sprint expectations.',
              textNotes: 'Welcome to the ASE Batch! Please review the developer environment guidelines and clone our starter repository.',
              isPublished: true
            },
            {
              id: 'les-2',
              title: 'Course Overview & System Architecture',
              type: 'video',
              duration: '05:21',
              description: 'High-level walkthrough of the platform microservices architecture and module milestones.',
              videoUrl: 'https://storage.googleapis.com/ase-recordings/course-overview.mp4',
              isPublished: true
            },
            {
              id: 'les-3',
              title: 'Downloadable Resources & Environment Setup Script',
              type: 'download',
              description: 'CLI installation scripts, Docker Compose files, and local database seeds.',
              downloadUrl: '#',
              fileSize: '4.2 MB',
              isPublished: true
            }
          ]
        },
        {
          id: 'chap-2',
          title: '2. Core Concepts: Microservices & Data Modeling',
          sequenceOrder: 2,
          isExpanded: true,
          lessons: [
            {
              id: 'les-4',
              title: 'Understanding the Basics: FastAPI & Clean Architecture',
              type: 'video',
              duration: '12:45',
              description: 'Hands-on breakdown of routers, service layers, and repository decoupling.',
              videoUrl: 'https://storage.googleapis.com/ase-recordings/fastapi-basics.mp4',
              isPublished: true
            },
            {
              id: 'les-5',
              title: 'Key Principles of Resilient Database Indexing',
              type: 'text',
              description: 'B-tree index structures, composite key order, and query planning.',
              textNotes: 'Index order matters: (tenant_id, created_at) enables prefix range searches while isolating customer records.',
              isPublished: true
            },
            {
              id: 'les-6',
              title: 'Quick Checkpoint Quiz: SQL & Concurrency',
              type: 'quiz',
              quizQuestionsCount: 5,
              description: '5-question sprint checkpoint evaluating query analysis and deadlock mitigation.',
              isPublished: true
            }
          ]
        },
        {
          id: 'chap-3',
          title: '3. Putting It into Practice: Reactive Frontend & Delivery',
          sequenceOrder: 3,
          isExpanded: true,
          lessons: [
            {
              id: 'les-7',
              title: 'Real World Examples: Angular Signals in High-Volume SPAs',
              type: 'video',
              duration: '08:15',
              description: 'Refactoring state services to signals for zero Zone.js overhead.',
              videoUrl: 'https://storage.googleapis.com/ase-recordings/angular-signals-demo.mp4',
              isPublished: true
            },
            {
              id: 'les-8',
              title: 'Practical Case Study: Distributed Cache Invalidation',
              type: 'text',
              description: 'Production war-stories solving cache stampede and stale session data.',
              textNotes: 'Use probabilistic early expiration (XFetch) or pub/sub cache invalidation over blanket short TTLs.',
              isPublished: true
            },
            {
              id: 'les-9',
              title: 'Live Lab Workshop: Real-Time Telemetry Dashboard',
              type: 'live',
              duration: '2.5 Hours',
              description: 'Interactive live coding session with Lead Trainer Priya Sharma.',
              isPublished: true
            },
            {
              id: 'les-10',
              title: 'Assignment 3: Reactive State Management Implementation',
              type: 'assignment',
              description: 'Build a signal-driven monitoring module with unit tests.',
              isPublished: true
            }
          ]
        }
      ],

      // Screenshot 5: Training Schedule & Live Sessions
      sessions: [
        {
          id: 'sess-today',
          title: 'Daily UX Writing & Frontend State Architecture',
          module: 'Module 3: Frontend Mastery',
          trainer: 'Priya Sharma',
          date: 'Today (Live Session)',
          time: '10:00 AM – 12:30 PM IST',
          duration: '2.5 Hours',
          status: 'today',
          location: 'Virtual Classroom 1 (Google Meet)',
          meetingUrl: 'https://meet.google.com/ase-cohort-live',
          slidesUrl: '#',
          topics: [
            'Fine-grained reactivity with Angular Signals',
            'Signal-based computed properties and effects',
            'Migrating BehaviorSubject services to Signals',
            'Component communication without unnecessary re-renders'
          ],
          isAttended: true
        },
        {
          id: 'sess-2',
          title: 'Deep Dive: Reactive Forms, Custom Validators & Async Directives',
          module: 'Module 3: Frontend Mastery',
          trainer: 'Ananya Roy',
          date: 'Tomorrow, 10:00 AM IST',
          time: '10:00 AM – 12:00 PM IST',
          duration: '2 Hours',
          status: 'upcoming',
          location: 'Virtual Classroom 1 (Google Meet)',
          meetingUrl: 'https://meet.google.com/ase-cohort-live',
          topics: [
            'Typed Reactive FormGroups and FormArrays',
            'Cross-field asynchronous validation with backend checks',
            'Custom UI control value accessors',
            'Optimistic updates and user error boundary handling'
          ]
        },
        {
          id: 'sess-3',
          title: 'Guest Lecture: Observability, OpenTelemetry & Distributed Tracing',
          module: 'Module 4: Systems & Cloud',
          trainer: 'Vikram Joshi (Guest Architect)',
          date: 'Friday, Nov 07, 2:00 PM IST',
          time: '2:00 PM – 4:00 PM IST',
          duration: '2 Hours',
          status: 'upcoming',
          location: 'Auditorium Stream & Q&A',
          meetingUrl: 'https://meet.google.com/ase-cohort-live',
          topics: [
            'Distributed tracing across microservices',
            'Structured logging with correlation IDs',
            'Prometheus metrics and Grafana dashboards',
            'Alerting thresholds and incident response runbooks'
          ]
        },
        {
          id: 'sess-4',
          title: 'Hands-on Workshop: FastAPI Clean Architecture & Dependency Injection',
          module: 'Module 2: Microservices Backend',
          trainer: 'Priya Sharma',
          date: 'Completed — Earlier This Week',
          time: '10:00 AM – 12:30 PM IST',
          duration: '2.5 Hours',
          status: 'completed',
          location: 'Virtual Classroom 1',
          meetingUrl: 'https://meet.google.com/ase-cohort-live',
          recordingUrl: 'https://storage.googleapis.com/ase-recordings/mod2-fastapi-clean-arch.mp4',
          slidesUrl: '#',
          topics: [
            'Layered service architecture (Routers, Services, Repositories)',
            'Dependency injection patterns in FastAPI',
            'Pydantic v2 schemas and validation contracts',
            'Custom exception handlers and middleware'
          ],
          isAttended: true
        },
        {
          id: 'sess-5',
          title: 'SQL Mastery: Execution Plans, Index Tuning & Isolation Levels',
          module: 'Module 2: Microservices Backend',
          trainer: 'Vikram Joshi',
          date: 'Completed — Last Week',
          time: '10:00 AM – 12:00 PM IST',
          duration: '2 Hours',
          status: 'completed',
          location: 'Virtual Classroom 1',
          meetingUrl: 'https://meet.google.com/ase-cohort-live',
          recordingUrl: 'https://storage.googleapis.com/ase-recordings/mod2-sql-execution-tuning.mp4',
          slidesUrl: '#',
          topics: [
            'B-Tree vs Hash vs GIN indexes in PostgreSQL',
            'EXPLAIN ANALYZE deep dive and cost modeling',
            'Transaction isolation levels (Read Committed vs Serializable)',
            'Deadlock prevention and advisory locking'
          ],
          isAttended: true
        }
      ],

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
          isBookmarked: true
        },
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
          isBookmarked: true
        },
        {
          id: 'mat-3',
          title: 'PostgreSQL Query Optimization & Indexing Cheat Sheet',
          module: 'Module 2: Microservices Backend',
          type: 'cheatsheet',
          size: '850 KB (PDF)',
          uploadedAt: '1 week ago',
          author: 'Vikram Joshi (Senior Architect)',
          downloadUrl: '#',
          description: 'Quick-reference guide for reading EXPLAIN ANALYZE output, composite index column order, and VACUUM maintenance.'
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
          description: 'Architectural blueprints explaining dual writes prevention, transactional outbox pattern, and distributed event streaming.'
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
          description: '45-minute screencast demonstrating minimal distroless Docker images for Python and Node.js with zero CVE footprint.'
        }
      ],

      assignments: [
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
          requirements: [
            'Cache-aside read/write implementation with Redis',
            'Cache invalidation hook on product mutation',
            'Minimum 90% unit test coverage with pytest-mock',
            'Graceful degradation when Redis cluster is unreachable'
          ]
        },
        {
          id: 'asg-2',
          title: 'Assignment 2: JWT & Role-Based Access Control Implementation',
          module: 'Module 2: Microservices Backend',
          description: 'Design and implement an end-to-end authentication microservice featuring access & refresh token rotation, password hashing with Argon2id, and granular RBAC middleware.',
          points: 100,
          dueDate: '2026-11-02',
          dueRelative: 'Completed & Graded',
          status: 'graded',
          submissionDate: '2026-11-01T21:15:00Z',
          submissionUrl: 'https://github.com/learner/ase-auth-service',
          submissionNotes: 'Implemented asymmetric RS256 key signing, token revocation list in Redis, and declarative role check decorators.',
          score: 92,
          trainerFeedback: 'Great work on the token rotation mechanism. Make sure to log revoked token reuse as high-severity security events.',
          requirements: [
            'Argon2id password hashing with custom salt',
            'Short-lived access tokens (15m) + secure refresh tokens (7d)',
            'Role and permission claim validation in FastAPI dependencies',
            'Test suite verifying unauthorized and forbidden routes'
          ]
        },
        {
          id: 'asg-3',
          title: 'Assignment 3: Reactive State Management with Angular Signals',
          module: 'Module 3: Frontend Mastery',
          description: 'Build an interactive dashboard module that consumes real-time telemetry updates using Angular 17+ Signals, computed metrics, and clean component decomposition.',
          points: 100,
          dueDate: '2026-11-08',
          dueRelative: 'Due in 3 days',
          status: 'submitted',
          submissionDate: '2026-11-04T19:40:00Z',
          submissionUrl: 'https://github.com/learner/ase-angular-telemetry-dashboard',
          submissionNotes: 'Completed all core criteria: signal stores, computed summaries, offline fallback, and 0 zone.js overhead.',
          trainerFeedback: 'Submission received and currently under review by Priya Sharma.',
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
          dueRelative: 'Due in 9 days',
          status: 'pending',
          requirements: [
            'Multi-stage Dockerfile producing < 100MB container',
            'Non-root user execution inside container',
            'Docker Compose with healthcheck dependency ordering',
            'GitHub Actions pipeline with caching and test reporting'
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
        {
          id: 'quiz-1',
          title: 'Sprint 1 Knowledge Check: Python Internals & OOP',
          module: 'Module 1: Architecture Foundations',
          questionsCount: 10,
          durationMinutes: 15,
          dueDate: 'Oct 22, 2026',
          passingScore: 70,
          status: 'completed',
          score: 90,
          passed: true,
          completedAt: '2026-10-21T16:00:00Z',
          questions: []
        },
        {
          id: 'quiz-2',
          title: 'Sprint 2 Knowledge Check: FastAPI, Pydantic & SQLAlchemy',
          module: 'Module 2: Microservices Backend',
          questionsCount: 10,
          durationMinutes: 15,
          dueDate: 'Oct 30, 2026',
          passingScore: 70,
          status: 'completed',
          score: 85,
          passed: true,
          completedAt: '2026-10-29T14:20:00Z',
          questions: []
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
        {
          id: 'quiz-4',
          title: 'Sprint 4 Checkpoint: Docker, CI/CD & Cloud Infrastructure',
          module: 'Module 4: Systems & Cloud',
          questionsCount: 10,
          durationMinutes: 15,
          dueDate: 'Nov 16, 2026',
          passingScore: 70,
          status: 'upcoming',
          questions: []
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

      // Check active logged in user snapshot & sessionStorage
      const activeUser = this.authService?.getCurrentUserSnapshot();
      if (
        activeUser &&
        activeUser.role === 'learner' &&
        activeUser.email &&
        !existingEmails.has(activeUser.email.toLowerCase().trim())
      ) {
        managedUsers.push({
          id: activeUser.id || Date.now(),
          full_name: activeUser.full_name || 'Current Learner',
          email: activeUser.email,
          role: 'learner',
          is_active: true,
          created_at: activeUser.created_at || new Date().toISOString()
        });
        existingEmails.add(activeUser.email.toLowerCase().trim());
      }

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
        const email = learner.email?.toLowerCase().trim() || '';
        const name = learner.full_name?.trim() || 'Platform Learner';
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
    learnerNames: string[] = []
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
      track: track || 'Associate Software Engineer Track',
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
        track: target.track || current.details.track
      }
    });
  }

  // ---------------------------------------------------------------------------
  // TEACHER ACTION: CURRICULUM & SYLLABUS BUILDER (SCREENSHOTS 2 & 3)
  // ---------------------------------------------------------------------------
  addChapter(title: string): CurriculumChapter {
    const current = this.getCohortData();
    const newChap: CurriculumChapter = {
      id: `chap-${Date.now()}`,
      title,
      sequenceOrder: current.curriculum.length + 1,
      isExpanded: true,
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
      trainer: resolvedTrainer
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
        isBookmarked: false
      });
    }

    // Synchronize to training sessions (timetable) simultaneously
    let updatedSessions = [...current.sessions];
    if (lesson.type === 'live') {
      const liveTrainer = (lesson as any).trainer || this.getCurrentUser().full_name;
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
        topics: [newLesson.description || newLesson.title]
      });
    }

    let updatedAssignments = [...current.assignments];
    if (lesson.type === 'assignment') {
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
        requirements: ['Code implementation meeting specification', 'Unit tests passing 85%+']
      });
    }

    let updatedQuizzes = [...current.quizzes];
    if (lesson.type === 'quiz') {
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
    date: string;
    time: string;
    duration: string;
    location: string;
    meetingUrl: string;
    topics: string[];
    isLiveNow?: boolean;
  }): TrainingSession {
    const current = this.getCohortData();
    const isLive = !!session.isLiveNow;
    const newSession: TrainingSession = {
      id: `sess-${Date.now()}`,
      title: session.title,
      module: session.module,
      trainer: session.trainer || this.getCurrentUser().full_name,
      date: session.date,
      time: session.time,
      duration: session.duration || '2 Hours',
      status: isLive ? 'today' : 'upcoming',
      location: session.location || 'Virtual Classroom 1 (Google Meet)',
      meetingUrl: session.meetingUrl || current.details.meetingLink,
      topics: session.topics && session.topics.length > 0 ? session.topics : [session.title]
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
        startedSession = {
          ...s,
          trainer: teacherName,
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
      updatedDetails.activeLiveTrainer = teacherName;
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
    const user = this.getCurrentUser();
    const isInstructorUser = user.role === 'teacher' || user.role === 'admin' || user.role === 'superadmin';
    const defaultTrainer = (isInstructorUser ? user.full_name : '') || current.details.leadTrainer?.name || 'Priya Sharma';

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
      requirements: asg.requirements || ['Implement required functionality', 'Add comprehensive test cases']
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
