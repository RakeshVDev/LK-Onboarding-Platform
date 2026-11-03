
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface AssessmentCategory {
  label: string;
  question_count: number;
}

export interface AssessmentTemplate {
  id: number;
  name: string;
  description: string | null;
  question_count: number;
  category_config: Record<string, AssessmentCategory>;
  is_active: boolean;
  created_by_user_id: number;
  created_at: string;
}

export interface CreateAssessmentTemplate {
  name: string;
  description: string | null;
  question_count: number;
  category_config: Record<string, AssessmentCategory>;
}

export interface UpdateAssessmentTemplate {
  name?: string;
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
  question_type: string;
  question_text: string;
  options: AssessmentOption[];
  display_order: number;
}

export interface AssessmentStartResponse {
  session_id: number;
  status: string;
  question_count: number;
  started_at: string;
  questions: AssessmentQuestion[];
}


export interface AssessmentResumeResponse {
  session_id: number;
  status: string;
  question_count: number;
  started_at: string;
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
  categories: CategoryScore[];
}

export interface AssessmentReportData {
  summary: string;
  strengths: string[];
  development_areas: string[];
  recommendations: string[];
  category_interpretations: Record<string, string>;
  overall_percentage?: number;
  total_score?: number;
  max_score?: number;
  category_scores?: CategoryScore[];
}

export interface AssessmentReport {
  id: number;
  session_id: number;
  report_data: AssessmentReportData;
  report_text: string;
  ai_model: string;
  generated_at: string;
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
    templateId: number
  ): Observable<AssessmentStartResponse> {
    return this.http.post<AssessmentStartResponse>(
      `${this.apiUrl}/start`,
      {
        template_id: templateId
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
}
