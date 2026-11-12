import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { AssessmentStatusService } from '../../../core/services/assessment-status.service';

export interface AssessmentCategory {
  label: string;
  question_count: number;
}

export interface AssessmentTemplate {
  id: number;
  name: string;
  assessment_type: "psychometric" | "technical" | "english_grammar" | "logical_reasoning" | "programming";
  description: string | null;
  question_count: number;
  duration_minutes?: number;
  category_config: Record<string, AssessmentCategory>;
  is_active: boolean;
  created_by_user_id: number;
  created_at: string;
  assignment_scope?: 'all' | 'cohort' | 'learner' | string;
  assigned_cohort_ids?: number[];
  assigned_learner_ids?: number[];
  assigned_count?: number;
  assignment_summary?: string;
  due_at?: string | null;
}

export interface CreateAssessmentTemplate {
  name: string;
  assessment_type?: "psychometric" | "technical" | "english_grammar" | "logical_reasoning" | "programming";
  description: string | null;
  question_count: number;
  category_config: Record<string, AssessmentCategory>;
  assignment_scope?: 'all' | 'cohort' | 'learner';
  cohort_ids?: number[];
  learner_ids?: number[];
  due_at?: string | null;
}

export interface UpdateAssessmentTemplate {
  name?: string;
  assessment_type?: "psychometric" | "technical" | "english_grammar" | "logical_reasoning" | "programming";
  description?: string | null;
  question_count?: number;
  category_config?: Record<string, AssessmentCategory>;
  is_active?: boolean;
  assignment_scope?: 'all' | 'cohort' | 'learner';
  cohort_ids?: number[];
  learner_ids?: number[];
  due_at?: string | null;
  clear_due_at?: boolean;
}

export type AssessmentAssignmentStatus =
  | 'NOT_STARTED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'EXPIRED';

export interface AssessmentAssignmentPayload {
  scope: 'all' | 'cohort' | 'learner';
  cohort_ids: number[];
  learner_ids: number[];
  due_at?: string | null;
}

export interface AssessmentAssignmentTargetSummary {
  template_id: number;
  scope: 'all' | 'cohort' | 'learner' | string;
  cohort_ids: number[];
  learner_ids: number[];
  assigned_count: number;
  due_at?: string | null;
}

export interface AssignableCohortItem {
  id: number;
  name: string;
  status: string;
  department_id: number;
  member_count: number;
}

export interface AssignableLearnerItem {
  id: number;
  full_name: string;
  email: string;
  cohort_ids: number[];
}

export interface AssignableTargetsResponse {
  cohorts: AssignableCohortItem[];
  learners: AssignableLearnerItem[];
}

export interface StudentAssignedAssessmentItem {
  template_id: number;
  assignment_id?: number | null;
  assignment_scope: 'all' | 'cohort' | 'learner' | string;
  cohort_name?: string | null;
  name: string;
  description?: string | null;
  assessment_type:
    | 'psychometric'
    | 'technical'
    | 'english_grammar'
    | 'logical_reasoning'
    | 'programming'
    | string;
  category_label: string;
  question_count: number;
  duration_minutes: number;
  status: AssessmentAssignmentStatus;
  assigned_at: string;
  due_at?: string | null;
  session_id?: number | null;
  started_at?: string | null;
  expires_at?: string | null;
  completed_at?: string | null;
  remaining_seconds?: number | null;
  total_score?: number | null;
  max_score?: number | null;
  overall_percentage?: number | null;
  has_report: boolean;
  tab_switch_count: number;
  can_start: boolean;
  can_continue: boolean;
  notification_title?: string | null;
}

export interface StudentAssignedStats {
  total_assigned: number;
  not_started_count: number;
  in_progress_count: number;
  completed_count: number;
  expired_count: number;
  average_score: number;
}

export interface StudentAssignedAssessmentsResponse {
  assessments: StudentAssignedAssessmentItem[];
  notifications: StudentAssignedAssessmentItem[];
  stats: StudentAssignedStats;
  cohort_names: string[];
  synced_at: string;
}

export interface AssessmentOption {
  id: string;
  text: string;
}

export interface AssessmentQuestion {
  id: number;
  category: string;
  difficulty?: 'Easy' | 'Medium' | 'Hard' | string;
  question_type: string;
  question_text: string;
  instructions?: string | null;
  options: AssessmentOption[];
  display_order: number;
  max_score?: number;
  negative_marks?: number;
}

export interface AssessmentStartResponse {
  session_id: number;
  status: string;
  question_count: number;
  duration_minutes?: number;
  remaining_seconds?: number;
  started_at: string;
  expires_at?: string;
  template_name?: string;
  assessment_type?: string;
  questions: AssessmentQuestion[];
}

export interface AssessmentResumeResponse {
  session_id: number;
  status: string;
  question_count: number;
  duration_minutes?: number;
  remaining_seconds?: number;
  started_at: string;
  expires_at?: string;
  template_name?: string;
  assessment_type?: string;
  saved_answers?: Record<number, string>;
  marked_for_review?: number[];
  questions: AssessmentQuestion[];
}

export interface AssessmentAnswer {
  question_id: number;
  answer: string;
}

export interface AssessmentSubmitResponse {
  session_id: number;
  status: string;
  completed_at: string;
  message: string;
}

export interface CategoryScore {
  category: string;
  score: number;
  max_score: number;
  percentage: number;
}

export interface AssessmentScoresResponse {
  session_id: number;
  template_id?: number;
  template_name?: string;
  assessment_type?: string;
  learner_user_id?: number;
  learner_name?: string;
  learner_email?: string;
  status?: string;
  completed_at?: string;
  categories: CategoryScore[];
  total_questions: number;
  answered_count: number;
  unanswered_count: number;
  total_score: number;
  max_score: number;
  overall_percentage: number;
  tab_switch_count?: number;
}

export interface AssessmentReportData {
  report_title?: string;
  skill_level?: string;
  total_questions?: number;
  correct_answers?: number;
  incorrect_answers?: number;
  unattempted_questions?: number;
  time_taken_str?: string;
  tab_switch_count?: number;
  proctoring_status?: string;
  summary: string;
  strengths: string[];
  development_areas: string[];
  recommendations: string[];
  category_interpretations: Record<string, string>;
  overall_percentage?: number;
  total_score?: number;
  max_score?: number;
  category_scores?: CategoryScore[];
  [key: string]: any;
}

export interface AssessmentReport {
  id: number;
  session_id: number;
  template_id?: number;
  template_name?: string;
  assessment_type?: string;
  learner_user_id?: number;
  learner_name?: string;
  learner_email?: string;
  report_data: AssessmentReportData;
  report_text: string;
  ai_model: string;
  generated_at: string;
}

export interface UserAssessmentResultItem {
  session_id: number;
  template_id: number;
  template_name: string;
  assessment_type: string;
  learner_user_id: number;
  learner_name?: string;
  learner_email?: string;
  status: string;
  question_count: number;
  total_score: number;
  max_score: number;
  overall_percentage: number;
  started_at: string;
  completed_at?: string;
  has_report: boolean;
  categories: CategoryScore[];
  tab_switch_count?: number;
}

export interface AdminAssessmentResultsResponse {
  results: UserAssessmentResultItem[];
  total_assessments: number;
  completed_count: number;
  average_score: number;
  unique_learners: number;
}

export interface BankQuestionOption {
  id: string;
  text: string;
}

export interface BankQuestion {
  id: number;
  template_id: number;
  category: string;
  difficulty: 'Easy' | 'Medium' | 'Hard' | string;
  question_type: string;
  question_text: string;
  instructions?: string | null;
  explanation?: string | null;
  options: BankQuestionOption[];
  max_score: number;
  negative_marks?: number;
  display_order?: number | null;
  in_assessment?: boolean;
  is_active: boolean;
  correct_option_id?: string;
  correct_option_ids?: string[];
}

export interface CreateBankQuestionPayload {
  category: string;
  difficulty: 'Easy' | 'Medium' | 'Hard' | string;
  question_type?: string;
  question_text: string;
  instructions?: string | null;
  explanation?: string | null;
  options: BankQuestionOption[];
  correct_option_id?: string;
  correct_option_ids?: string[];
  max_score?: number;
  negative_marks?: number;
  in_assessment?: boolean;
}

export interface UpdateBankQuestionPayload {
  category?: string;
  difficulty?: 'Easy' | 'Medium' | 'Hard' | string;
  question_type?: string;
  question_text?: string;
  instructions?: string | null;
  explanation?: string | null;
  options?: BankQuestionOption[];
  correct_option_id?: string;
  correct_option_ids?: string[];
  max_score?: number;
  negative_marks?: number;
  in_assessment?: boolean;
}

export interface PreviewQuestionItem {
  id: number;
  source?: 'bank' | 'builtin' | string;
  category: string;
  difficulty?: string;
  question_type: string;
  question_text: string;
  instructions?: string | null;
  options: AssessmentOption[];
  display_order: number;
  max_score: number;
  negative_marks?: number;
  correct_option_id?: string | null;
  correct_option_ids?: string[] | null;
  explanation?: string | null;
}

export interface AssessmentTemplatePreview {
  template_id: number;
  template_name: string;
  assessment_type: string;
  description?: string | null;
  instructions: string;
  mode: 'student' | 'admin' | string;
  duration_minutes: number;
  total_questions: number;
  configured_question_count: number;
  custom_question_count: number;
  builtin_question_count: number;
  total_marks: number;
  questions: PreviewQuestionItem[];
}

@Injectable({
  providedIn: 'root'
})
export class AssessmentService {

  private readonly http = inject(HttpClient);
  private readonly assessmentStatusService = inject(AssessmentStatusService);

  private readonly apiUrl =
    '/training-api/api/v1/assessments';

  readonly syncVersion = signal(0);

  notifyStatusChanged(): void {
    this.assessmentStatusService.clearCache();
    this.syncVersion.update(v => v + 1);
  }

  // ----------------------------------
  // Assessment templates
  // ----------------------------------

  getTemplates(): Observable<AssessmentTemplate[]> {
    return this.http.get<AssessmentTemplate[]>(
      `${this.apiUrl}/templates`
    );
  }

  getMyAssignedAssessments(): Observable<StudentAssignedAssessmentsResponse> {
    return this.http.get<StudentAssignedAssessmentsResponse>(
      `${this.apiUrl}/my/assigned`
    );
  }

  getAssignableTargets(): Observable<AssignableTargetsResponse> {
    return this.http.get<AssignableTargetsResponse>(
      `${this.apiUrl}/assignable-targets`
    );
  }

  getTemplateAssignments(
    templateId: number
  ): Observable<AssessmentAssignmentTargetSummary> {
    return this.http.get<AssessmentAssignmentTargetSummary>(
      `${this.apiUrl}/templates/${templateId}/assignments`
    );
  }

  updateTemplateAssignments(
    templateId: number,
    payload: AssessmentAssignmentPayload
  ): Observable<AssessmentAssignmentTargetSummary> {
    return this.http.put<AssessmentAssignmentTargetSummary>(
      `${this.apiUrl}/templates/${templateId}/assignments`,
      payload
    ).pipe(
      tap(() => this.notifyStatusChanged())
    );
  }

  getTemplate(id: number): Observable<AssessmentTemplate> {
    return this.http.get<AssessmentTemplate>(
      `${this.apiUrl}/templates/${id}`
    );
  }

  getBankQuestions(templateId: number, includeUnassigned = true): Observable<BankQuestion[]> {
    const params = new HttpParams().set('include_unassigned', String(includeUnassigned));
    return this.http.get<BankQuestion[]>(
      `${this.apiUrl}/templates/${templateId}/questions`,
      { params }
    );
  }

  createBankQuestion(
    templateId: number,
    data: CreateBankQuestionPayload
  ): Observable<BankQuestion> {
    return this.http.post<BankQuestion>(
      `${this.apiUrl}/templates/${templateId}/questions`,
      data
    );
  }

  updateBankQuestion(
    templateId: number,
    questionId: number,
    data: UpdateBankQuestionPayload
  ): Observable<BankQuestion> {
    return this.http.put<BankQuestion>(
      `${this.apiUrl}/templates/${templateId}/questions/${questionId}`,
      data
    );
  }

  reorderBankQuestions(
    templateId: number,
    questionIds: number[]
  ): Observable<BankQuestion[]> {
    return this.http.put<BankQuestion[]>(
      `${this.apiUrl}/templates/${templateId}/questions/reorder`,
      { question_ids: questionIds }
    );
  }

  removeQuestionFromAssessment(
    templateId: number,
    questionId: number
  ): Observable<BankQuestion[]> {
    return this.http.post<BankQuestion[]>(
      `${this.apiUrl}/templates/${templateId}/questions/${questionId}/remove`,
      {}
    );
  }

  assignQuestionToAssessment(
    templateId: number,
    questionId: number
  ): Observable<BankQuestion[]> {
    return this.http.post<BankQuestion[]>(
      `${this.apiUrl}/templates/${templateId}/questions/${questionId}/assign`,
      {}
    );
  }

  deleteBankQuestion(
    templateId: number,
    questionId: number
  ): Observable<void> {
    return this.http.delete<void>(
      `${this.apiUrl}/templates/${templateId}/questions/${questionId}`
    );
  }

  previewTemplate(
    templateId: number,
    mode: 'student' | 'admin' = 'student',
    customOnly = false
  ): Observable<AssessmentTemplatePreview> {
    const params = new HttpParams()
      .set('mode', mode)
      .set('custom_only', String(customOnly));
    return this.http.get<AssessmentTemplatePreview>(
      `${this.apiUrl}/templates/${templateId}/preview`,
      { params }
    );
  }

  resumeAssessment(
    sessionId: number
  ): Observable<AssessmentResumeResponse> {
    return this.http.get<AssessmentResumeResponse>(
      `${this.apiUrl}/sessions/${sessionId}/resume`
    );
  }

  createTemplate(
    data: CreateAssessmentTemplate
  ): Observable<AssessmentTemplate> {
    return this.http.post<AssessmentTemplate>(
      `${this.apiUrl}/templates`,
      data
    ).pipe(
      tap(() => this.notifyStatusChanged())
    );
  }

  updateTemplate(
    id: number,
    data: UpdateAssessmentTemplate
  ): Observable<AssessmentTemplate> {
    return this.http.put<AssessmentTemplate>(
      `${this.apiUrl}/templates/${id}`,
      data
    ).pipe(
      tap(() => this.notifyStatusChanged())
    );
  }

  // ----------------------------------
  // Start assessment
  // ----------------------------------

  startAssessment(
    templateId: number,
    forceNew: boolean = false
  ): Observable<AssessmentStartResponse> {
    return this.http.post<AssessmentStartResponse>(
      `${this.apiUrl}/start`,
      {
        template_id: templateId,
        force_new: forceNew
      }
    ).pipe(
      tap(() => this.notifyStatusChanged())
    );
  }

  // ----------------------------------
  // Submit assessment
  // ----------------------------------

  submitAssessment(
    sessionId: number,
    answers: AssessmentAnswer[],
    tabSwitchCount: number = 0
  ): Observable<AssessmentSubmitResponse> {
    return this.http.post<AssessmentSubmitResponse>(
      `${this.apiUrl}/sessions/${sessionId}/submit`,
      {
        answers,
        tab_switch_count: tabSwitchCount
      }
    ).pipe(
      tap(() => this.notifyStatusChanged())
    );
  }

  // ----------------------------------
  // Record live tab switch violation
  // ----------------------------------

  recordTabSwitch(
    sessionId: number,
    tabSwitchCount: number
  ): Observable<{ status: string; session_id: number; tab_switch_count: number }> {
    return this.http.post<{ status: string; session_id: number; tab_switch_count: number }>(
      `${this.apiUrl}/sessions/${sessionId}/tab-switch`,
      {
        tab_switch_count: tabSwitchCount
      }
    );
  }

  // ----------------------------------
  // Save answer progressively
  // ----------------------------------

  saveAnswer(
    sessionId: number,
    payload: {
      question_id: number;
      answer?: string | null;
      is_marked_for_review?: boolean;
    }
  ): Observable<{
    status: string;
    question_id: number;
    answer: string | null;
    is_marked_for_review: boolean;
  }> {
    return this.http.post<{
      status: string;
      question_id: number;
      answer: string | null;
      is_marked_for_review: boolean;
    }>(
      `${this.apiUrl}/sessions/${sessionId}/save-answer`,
      payload
    );
  }

  // ----------------------------------
  // Get saved results
  // ----------------------------------

  getResults(
    sessionId: number
  ): Observable<AssessmentScoresResponse> {
    return this.http.get<AssessmentScoresResponse>(
      `${this.apiUrl}/sessions/${sessionId}/results`
    );
  }

  // ----------------------------------
  // Generate report
  // ----------------------------------

  generateReport(
    sessionId: number
  ): Observable<AssessmentReport> {
    return this.http.post<AssessmentReport>(
      `${this.apiUrl}/sessions/${sessionId}/report`,
      {}
    );
  }

  // ----------------------------------
  // Get saved report
  // ----------------------------------

  getReport(
    sessionId: number
  ): Observable<AssessmentReport> {
    return this.http.get<AssessmentReport>(
      `${this.apiUrl}/sessions/${sessionId}/report`
    );
  }

  // ----------------------------------
  // Learner: Get my results & report cards
  // ----------------------------------

  getMyResults(): Observable<UserAssessmentResultItem[]> {
    return this.http.get<UserAssessmentResultItem[]>(
      `${this.apiUrl}/my/results`
    );
  }

  // ----------------------------------
  // Admin & Teacher: Get all users' assessment results
  // ----------------------------------

  getAdminResults(params?: {
    template_id?: number;
    status?: string;
    search?: string;
  }): Observable<AdminAssessmentResultsResponse> {
    let httpParams = new HttpParams();
    if (params?.template_id) {
      httpParams = httpParams.set('template_id', params.template_id.toString());
    }
    if (params?.status) {
      httpParams = httpParams.set('status', params.status);
    }
    if (params?.search) {
      httpParams = httpParams.set('search', params.search);
    }
    return this.http.get<AdminAssessmentResultsResponse>(
      `${this.apiUrl}/admin/results`,
      { params: httpParams }
    );
  }
}
