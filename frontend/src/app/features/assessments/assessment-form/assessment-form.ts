import {
  Component,
  OnInit,
  ChangeDetectorRef,
  inject
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
  FormsModule
} from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import {
  AssessmentService,
  AssessmentTemplate,
  AssessmentCategory,
  BankQuestion,
  CreateBankQuestionPayload
} from '../services/assessment';

export interface CategoryOption {
  key: string;
  label: string;
}

const CATEGORY_MAP: Record<string, CategoryOption[]> = {
  logical_reasoning: [
    { key: 'number_series', label: 'Number Series' },
    { key: 'alphabet_series', label: 'Alphabet Series' },
    { key: 'coding_decoding', label: 'Coding-Decoding' },
    { key: 'blood_relations', label: 'Blood Relations' },
    { key: 'direction_distance', label: 'Direction & Distance' },
    { key: 'pattern_recognition', label: 'Pattern Recognition' },
    { key: 'logical_statements', label: 'Logical Statements' },
    { key: 'odd_one_out', label: 'Odd One Out' },
    { key: 'analogy', label: 'Analogy' },
  ],
  english_grammar: [
    { key: 'subject_verb_agreement', label: 'Subject-Verb Agreement' },
    { key: 'tenses_and_aspects', label: 'Tenses & Aspects' },
    { key: 'articles', label: 'Articles (A, An, The)' },
    { key: 'prepositions', label: 'Prepositions & Phrasal Verbs' },
    { key: 'conjunctions', label: 'Conjunctions & Connectors' },
    { key: 'sentence_correction', label: 'Sentence Correction & Syntax' },
    { key: 'vocabulary', label: 'Corporate Vocabulary & Usage' },
    { key: 'voice_and_speech', label: 'Active/Passive Voice & Speech' },
    { key: 'idioms_collocations', label: 'Idioms & Professional Collocations' },
    { key: 'reading_comprehension', label: 'Reading Comprehension' },
  ],
  technical: [
    { key: 'data_structures', label: 'Data Structures' },
    { key: 'algorithms', label: 'Algorithms & Complexity' },
    { key: 'python_programming', label: 'Python Programming' },
    { key: 'javascript_web', label: 'JavaScript & Modern Web' },
    { key: 'databases_sql', label: 'Databases & SQL Queries' },
    { key: 'system_design', label: 'System Design & Architecture' },
    { key: 'git_devops', label: 'Git, DevOps & CI/CD' },
  ],
  programming: [
    { key: 'programming_logic', label: 'Programming Logic' },
    { key: 'algorithm_understanding', label: 'Algorithm Understanding' },
    { key: 'code_output', label: 'Code Output & Tracing' },
    { key: 'problem_solving', label: 'Problem Solving & Debugging' },
    { key: 'data_structures', label: 'Data Structures' },
    { key: 'time_complexity', label: 'Time & Space Complexity' },
  ],
  psychometric: [
    { key: 'emotional_intelligence', label: 'Emotional Intelligence' },
    { key: 'situational_judgement', label: 'Situational Judgement' },
    { key: 'learning_adaptability', label: 'Learning & Adaptability' },
    { key: 'personality_work_preferences', label: 'Personality & Work Preferences' },
    { key: 'team_collaboration', label: 'Team Collaboration & Ethics' },
  ],
};

@Component({
  selector: 'app-assessment-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule
  ],
  templateUrl: './assessment-form.html',
  styleUrl: './assessment-form.scss'
})
export class AssessmentForm implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(AssessmentService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  templateId: number | null = null;
  template: AssessmentTemplate | null = null;

  activeTab: 'config' | 'questions' = 'config';

  loading = false;
  saving = false;
  errorMessage = '';
  successMessage = '';

  // Question Bank state
  bankQuestions: BankQuestion[] = [];
  loadingQuestions = false;
  savingQuestion = false;
  showAddQuestionForm = false;
  deletingQuestionId: number | null = null;
  questionError = '';
  questionSuccess = '';

  // Main Template Form
  form = this.fb.nonNullable.group({
    name: [
      '',
      [
        Validators.required,
        Validators.minLength(3),
        Validators.maxLength(200)
      ]
    ],
    assessment_type: [
      'logical_reasoning' as 'psychometric' | 'technical' | 'english_grammar' | 'logical_reasoning' | 'programming',
      [Validators.required]
    ],
    description: [''],
    question_count: [25, [Validators.required, Validators.min(1), Validators.max(100)]]
  });

  // Manual Question Authoring Form
  qCategory = 'number_series';
  qCustomCategory = '';
  qDifficulty: 'Easy' | 'Medium' | 'Hard' = 'Medium';
  qText = '';
  qOptionA = '';
  qOptionB = '';
  qOptionC = '';
  qOptionD = '';
  qCorrectOption: 'A' | 'B' | 'C' | 'D' = 'A';
  qMaxScore = 1.0;

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));

    if (id > 0) {
      this.templateId = id;
      this.loadTemplate(id);
    } else {
      // Default to logical reasoning 25 questions
      this.onTypeChange('logical_reasoning');
    }

    // Check query params or hash for active tab
    const tab = this.route.snapshot.queryParamMap.get('tab');
    if (tab === 'questions') {
      this.activeTab = 'questions';
    }
  }

  get availableCategories(): CategoryOption[] {
    const type = this.form.controls.assessment_type.value || 'logical_reasoning';
    return CATEGORY_MAP[type] || CATEGORY_MAP['logical_reasoning'];
  }

  get categoryGroups(): { domain: string; categories: CategoryOption[] }[] {
    const currentType = this.form.controls.assessment_type.value || 'logical_reasoning';
    const domainLabels: Record<string, string> = {
      english_grammar: 'English Grammar Categories',
      logical_reasoning: 'Logical Reasoning Categories',
      technical: 'Technical Assessment Categories',
      programming: 'Programming & Logic Categories',
      psychometric: 'Psychometric Categories'
    };

    const orderedKeys = [
      currentType,
      ...Object.keys(CATEGORY_MAP).filter(k => k !== currentType)
    ];

    return orderedKeys.map(k => ({
      domain: domainLabels[k] || k.replaceAll('_', ' ').toUpperCase(),
      categories: CATEGORY_MAP[k] || []
    }));
  }

  onTypeChange(type: 'psychometric' | 'technical' | 'english_grammar' | 'logical_reasoning' | 'programming'): void {
    const cats = CATEGORY_MAP[type] || [];
    if (cats.length > 0) {
      this.qCategory = cats[0].key;
    }

    if (type === 'logical_reasoning') {
      this.form.controls.question_count.setValue(25);
    } else {
      this.form.controls.question_count.setValue(20);
    }
    this.cdr.detectChanges();
  }

  setActiveTab(tab: 'config' | 'questions'): void {
    this.activeTab = tab;
    this.errorMessage = '';
    this.successMessage = '';
    this.questionError = '';
    this.questionSuccess = '';

    if (tab === 'questions' && this.templateId && this.bankQuestions.length === 0) {
      this.loadBankQuestions(this.templateId);
    }
    this.cdr.detectChanges();
  }

  // ----------------------------------------------------
  // Load Template (With full Zoneless Change Detection)
  // ----------------------------------------------------

  async loadTemplate(id: number): Promise<void> {
    this.loading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    try {
      // Try single template endpoint first
      let template: AssessmentTemplate | null = null;
      try {
        template = await firstValueFrom(this.api.getTemplate(id));
      } catch {
        // Fallback to getTemplates() array
        const list = await firstValueFrom(this.api.getTemplates());
        template = list.find(t => t.id === id) || null;
      }

      if (!template) {
        this.errorMessage = `Assessment template #${id} was not found.`;
      } else {
        this.template = template;
        this.form.patchValue({
          name: template.name,
          assessment_type: template.assessment_type || 'logical_reasoning',
          description: template.description ?? '',
          question_count: template.question_count || (template.assessment_type === 'logical_reasoning' ? 25 : 20),
        });

        // Set default category for manual authoring
        const cats = CATEGORY_MAP[template.assessment_type] || [];
        if (cats.length > 0) {
          this.qCategory = cats[0].key;
        }

        // Also load questions for this template
        await this.loadBankQuestions(id);
      }
    } catch (error: any) {
      console.error('Template load error:', error);
      this.errorMessage = this.parseErrorMessage(error, 'Unable to load assessment.');
    } finally {
      this.loading = false;
      this.cdr.detectChanges();
    }
  }

  // ----------------------------------------------------
  // Load Bank Questions
  // ----------------------------------------------------

  async loadBankQuestions(templateId: number): Promise<void> {
    this.loadingQuestions = true;
    this.questionError = '';
    this.cdr.detectChanges();

    try {
      const questions = await firstValueFrom(this.api.getBankQuestions(templateId));
      this.bankQuestions = Array.isArray(questions) ? questions : [];
    } catch (err: any) {
      console.warn('Bank questions load warning:', err);
      // Non-fatal if no questions exist yet
      this.bankQuestions = [];
    } finally {
      this.loadingQuestions = false;
      this.cdr.detectChanges();
    }
  }

  // ----------------------------------------------------
  // Save Template Settings
  // ----------------------------------------------------

  async save(): Promise<void> {
    this.errorMessage = '';
    this.successMessage = '';

    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.cdr.detectChanges();
      return;
    }

    const type = this.form.controls.assessment_type.value;
    const name = this.form.controls.name.value.trim();
    const description = this.form.controls.description.value.trim() || null;
    const questionCount = Number(this.form.controls.question_count.value) || 20;

    // Build category configuration
    const cats = CATEGORY_MAP[type] || [];
    const catConfig: Record<string, AssessmentCategory> = {};
    const perCat = Math.max(1, Math.floor(questionCount / (cats.length || 1)));

    for (const c of cats) {
      catConfig[c.key] = {
        label: c.label,
        question_count: perCat
      };
    }

    this.saving = true;
    this.cdr.detectChanges();

    try {
      if (this.templateId) {
        const updated = await firstValueFrom(
          this.api.updateTemplate(this.templateId, {
            name,
            assessment_type: type,
            description,
            question_count: questionCount,
            category_config: catConfig
          })
        );
        this.template = updated;
        this.successMessage = 'Assessment settings successfully updated.';
      } else {
        const created = await firstValueFrom(
          this.api.createTemplate({
            name,
            assessment_type: type,
            description,
            question_count: questionCount,
            category_config: catConfig
          })
        );
        this.templateId = created.id;
        this.template = created;
        this.successMessage = 'Assessment created successfully! You can now add questions below.';
        this.activeTab = 'questions';
      }
    } catch (error: any) {
      console.error('Template save error:', error);
      this.errorMessage = this.parseErrorMessage(error, 'Unable to save assessment.');
    } finally {
      this.saving = false;
      this.cdr.detectChanges();
    }
  }

  // ----------------------------------------------------
  // Manual Question Management
  // ----------------------------------------------------

  toggleAddQuestion(): void {
    this.showAddQuestionForm = !this.showAddQuestionForm;
    this.questionError = '';
    this.questionSuccess = '';
    this.cdr.detectChanges();
  }

  setCorrectOption(opt: 'A' | 'B' | 'C' | 'D'): void {
    this.qCorrectOption = opt;
    this.cdr.detectChanges();
  }

  parseErrorMessage(err: any, fallback: string = 'An unexpected error occurred'): string {
    if (!err) return fallback;
    const detail = err.error?.detail ?? err.error?.message ?? err.error ?? err.message;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item: any) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object') {
            const loc = Array.isArray(item.loc)
              ? item.loc.filter((x: any) => x !== 'body').join(' ')
              : '';
            const msg = item.msg || item.message || JSON.stringify(item);
            return loc ? `${loc}: ${msg}` : msg;
          }
          return String(item);
        })
        .filter(Boolean);
      return messages.length > 0 ? messages.join('. ') : fallback;
    }
    if (typeof detail === 'object' && detail !== null) {
      if (typeof detail.msg === 'string') return detail.msg;
      if (typeof detail.message === 'string') return detail.message;
      return JSON.stringify(detail);
    }
    return fallback;
  }

  async addManualQuestion(): Promise<void> {
    if (!this.templateId) {
      this.questionError = 'Please save the assessment first before authoring questions.';
      this.cdr.detectChanges();
      return;
    }

    this.questionError = '';
    this.questionSuccess = '';

    const text = (this.qText || '').trim();
    const optA = (this.qOptionA || '').trim();
    const optB = (this.qOptionB || '').trim();
    const optC = (this.qOptionC || '').trim();
    const optD = (this.qOptionD || '').trim();

    if (!text) {
      this.questionError = 'Question statement statement is required.';
      this.cdr.detectChanges();
      return;
    }

    if (text.length < 5) {
      this.questionError = 'Question statement must be at least 5 characters long.';
      this.cdr.detectChanges();
      return;
    }

    if (!optA || !optB || !optC || !optD) {
      this.questionError = 'All four answer choices (A, B, C, D) are required.';
      this.cdr.detectChanges();
      return;
    }

    let finalCategory = (this.qCategory || '').trim();
    if (this.qCategory === '__custom__') {
      finalCategory = (this.qCustomCategory || '').trim().toLowerCase().replaceAll(' ', '_');
    }
    if (!finalCategory || finalCategory.length < 2) {
      finalCategory = this.template?.assessment_type || 'general';
    }

    const correctOpt = ['A', 'B', 'C', 'D'].includes(this.qCorrectOption) ? this.qCorrectOption : 'A';
    const parsedScore = parseFloat(String(this.qMaxScore));
    const finalScore = (!isNaN(parsedScore) && parsedScore > 0) ? parsedScore : 1.0;

    const payload: CreateBankQuestionPayload = {
      category: finalCategory,
      difficulty: this.qDifficulty || 'Medium',
      question_type: 'multiple_choice',
      question_text: text,
      options: [
        { id: 'A', text: optA },
        { id: 'B', text: optB },
        { id: 'C', text: optC },
        { id: 'D', text: optD },
      ],
      correct_option_id: correctOpt,
      max_score: finalScore,
    };

    this.savingQuestion = true;
    this.cdr.detectChanges();

    try {
      const created = await firstValueFrom(
        this.api.createBankQuestion(this.templateId, payload)
      );

      this.bankQuestions.unshift(created);
      this.questionSuccess = `Question added successfully! (Total in bank: ${this.bankQuestions.length})`;

      // Reset question form
      this.qText = '';
      this.qOptionA = '';
      this.qOptionB = '';
      this.qOptionC = '';
      this.qOptionD = '';
      this.qCustomCategory = '';
      this.qCorrectOption = 'A';
      this.showAddQuestionForm = false;
    } catch (err: any) {
      console.error('Add question error:', err);
      this.questionError = this.parseErrorMessage(err, 'Failed to save question to question bank.');
    } finally {
      this.savingQuestion = false;
      this.cdr.detectChanges();
    }
  }

  async deleteQuestion(questionId: number): Promise<void> {
    if (!this.templateId) return;

    if (!confirm('Are you sure you want to delete this question from the question bank?')) {
      return;
    }

    this.deletingQuestionId = questionId;
    this.questionError = '';
    this.questionSuccess = '';
    this.cdr.detectChanges();

    try {
      await firstValueFrom(
        this.api.deleteBankQuestion(this.templateId, questionId)
      );

      this.bankQuestions = this.bankQuestions.filter(q => q.id !== questionId);
      this.questionSuccess = 'Question removed from question bank.';
    } catch (err: any) {
      console.error('Delete question error:', err);
      this.questionError = this.parseErrorMessage(err, 'Failed to delete question.');
    } finally {
      this.deletingQuestionId = null;
      this.cdr.detectChanges();
    }
  }

  categoryLabel(catKey: string): string {
    for (const group of Object.values(CATEGORY_MAP)) {
      const found = group.find(c => c.key === catKey);
      if (found) return found.label;
    }
    return catKey.replaceAll('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  cancel(): void {
    void this.router.navigate(['/assessments']);
  }
}
