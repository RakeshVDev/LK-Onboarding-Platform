import {
  ChangeDetectorRef,
  Component,
  OnInit,
  computed,
  inject,
  signal
} from '@angular/core';

import { CommonModule } from '@angular/common';
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
  DimensionScoreItem
} from '../services/assessment-intelligence.service';
import {
  AssessmentRadarChartComponent,
  RadarChartSeries
} from '../components/assessment-radar-chart/assessment-radar-chart';
import { BrandLogo } from '../../../shared/components/brand-logo/brand-logo';

@Component({
  selector: 'app-assessment-report',
  standalone: true,
  imports: [CommonModule, RouterModule, AssessmentRadarChartComponent, BrandLogo],
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
  sessionId = 0;

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
          backgroundColor: 'rgba(79, 70, 229, 0.18)',
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
          backgroundColor: 'rgba(79, 70, 229, 0.18)',
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
    this.sessionId = Number(
      this.route.snapshot.paramMap.get('sessionId')
    );

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
        this.loading.set(false);
        this.cdr.detectChanges();
        this.loadIntelligence();
      },
      error: (error: HttpErrorResponse) => {
        if (error.status === 404) {
          // If report not yet generated, attempt generation
          this.api.generateReport(this.sessionId).subscribe({
            next: (data) => {
              this.report.set(data);
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
          error.error?.detail ||
          'Unable to load assessment report. Please try again.'
        );
        this.loading.set(false);
        this.cdr.detectChanges();
      }
    });
  }

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

  get skillLevel(): string {
    return this.report()?.report_data?.skill_level || 'Evaluated';
  }

  get totalQuestions(): number | null {
    return this.report()?.report_data?.total_questions ?? null;
  }

  get correctAnswers(): number | null {
    return this.report()?.report_data?.correct_answers ?? null;
  }

  get incorrectAnswers(): number | null {
    return this.report()?.report_data?.incorrect_answers ?? null;
  }

  get unattemptedQuestions(): number | null {
    return this.report()?.report_data?.unattempted_questions ?? null;
  }

  get timeTakenStr(): string | null {
    return this.report()?.report_data?.time_taken_str ?? null;
  }

  get isPsychometric(): boolean {
    return this.report()?.assessment_type === 'psychometric';
  }

  loadIntelligence(): void {
    if (!this.sessionId) return;
    this.intelligenceLoading.set(true);
    this.intelligenceService.getSessionIntelligence(this.sessionId).subscribe({
      next: (intel) => {
        this.intelligence.set(intel);
        this.intelligenceLoading.set(false);
        this.cdr.detectChanges();
      },
      error: () => {
        this.intelligenceLoading.set(false);
        this.cdr.detectChanges();
      },
    });
  }

  get embeddedIntel(): any {
    return (this.report()?.report_data as any)?.intelligence ?? null;
  }

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

  get difficultyEntries(): Array<{ level: string; total: number; correct: number; percentage: number }> {
    const raw = this.cognitiveMeta?.['difficulty_breakdown'] ?? {};
    return Object.entries(raw).map(([level, v]: [string, any]) => ({
      level: level.toUpperCase(),
      total: Number(v?.total ?? 0),
      correct: Number(v?.correct ?? 0),
      percentage: Number(v?.percentage ?? 0),
    }));
  }

  get cognitiveClusterEntries(): Array<[string, number]> {
    const raw = this.cognitiveMeta?.['cognitive_clusters'] ?? {};
    return Object.entries(raw).map(([k, v]) => [k, Number(v ?? 0)]);
  }

  get detailedFocusAreas(): string[] {
    return this.embeddedIntel?.development_focus_areas ?? [];
  }

  get roleReadinessFit(): string[] {
    return this.embeddedIntel?.role_readiness_fit ?? [];
  }

  get scoringVersionLabel(): string {
    return this.intelligence()?.scoring_version ?? this.embeddedIntel?.scoring_version ?? 'v2.0-local-ml';
  }

  get weightedScorePct(): number | null {
    const val = this.intelligence()?.weighted_percentage ?? this.embeddedIntel?.weighted_percentage;
    return typeof val === 'number' ? val : null;
  }

  get categoryEntries(): [string, string][] {
    return Object.entries(
      this.report()?.report_data?.category_interpretations ?? {}
    );
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
