import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

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
  category_config: Record<string, AssessmentCategory>;
  is_active: boolean;
  created_by_user_id: number;
  created_at: string;
}

export interface CreateAssessmentTemplate {
  name: string;
  assessment_type?: "psychometric" | "technical" | "english_grammar" | "logical_reasoning" | "programming";
  description: string | null;
  question_count: number;
  category_config: Record<string, AssessmentCategory>;
}

export interface UpdateAssessmentTemplate {
  name?: string;
  assessment_type?: "psychometric" | "technical" | "english_grammar" | "logical_reasoning" | "programming";
  description?: string | null;
  question_count?: number;
  category_config?: Record<string, AssessmentCategory>;
  is_active?: boolean;
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
  options: AssessmentOption[];
  display_order: number;
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
}

export interface AssessmentReportData {
  report_title?: string;
  skill_level?: string;
  total_questions?: number;
  correct_answers?: number;
  incorrect_answers?: number;
  unattempted_questions?: number;
  time_taken_str?: string;
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
  options: BankQuestionOption[];
  max_score: number;
  is_active: boolean;
  correct_option_id?: string;
}

export interface CreateBankQuestionPayload {
  category: string;
  difficulty: 'Easy' | 'Medium' | 'Hard' | string;
  question_type?: string;
  question_text: string;
  options: BankQuestionOption[];
  correct_option_id: string;
  max_score?: number;
}

@Injectable({
  providedIn: 'root'
})
export class AssessmentService {

  private readonly http = inject(HttpClient);

  private readonly apiUrl =
    '/training-api/api/v1/assessments';

  // ----------------------------------
  // Assessment templates
  // ----------------------------------

  getTemplates(): Observable<AssessmentTemplate[]> {
    return this.http.get<AssessmentTemplate[]>(
      `${this.apiUrl}/templates`
    );
  }

  getTemplate(id: number): Observable<AssessmentTemplate> {
    return this.http.get<AssessmentTemplate>(
      `${this.apiUrl}/templates/${id}`
    );
  }

  getBankQuestions(templateId: number): Observable<BankQuestion[]> {
    return this.http.get<BankQuestion[]>(
      `${this.apiUrl}/templates/${templateId}/questions`
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

  deleteBankQuestion(
    templateId: number,
    questionId: number
  ): Observable<void> {
    return this.http.delete<void>(
      `${this.apiUrl}/templates/${templateId}/questions/${questionId}`
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
    );
  }

  updateTemplate(
    id: number,
    data: UpdateAssessmentTemplate
  ): Observable<AssessmentTemplate> {
    return this.http.put<AssessmentTemplate>(
      `${this.apiUrl}/templates/${id}`,
      data
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
    );
  }

  // ----------------------------------
  // Submit assessment
  // ----------------------------------

  submitAssessment(
    sessionId: number,
    answers: AssessmentAnswer[]
  ): Observable<AssessmentSubmitResponse> {
    return this.http.post<AssessmentSubmitResponse>(
      `${this.apiUrl}/sessions/${sessionId}/submit`,
      {
        answers
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
