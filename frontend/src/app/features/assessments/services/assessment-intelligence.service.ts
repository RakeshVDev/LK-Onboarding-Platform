import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export interface DimensionScoreItem {
  dimension_key: string;
  dimension_label: string;
  raw_score: number;
  max_score: number;
  normalized_score: number;
  percentile_band: string;
  evidence: Record<string, unknown>;
}

export interface RadarAxisPoint {
  axis_key: string;
  axis_label: string;
  candidate_score: number;
  benchmark_score: number;
  cohort_average?: number | null;
}

export interface StudyPlanStep {
  days: string;
  title: string;
  detail: string;
  focus_topic: string;
}

export interface DifficultyBarItem {
  level: string;
  percentage: number;
  correct: number;
  total: number;
}

export interface PredictionPoint {
  label: string;
  score: number;
}

export interface DeepAnalyticsBundle {
  percentile_rank: number;
  top_percent_label: string;
  performance_rating: string;
  error_analysis: {
    correct_pct: number;
    wrong_pct: number;
    unattempted_pct: number;
    common_mistakes: string;
  };
  difficulty_performance: DifficultyBarItem[];
  ml_metrics: {
    accuracy_rate: number;
    speed_score: number;
    consistency_score: number;
    difficulty_summary: string;
  };
  performance_prediction: {
    current_score: number;
    expected_low: number;
    expected_high: number;
    uplift_points: number;
    trajectory_points: PredictionPoint[];
  };
  study_plan: StudyPlanStep[];
  key_takeaways: string[];
  assistant_prompts: string[];
}

export interface AskReportQuestionResponse {
  answer: string;
  intent: string;
  referenced_topics: string[];
  follow_up_prompts: string[];
}

export interface IntelligenceMetadataBlock {
  scoring_version: string;
  weighted_percentage: number;
  reverse_scored_count: number;
  executive_summary: string;
  dimensions: DimensionScoreItem[];
  radar_profile: RadarAxisPoint[];
  domain_analysis: Record<string, any>;
  deep_analytics?: DeepAnalyticsBundle;
  key_strengths_detailed: string[];
  development_focus_areas: string[];
  role_readiness_fit: string[];
}

export interface AssessmentIntelligenceResponse {
  session_id: number;
  template_id: number;
  template_name: string;
  assessment_type: string;
  learner_user_id: number;
  learner_name?: string | null;
  learner_email?: string | null;
  scoring_version: string;
  overall_percentage: number;
  weighted_percentage: number;
  total_score: number;
  max_score: number;
  skill_level: string;
  evaluated_at: string;
  dimensions: DimensionScoreItem[];
  radar_profile: RadarAxisPoint[];
  domain_analysis: Record<string, any>;
  report_data: Record<string, any> & { intelligence?: IntelligenceMetadataBlock };
  report_text: string;
}

export interface DomainAverageSummary {
  assessment_type: string;
  evaluated_sessions: number;
  average_percentage: number;
  min_percentage: number;
  max_percentage: number;
}

export interface AnalyticsCandidateOption {
  session_id: number;
  learner_user_id: number;
  learner_name: string;
  learner_email: string;
  template_id: number;
  template_name: string;
  assessment_type: string;
  overall_percentage: number;
  completed_at?: string | null;
}

export interface OverviewAnalyticsResponse {
  total_evaluated_sessions: number;
  unique_evaluated_learners: number;
  global_average_percentage: number;
  domain_summaries: DomainAverageSummary[];
  evaluated_candidates: AnalyticsCandidateOption[];
  active_scoring_versions: Array<Record<string, any>>;
}

@Injectable({
  providedIn: 'root',
})
export class AssessmentIntelligenceService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/training-api/api/v1/assessment-intelligence';

  evaluateSession(
    sessionId: number,
    force = false,
    scoringVersionTag?: string
  ): Observable<AssessmentIntelligenceResponse> {
    return this.http.post<AssessmentIntelligenceResponse>(
      `${this.apiUrl}/sessions/${sessionId}/evaluate`,
      {
        force,
        scoring_version_tag: scoringVersionTag ?? null,
      }
    );
  }

  getSessionIntelligence(sessionId: number): Observable<AssessmentIntelligenceResponse> {
    return this.http.get<AssessmentIntelligenceResponse>(
      `${this.apiUrl}/sessions/${sessionId}/intelligence`
    );
  }

  getOverviewAnalytics(): Observable<OverviewAnalyticsResponse> {
    return this.http.get<OverviewAnalyticsResponse>(
      `${this.apiUrl}/analytics/overview`
    );
  }

  askReportAssistant(
    sessionId: number,
    question: string
  ): Observable<AskReportQuestionResponse> {
    return this.http.post<AskReportQuestionResponse>(
      `${this.apiUrl}/sessions/${sessionId}/ask`,
      { question }
    );
  }
}

