import {
  ChangeDetectorRef,
  Component,
  OnInit,
  computed,
  inject,
  signal
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../../core/services/auth.service';
import { AssessmentStatusService } from '../../../core/services/assessment-status.service';

import {
  AssessmentService,
  AssessmentReport,
  CategoryScore
} from '../services/assessment';
import {
  AssessmentIntelligenceResponse,
  AssessmentIntelligenceService,
  DeepAnalyticsBundle,
  DifficultyBarItem,
  DimensionScoreItem,
  PredictionPoint,
  StudyPlanStep
} from '../services/assessment-intelligence.service';
import {
  AssessmentRadarChartComponent,
  RadarChartSeries
} from '../components/assessment-radar-chart/assessment-radar-chart';
import { BrandLogo } from '../../../shared/components/brand-logo/brand-logo';

export interface AssistantChatEntry {
  role: 'user' | 'assistant';
  text: string;
  referencedTopics?: string[];
}

export interface TopicMetricItem {
  key: string;
  label: string;
  shortLabel: string;
  score: number;
  cohortAvg: number;
  band: string;
  color: string;
}

@Component({
  selector: 'app-assessment-report',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, AssessmentRadarChartComponent, BrandLogo],
  templateUrl: './assessment-report.html',
  styleUrl: './assessment-report.scss'
})
export class AssessmentReportPage implements OnInit {

  private readonly api = inject(AssessmentService);
  private readonly intelligenceService = inject(AssessmentIntelligenceService);
  private readonly assessmentStatusService = inject(AssessmentStatusService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  public readonly authService = inject(AuthService);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly report = signal<AssessmentReport | null>(null);
  readonly intelligence = signal<AssessmentIntelligenceResponse | null>(null);
  readonly intelligenceLoading = signal(false);
  readonly loading = signal(true);
  readonly errorMessage = signal('');
  readonly allCompleted = signal(false);
  readonly pendingCount = signal(0);
  readonly selectedTopicKey = signal<string>('');

  // Interactive Ask AI Assistant state
  assistantInput = '';
  readonly assistantLoading = signal(false);
  readonly assistantMessages = signal<AssistantChatEntry[]>([]);

  sessionId = 0;

  private readonly palette = ['#6366f1', '#0ea5e9', '#10b981', '#8b5cf6', '#f59e0b', '#ec4899'];

  readonly radarAxes = computed<string[]>(() => {
    const intel = this.intelligence();
    if (intel?.radar_profile?.length) {
      return intel.radar_profile.map((p) => p.axis_label);
    }
    const embedded = (this.report()?.report_data as any)?.intelligence?.radar_profile;
    if (Array.isArray(embedded) && embedded.length) {
      return embedded.map((p: any) => p.axis_label);
    }
    return this.categoryScores.map((c) => this.categoryLabel(c.category));
  });

  readonly radarBenchmarkValues = computed<number[]>(() => {
    const intel = this.intelligence();
    if (intel?.radar_profile?.length) {
      return intel.radar_profile.map((p) => Number(p.benchmark_score ?? 75));
    }
    return this.radarAxes().map(() => 75);
  });

  readonly radarSeries = computed<RadarChartSeries[]>(() => {
    const intel = this.intelligence();
    const profile = intel?.radar_profile?.length
      ? intel.radar_profile
      : ((this.report()?.report_data as any)?.intelligence?.radar_profile ?? []);

    if (Array.isArray(profile) && profile.length > 0) {
      const series: RadarChartSeries[] = [
        {
          id: `candidate-${this.sessionId}`,
          label: intel?.learner_name || this.report()?.learner_name || 'Candidate Profile',
          values: profile.map((p: any) => Number(p.candidate_score ?? 0)),
          borderColor: '#4f46e5',
          backgroundColor: 'rgba(79, 70, 229, 0.20)',
          seriesType: 'candidate',
          overallPercentage: Number(intel?.overall_percentage ?? this.report()?.report_data?.overall_percentage ?? 0),
        },
      ];
      const hasCohort = profile.some((p: any) => typeof p.cohort_average === 'number');
      if (hasCohort) {
        series.push({
          id: 'cohort-average',
          label: 'Cohort Average',
          values: profile.map((p: any) => Number(p.cohort_average ?? 0)),
          borderColor: '#0284c7',
          backgroundColor: 'rgba(2, 132, 199, 0.10)',
          dashed: true,
          seriesType: 'cohort_average',
        });
      }
      return series;
    }

    if (this.categoryScores.length > 0) {
      return [
        {
          id: `candidate-${this.sessionId}`,
          label: this.report()?.learner_name || 'Candidate Profile',
          values: this.categoryScores.map((c) => Number(c.percentage ?? 0)),
          borderColor: '#4f46e5',
          backgroundColor: 'rgba(79, 70, 229, 0.20)',
          seriesType: 'candidate',
        },
      ];
    }
    return [];
  });

  readonly isManagerView = computed(() =>
    this.authService.hasRole('admin', 'superadmin', 'teacher')
  );

  ngOnInit(): void {
    this.sessionId = Number(this.route.snapshot.paramMap.get('sessionId'));

    if (!Number.isInteger(this.sessionId) || this.sessionId <= 0) {
      this.errorMessage.set('Invalid assessment session.');
      this.loading.set(false);
      this.cdr.detectChanges();
      return;
    }

    if (this.authService.hasRole('learner')) {
      void this.assessmentStatusService.getStatus(true).then(s => {
        this.allCompleted.set(s.status === 'completed' || s.all_completed === true);
        this.pendingCount.set(s.pending_count ?? 0);
        this.cdr.detectChanges();
      }).catch(() => {});
    } else {
      this.allCompleted.set(true);
    }

    this.loadReport();
  }

  loadReport(): void {
    this.loading.set(true);
    this.errorMessage.set('');

    this.api.getReport(this.sessionId).subscribe({
      next: (data: AssessmentReport) => {
        this.report.set(data);
        this.ensureSelectedTopic();
        this.loading.set(false);
        this.cdr.detectChanges();
        this.loadIntelligence();
      },
      error: (error: HttpErrorResponse) => {
        if (error.status === 404) {
          this.api.generateReport(this.sessionId).subscribe({
            next: (data) => {
              this.report.set(data);
              this.ensureSelectedTopic();
              this.loading.set(false);
              this.cdr.detectChanges();
              this.loadIntelligence();
            },
            error: (genErr) => {
              this.errorMessage.set(genErr.error?.detail || 'Unable to generate assessment report.');
              this.loading.set(false);
              this.cdr.detectChanges();
            }
          });
          return;
        }

        this.errorMessage.set(
          error.error?.detail || 'Unable to load assessment report. Please try again.'
        );
        this.loading.set(false);
        this.cdr.detectChanges();
      }
    });
  }

  loadIntelligence(): void {
    if (!this.sessionId) return;
    this.intelligenceLoading.set(true);
    this.intelligenceService.getSessionIntelligence(this.sessionId).subscribe({
      next: (intel) => {
        this.intelligence.set(intel);
        this.ensureSelectedTopic();
        this.intelligenceLoading.set(false);
        this.cdr.detectChanges();
      },
      error: () => {
        this.intelligenceLoading.set(false);
        this.cdr.detectChanges();
      },
    });
  }

  private ensureSelectedTopic(): void {
    const items = this.topicMetrics;
    if (items.length > 0 && !items.some((t) => t.key === this.selectedTopicKey())) {
      this.selectedTopicKey.set(items[0].key);
    }
  }

  selectTopic(key: string): void {
    this.selectedTopicKey.set(key);
    this.cdr.detectChanges();
  }

  askAssistant(presetPrompt?: string): void {
    const query = (presetPrompt ?? this.assistantInput).trim();
    if (!query || this.assistantLoading() || !this.sessionId) return;
    this.assistantInput = '';
    this.assistantMessages.update((msgs) => [...msgs, { role: 'user', text: query }]);
    this.assistantLoading.set(true);
    this.cdr.detectChanges();

    this.intelligenceService.askReportAssistant(this.sessionId, query).subscribe({
      next: (res) => {
        this.assistantMessages.update((msgs) => [
          ...msgs,
          {
            role: 'assistant',
            text: res.answer,
            referencedTopics: res.referenced_topics,
          },
        ]);
        this.assistantLoading.set(false);
        this.cdr.detectChanges();
      },
      error: () => {
        this.assistantMessages.update((msgs) => [
          ...msgs,
          {
            role: 'assistant',
            text: this.report()?.report_data?.summary || 'Focus on your lowest-scoring topics and follow the 7-day study plan above.',
          },
        ]);
        this.assistantLoading.set(false);
        this.cdr.detectChanges();
      },
    });
  }

  // ---- Core Report Getters ----

  get reportTitle(): string {
    const rep = this.report();
    if (rep?.report_data?.report_title) {
      return rep.report_data.report_title;
    }
    const type = (rep?.assessment_type || '').toLowerCase();
    if (type === 'english_grammar') return 'English Grammar Assessment Report';
    if (type === 'logical_reasoning') return 'Logical Reasoning Assessment Report';
    if (type === 'technical') return 'Technical Assessment Report';
    if (type === 'programming') return 'Programming Assessment Report';
    if (type === 'psychometric') return 'Psychometric Assessment Report';
    return rep?.template_name ? `${rep.template_name} Report` : 'Assessment Performance Report';
  }

  get overallPercentage(): number {
    return Number(
      this.intelligence()?.overall_percentage ??
      this.report()?.report_data?.overall_percentage ??
      0
    );
  }

  get totalScore(): number {
    return Number(this.intelligence()?.total_score ?? this.report()?.report_data?.total_score ?? 0);
  }

  get maxScore(): number {
    return Number(this.intelligence()?.max_score ?? this.report()?.report_data?.max_score ?? 0);
  }

  get skillLevel(): string {
    return this.report()?.report_data?.skill_level || 'Evaluated';
  }

  get totalQuestions(): number {
    return Number(this.report()?.report_data?.total_questions ?? 0);
  }

  get correctAnswers(): number {
    return Number(this.report()?.report_data?.correct_answers ?? 0);
  }

  get incorrectAnswers(): number {
    return Number(this.report()?.report_data?.incorrect_answers ?? 0);
  }

  get unattemptedQuestions(): number {
    return Number(this.report()?.report_data?.unattempted_questions ?? 0);
  }

  get timeTakenStr(): string {
    return this.report()?.report_data?.time_taken_str || 'Recorded';
  }

  get isPsychometric(): boolean {
    return this.report()?.assessment_type === 'psychometric';
  }

  get embeddedIntel(): any {
    return (this.report()?.report_data as any)?.intelligence ?? null;
  }

  get mlInsights(): Record<string, any> {
    return (
      (this.intelligence()?.report_data as any)?.ml_insights ??
      (this.report()?.report_data as any)?.ml_insights ??
      this.embeddedIntel?.ml_insights ??
      {}
    );
  }

  get deepAnalytics(): DeepAnalyticsBundle {
    const raw =
      (this.intelligence()?.report_data as any)?.deep_analytics ??
      (this.report()?.report_data as any)?.deep_analytics ??
      this.embeddedIntel?.deep_analytics;
    if (raw) {
      return raw as DeepAnalyticsBundle;
    }
    const pct = this.overallPercentage;
    const uplift = Number(this.mlInsights['estimated_uplift_points'] ?? Math.max(4, Math.min(25, (98 - pct) * 0.45)));
    const expectedLow = Math.min(98, Math.round(pct + uplift * 0.65));
    const expectedHigh = Math.min(100, Math.max(expectedLow + 2, Math.round(pct + uplift)));
    const totalQ = Math.max(1, this.totalQuestions || (this.correctAnswers + this.incorrectAnswers + this.unattemptedQuestions) || 1);
    const correctPct = this.totalQuestions ? Math.round((this.correctAnswers / totalQ) * 1000) / 10 : Math.round(pct * 10) / 10;
    const unattPct = this.totalQuestions ? Math.round((this.unattemptedQuestions / totalQ) * 1000) / 10 : 0;
    const wrongPct = Math.max(0, Math.round((100 - correctPct - unattPct) * 10) / 10);
    return {
      percentile_rank: Math.min(99, Math.max(10, Math.round(pct * 0.96 * 10) / 10)),
      top_percent_label: pct >= 85 ? 'Top 10% of Test Takers' : (pct >= 70 ? 'Top 25% of Test Takers' : 'Developing Cohort Tier'),
      performance_rating: pct >= 85 ? 'Excellent' : (pct >= 70 ? 'Proficient' : (pct >= 50 ? 'Developing' : 'Foundational')),
      error_analysis: {
        correct_pct: correctPct,
        wrong_pct: wrongPct,
        unattempted_pct: unattPct,
        common_mistakes: this.developmentAreas[0] || 'Review missed items carefully to strengthen accuracy.',
      },
      difficulty_performance: [
        { level: 'Easy', percentage: Math.min(100, Math.round(pct + 8)), correct: 0, total: 0 },
        { level: 'Medium', percentage: Math.round(pct), correct: 0, total: 0 },
        { level: 'Hard', percentage: Math.max(0, Math.round(pct - 10)), correct: 0, total: 0 },
      ],
      ml_metrics: {
        accuracy_rate: Math.round(pct * 10) / 10,
        speed_score: Math.round(Number(this.timingMeta?.['time_efficiency_score'] ?? pct) * 10) / 10,
        consistency_score: Math.round(Number(this.psychometricMeta?.['consistency_index'] ?? 85) * 10) / 10,
        difficulty_summary: `Easy ${Math.min(100, Math.round(pct + 8))}% | Medium ${Math.round(pct)}% | Hard ${Math.max(0, Math.round(pct - 10))}%`,
      },
      performance_prediction: {
        current_score: Math.round(pct * 10) / 10,
        expected_low: expectedLow,
        expected_high: expectedHigh,
        uplift_points: Math.round(uplift * 10) / 10,
        trajectory_points: [
          { label: 'Current', score: Math.round(pct * 10) / 10 },
          { label: 'Day 2', score: Math.min(100, Math.round((pct + uplift * 0.25) * 10) / 10) },
          { label: 'Day 4', score: Math.min(100, Math.round((pct + uplift * 0.55) * 10) / 10) },
          { label: 'Day 6', score: Math.min(100, Math.round((pct + uplift * 0.82) * 10) / 10) },
          { label: 'Day 7', score: expectedHigh },
        ],
      },
      study_plan: [
        { days: 'Day 1–2', title: 'Strengthen Priority Topic', detail: this.recommendations[0] || 'Review core principles and missed items.', focus_topic: 'Core Fundamentals' },
        { days: 'Day 3–4', title: 'Targeted Practice Sets', detail: 'Work through medium-to-hard scenarios with explicit step-by-step checks.', focus_topic: 'Applied Practice' },
        { days: 'Day 5–6', title: 'Timed Fluency Drills', detail: 'Build speed and accuracy under exam time budgets.', focus_topic: 'Pacing & Speed' },
        { days: 'Day 7', title: 'Mock Test + Review', detail: 'Attempt a full review set and close remaining gaps.', focus_topic: 'Verification' },
      ],
      key_takeaways: [
        this.report()?.report_data?.summary || `Achieved ${pct.toFixed(1)}% overall score.`,
      ],
      assistant_prompts: [
        'Why did I lose marks?',
        `How can I improve my score by ${Math.max(5, Math.round(uplift))}%?`,
        'Give me a 7-day practice plan',
      ],
    };
  }

  get topicMetrics(): TopicMetricItem[] {
    const radar = this.intelligence()?.radar_profile ?? this.embeddedIntel?.radar_profile ?? [];
    const radarCohortMap = new Map<string, number>();
    for (const r of radar) {
      if (typeof r.cohort_average === 'number') {
        radarCohortMap.set(r.axis_key, r.cohort_average);
      }
    }

    const dims = this.intelligenceDimensions;
    if (dims.length > 0) {
      return dims.map((d, idx) => {
        const label = d.dimension_label || this.categoryLabel(d.dimension_key);
        return {
          key: d.dimension_key,
          label,
          shortLabel: this.abbreviateLabel(label),
          score: Math.round(Number(d.normalized_score ?? 0) * 10) / 10,
          cohortAvg: Math.round((radarCohortMap.get(d.dimension_key) ?? 72) * 10) / 10,
          band: d.percentile_band || this.bandForScore(Number(d.normalized_score ?? 0)),
          color: this.palette[idx % this.palette.length],
        };
      });
    }

    return this.categoryScores.map((c, idx) => {
      const label = this.categoryLabel(c.category);
      const score = Math.round(Number(c.percentage ?? 0) * 10) / 10;
      return {
        key: c.category,
        label,
        shortLabel: this.abbreviateLabel(label),
        score,
        cohortAvg: 72,
        band: this.bandForScore(score),
        color: this.palette[idx % this.palette.length],
      };
    });
  }

  get sortedTopicMetrics(): TopicMetricItem[] {
    return [...this.topicMetrics].sort((a, b) => b.score - a.score);
  }

  get activeTopicMetric(): TopicMetricItem | null {
    const items = this.topicMetrics;
    if (!items.length) return null;
    return items.find((t) => t.key === this.selectedTopicKey()) ?? items[0];
  }

  get subjectRings(): TopicMetricItem[] {
    return this.topicMetrics.slice(0, 4);
  }

  get studyPlanSteps(): StudyPlanStep[] {
    return this.deepAnalytics.study_plan ?? [];
  }

  get difficultyBars(): DifficultyBarItem[] {
    return this.deepAnalytics.difficulty_performance ?? [];
  }

  get predictionPoints(): PredictionPoint[] {
    return this.deepAnalytics.performance_prediction?.trajectory_points ?? [];
  }

  get weakestTopicLabel(): string {
    const sorted = [...this.topicMetrics].sort((a, b) => a.score - b.score);
    return sorted[0]?.label || this.reportTitle;
  }

  // ---- SVG Geometry Helpers ----

  ringCircumference(radius: number): number {
    return 2 * Math.PI * radius;
  }

  ringDashOffset(percentage: number, radius: number): number {
    const clamped = Math.max(0, Math.min(100, Number(percentage || 0)));
    const c = this.ringCircumference(radius);
    return c * (1 - clamped / 100);
  }

  ringColor(percentage: number): string {
    if (percentage >= 80) return '#10b981';
    if (percentage >= 60) return '#3b82f6';
    if (percentage >= 40) return '#f59e0b';
    return '#ef4444';
  }

  get comparisonChartData(): {
    yourPoints: string;
    avgPoints: string;
    nodes: Array<{ x: number; yYour: number; yAvg: number; label: string; score: number; active: boolean }>;
  } {
    const items = this.topicMetrics.slice(0, 6);
    if (!items.length) return { yourPoints: '', avgPoints: '', nodes: [] };
    const w = 280;
    const h = 110;
    const padX = 24;
    const padY = 14;
    const stepX = items.length > 1 ? (w - padX * 2) / (items.length - 1) : 0;
    const nodes = items.map((t, idx) => {
      const x = items.length > 1 ? padX + idx * stepX : w / 2;
      const yYour = padY + ((100 - Math.max(0, Math.min(100, t.score))) / 100) * (h - padY * 2);
      const yAvg = padY + ((100 - Math.max(0, Math.min(100, t.cohortAvg))) / 100) * (h - padY * 2);
      return {
        x: Math.round(x * 10) / 10,
        yYour: Math.round(yYour * 10) / 10,
        yAvg: Math.round(yAvg * 10) / 10,
        label: `T${idx + 1}`,
        score: t.score,
        active: t.key === this.selectedTopicKey(),
      };
    });
    return {
      yourPoints: nodes.map((n) => `${n.x},${n.yYour}`).join(' '),
      avgPoints: nodes.map((n) => `${n.x},${n.yAvg}`).join(' '),
      nodes,
    };
  }

  get predictionChartData(): {
    linePoints: string;
    areaPoints: string;
    nodes: Array<{ x: number; y: number; label: string; score: number }>;
  } {
    const pts = this.predictionPoints;
    if (!pts.length) return { linePoints: '', areaPoints: '', nodes: [] };
    const w = 260;
    const h = 88;
    const padX = 18;
    const padY = 12;
    const stepX = pts.length > 1 ? (w - padX * 2) / (pts.length - 1) : 0;
    const nodes = pts.map((p, idx) => {
      const x = pts.length > 1 ? padX + idx * stepX : w / 2;
      const y = padY + ((100 - Math.max(0, Math.min(100, p.score))) / 100) * (h - padY * 2);
      return {
        x: Math.round(x * 10) / 10,
        y: Math.round(y * 10) / 10,
        label: p.label,
        score: p.score,
      };
    });
    const linePoints = nodes.map((n) => `${n.x},${n.y}`).join(' ');
    const areaPoints = `${nodes[0].x},${h - padY} ${linePoints} ${nodes[nodes.length - 1].x},${h - padY}`;
    return { linePoints, areaPoints, nodes };
  }

  get errorDonutBackground(): string {
    const err = this.deepAnalytics.error_analysis;
    const c = Math.max(0, Math.min(100, err.correct_pct));
    const w = Math.max(0, Math.min(100 - c, err.wrong_pct));
    return `conic-gradient(#10b981 0% ${c}%, #ef4444 ${c}% ${c + w}%, #94a3b8 ${c + w}% 100%)`;
  }

  // ---- Domain Metadata Getters ----

  get intelligenceDimensions(): DimensionScoreItem[] {
    return this.intelligence()?.dimensions ?? this.embeddedIntel?.dimensions ?? [];
  }

  get domainAnalysis(): Record<string, any> {
    return this.intelligence()?.domain_analysis ?? this.embeddedIntel?.domain_analysis ?? {};
  }

  get psychometricMeta(): Record<string, any> | null {
    return this.domainAnalysis['psychometric'] ?? null;
  }

  get cognitiveMeta(): Record<string, any> | null {
    return this.domainAnalysis['cognitive'] ?? null;
  }

  get timingMeta(): Record<string, any> | null {
    return this.domainAnalysis['timing'] ?? null;
  }

  get nlpMeta(): Record<string, any> | null {
    return this.domainAnalysis['nlp'] ?? null;
  }

  get programmingMeta(): Record<string, any> | null {
    return this.domainAnalysis['programming'] ?? null;
  }

  get detailedFocusAreas(): string[] {
    return this.embeddedIntel?.development_focus_areas ?? [];
  }

  get roleReadinessFit(): string[] {
    return this.embeddedIntel?.role_readiness_fit ?? [];
  }

  get weightedScorePct(): number | null {
    const val = this.intelligence()?.weighted_percentage ?? this.embeddedIntel?.weighted_percentage;
    return typeof val === 'number' ? val : null;
  }

  get categoryEntries(): [string, string][] {
    return Object.entries(this.report()?.report_data?.category_interpretations ?? {});
  }

  get categoryScores(): CategoryScore[] {
    return this.report()?.report_data?.category_scores ?? [];
  }

  get strengths(): string[] {
    return this.report()?.report_data?.strengths ?? [];
  }

  get developmentAreas(): string[] {
    return this.report()?.report_data?.development_areas ?? [];
  }

  get recommendations(): string[] {
    return this.report()?.report_data?.recommendations ?? [];
  }

  private abbreviateLabel(label: string): string {
    if (label.length <= 13) return label;
    const words = label.split(/\s+/).filter(Boolean);
    if (words.length >= 2) {
      return words[0].length <= 10 ? words[0] : words.map((w) => w[0]).join('').toUpperCase();
    }
    return label.slice(0, 11) + '…';
  }

  private bandForScore(score: number): string {
    if (score >= 85) return 'Excellent';
    if (score >= 70) return 'Strong';
    if (score >= 50) return 'Good';
    return 'Needs Practice';
  }

  categoryLabel(category: string): string {
    const labels: Record<string, string> = {
      english_grammar: 'English Grammar & Syntax',
      subject_verb_agreement: 'Subject-Verb Agreement',
      tenses_and_aspects: 'Tenses & Aspects',
      tenses: 'Verb Tenses',
      articles: 'Articles & Determiners',
      prepositions: 'Prepositions & Phrasal Verbs',
      conjunctions: 'Conjunctions & Connectors',
      voice_and_speech: 'Active/Passive Voice & Speech',
      sentence_correction: 'Sentence Correction & Syntax',
      error_detection: 'Error Detection & Spotting',
      vocabulary: 'Corporate Vocabulary & Usage',
      idioms_collocations: 'Idioms & Professional Collocations',
      reading_comprehension: 'Reading Comprehension & Analysis',
      logical_reasoning: 'Logical Reasoning & Deduction',
      number_series: 'Number Series & Sequences',
      alphabet_series: 'Alphabet Series & Letter Patterns',
      coding_decoding: 'Coding-Decoding & Cipher Logic',
      blood_relations: 'Family Trees & Blood Relations',
      direction_distance: 'Direction & Spatial Distance',
      pattern_recognition: 'Pattern Recognition & Matrices',
      logical_statements: 'Logical Statements & Assumptions',
      odd_one_out: 'Classification & Odd One Out',
      analogy: 'Analogy & Semantic Relationships',
      technical: 'Core Technical Engineering',
      technical_knowledge: 'Fundamentals & Architecture',
      data_structures: 'Data Structures & Efficiency',
      algorithms: 'Algorithms & Complexity',
      python_programming: 'Python Programming',
      javascript_web: 'JavaScript, TypeScript & Web',
      databases_sql: 'Databases & SQL Queries',
      system_design: 'System Design & Distributed Systems',
      git_devops: 'Git, CI/CD & DevOps Practices',
      personality_work_preferences: 'Personality & Work Preferences',
      situational_judgement: 'Situational Judgement',
      emotional_intelligence: 'Emotional Intelligence',
      learning_adaptability: 'Learning Agility & Adaptability',
    };

    return labels[category] || category
      .replaceAll('_', ' ')
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  printReport(): void {
    window.print();
  }

  goBack(): void {
    if (this.authService.hasRole('admin', 'teacher', 'superadmin')) {
      void this.router.navigate(['/assessment-results']);
    } else if (!this.allCompleted()) {
      void this.router.navigate(['/my-assessments']);
    } else {
      void this.router.navigate(['/my-results']);
    }
  }
}
