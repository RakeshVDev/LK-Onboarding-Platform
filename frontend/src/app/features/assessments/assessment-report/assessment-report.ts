import {
  ChangeDetectorRef,
  Component,
  OnInit,
  inject,
  signal
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService } from '../../../core/services/auth.service';

import {
  AssessmentService,
  AssessmentReport,
  CategoryScore
} from '../services/assessment';

@Component({
  selector: 'app-assessment-report',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './assessment-report.html',
  styleUrl: './assessment-report.scss'
})
export class AssessmentReportPage implements OnInit {

  private readonly api = inject(AssessmentService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  public readonly authService = inject(AuthService);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly report = signal<AssessmentReport | null>(null);
  readonly loading = signal(true);
  readonly errorMessage = signal('');
  sessionId = 0;

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
      },
      error: (error: HttpErrorResponse) => {
        if (error.status === 404) {
          // If report not yet generated, attempt generation
          this.api.generateReport(this.sessionId).subscribe({
            next: (data) => {
              this.report.set(data);
              this.loading.set(false);
              this.cdr.detectChanges();
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
    } else {
      void this.router.navigate(['/my-results']);
    }
  }
}
