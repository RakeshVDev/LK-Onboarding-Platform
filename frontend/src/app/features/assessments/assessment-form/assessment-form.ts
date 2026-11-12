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
  BankQuestionOption,
  CreateBankQuestionPayload,
  UpdateBankQuestionPayload,
  PreviewQuestionItem,
  AssignableCohortItem,
  AssignableLearnerItem
} from '../services/assessment';
import { QuestionRenderer, RenderableQuestion } from '../components/question-renderer/question-renderer';
import { AssessmentPreviewModal, PreviewDraftOverrides } from '../components/assessment-preview-modal/assessment-preview-modal';

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
    { key: 'personality_work_preferences', label: 'Personality & Work Preferences' },
    { key: 'logical_reasoning', label: 'Logical Reasoning' },
    { key: 'situational_judgement', label: 'Situational Judgement' },
    { key: 'emotional_intelligence', label: 'Emotional Intelligence' },
    { key: 'learning_adaptability', label: 'Learning & Adaptability' },
  ],
};

function defaultFourOptions(): BankQuestionOption[] {
  return [
    { id: 'A', text: '' },
    { id: 'B', text: '' },
    { id: 'C', text: '' },
    { id: 'D', text: '' },
  ];
}

@Component({
  selector: 'app-assessment-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    QuestionRenderer,
    AssessmentPreviewModal,
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
  editingQuestionId: number | null = null;
  deletingQuestionId: number | null = null;
  sequenceBusyQuestionId: number | null = null;
  questionError = '';
  questionSuccess = '';

  // Drag & drop + Sequence persistence state
  draggedQuestionId: number | null = null;
  dragOverQuestionId: number | null = null;
  reorderingSequence = false;
  sequenceStatus: 'idle' | 'saving' | 'saved' | 'error' = 'idle';

  // Preview modal state (Full Assessment or Single Question)
  isPreviewModalOpen = false;
  previewSingleQuestion: PreviewQuestionItem | null = null;
  previewSingleNumber = 1;
  previewSingleTotal = 1;
  previewModalTitle = 'Assessment Preview';

  // Live inline question preview inside Manual Question Form
  showInlineQuestionPreview = false;
  inlinePreviewMode: 'student' | 'admin' = 'student';
  inlinePreviewSelectedAnswer = '';

  // Assignment Target & Deadline state
  assignmentScope: 'all' | 'cohort' | 'learner' = 'all';
  selectedCohortIds: number[] = [];
  selectedLearnerIds: number[] = [];
  dueAtLocal = '';
  clearDueAt = false;
  availableCohorts: AssignableCohortItem[] = [];
  availableLearners: AssignableLearnerItem[] = [];
  loadingTargets = false;
  targetSearchQuery = '';

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

  // Manual Question Authoring Form (Create + Edit + Dynamic Options)
  qQuestionType: 'multiple_choice' | 'multiple_select' | 'true_false' = 'multiple_choice';
  qCategory = 'number_series';
  qCustomCategory = '';
  qDifficulty: 'Easy' | 'Medium' | 'Hard' = 'Medium';
  qText = '';
  qInstructions = '';
  qExplanation = '';
  qOptions: BankQuestionOption[] = defaultFourOptions();
  qCorrectOptionIds: string[] = ['A'];
  qMaxScore = 1.0;
  qNegativeMarks = 0.0;
  qAddToAssessment = true;

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    void this.loadAssignableTargets();

    if (id > 0) {
      this.templateId = id;
      this.loadTemplate(id);
    } else {
      this.onTypeChange('logical_reasoning');
    }

    const tab = this.route.snapshot.queryParamMap.get('tab');
    if (tab === 'questions') {
      this.activeTab = 'questions';
    }
  }

  get defaultDurationText(): string {
    const type = this.form.controls.assessment_type.value;
    return (type === 'logical_reasoning' || type === 'programming') ? '30 Minutes' : '15 Minutes';
  }

  get assignedQuestions(): BankQuestion[] {
    return this.bankQuestions
      .filter(q => q.in_assessment !== false)
      .slice()
      .sort((a, b) => {
        const oa = a.display_order ?? 999999;
        const ob = b.display_order ?? 999999;
        return oa !== ob ? oa - ob : a.id - b.id;
      });
  }

  get unassignedQuestions(): BankQuestion[] {
    return this.bankQuestions
      .filter(q => q.in_assessment === false)
      .slice()
      .sort((a, b) => b.id - a.id);
  }

  get inlinePreviewQuestionNumber(): number {
    if (!this.editingQuestionId) {
      return this.assignedQuestions.length + 1;
    }
    const idx = this.assignedQuestions.findIndex(q => q.id === this.editingQuestionId);
    return idx >= 0 ? idx + 1 : 1;
  }

  get inlinePreviewTotalCount(): number {
    if (!this.editingQuestionId) {
      return this.assignedQuestions.length + 1;
    }
    return Math.max(1, this.assignedQuestions.length);
  }

  get previewDraftOverrides(): PreviewDraftOverrides {
    return {
      name: this.form.controls.name.value?.trim() || undefined,
      description: this.form.controls.description.value?.trim() || null,
      assessment_type: this.form.controls.assessment_type.value,
    };
  }

  get liveDraftQuestion(): RenderableQuestion {
    const resolvedCategory = this.resolveSelectedCategory();
    const cleanOptions = this.qOptions.map((opt, idx) => ({
      id: String.fromCharCode(65 + idx),
      text: opt.text || '',
    }));

    const base: RenderableQuestion = {
      id: this.editingQuestionId ?? 0,
      category: resolvedCategory,
      difficulty: this.qDifficulty || 'Medium',
      question_type: this.qQuestionType,
      question_text: this.qText,
      instructions: this.qInstructions?.trim() ? this.qInstructions : null,
      options: cleanOptions,
      max_score: Number(this.qMaxScore) > 0 ? Number(this.qMaxScore) : 1.0,
      negative_marks: Number(this.qNegativeMarks) >= 0 ? Number(this.qNegativeMarks) : 0.0,
    };

    if (this.inlinePreviewMode === 'admin') {
      base.correct_option_ids = [...this.qCorrectOptionIds];
      base.correct_option_id = this.qCorrectOptionIds[0] || null;
      base.explanation = this.qExplanation?.trim() ? this.qExplanation : null;
    }

    return base;
  }

  get filteredCohorts(): AssignableCohortItem[] {
    const q = this.targetSearchQuery.trim().toLowerCase();
    if (!q) return this.availableCohorts;
    return this.availableCohorts.filter(c => c.name.toLowerCase().includes(q));
  }

  get filteredLearners(): AssignableLearnerItem[] {
    const q = this.targetSearchQuery.trim().toLowerCase();
    if (!q) return this.availableLearners;
    return this.availableLearners.filter(
      l => l.full_name.toLowerCase().includes(q) || l.email.toLowerCase().includes(q)
    );
  }

  async loadAssignableTargets(): Promise<void> {
    this.loadingTargets = true;
    this.cdr.detectChanges();
    try {
      const data = await firstValueFrom(this.api.getAssignableTargets());
      this.availableCohorts = Array.isArray(data?.cohorts) ? data.cohorts : [];
      this.availableLearners = Array.isArray(data?.learners) ? data.learners : [];
    } catch (err) {
      console.warn('Could not load assignable cohorts/students:', err);
    } finally {
      this.loadingTargets = false;
      this.cdr.detectChanges();
    }
  }

  onScopeChange(scope: 'all' | 'cohort' | 'learner'): void {
    this.assignmentScope = scope;
    this.targetSearchQuery = '';
    this.errorMessage = '';
    this.cdr.detectChanges();
  }

  isCohortSelected(id: number): boolean {
    return this.selectedCohortIds.includes(id);
  }

  toggleCohortSelection(id: number): void {
    if (this.isCohortSelected(id)) {
      this.selectedCohortIds = this.selectedCohortIds.filter(x => x !== id);
    } else {
      this.selectedCohortIds = [...this.selectedCohortIds, id];
    }
    this.cdr.detectChanges();
  }

  selectAllCohorts(): void {
    this.selectedCohortIds = this.filteredCohorts.map(c => c.id);
    this.cdr.detectChanges();
  }

  clearCohortsSelection(): void {
    this.selectedCohortIds = [];
    this.cdr.detectChanges();
  }

  isLearnerSelected(id: number): boolean {
    return this.selectedLearnerIds.includes(id);
  }

  toggleLearnerSelection(id: number): void {
    if (this.isLearnerSelected(id)) {
      this.selectedLearnerIds = this.selectedLearnerIds.filter(x => x !== id);
    } else {
      this.selectedLearnerIds = [...this.selectedLearnerIds, id];
    }
    this.cdr.detectChanges();
  }

  selectAllFilteredLearners(): void {
    const merged = new Set(this.selectedLearnerIds);
    for (const learner of this.filteredLearners) {
      merged.add(learner.id);
    }
    this.selectedLearnerIds = Array.from(merged);
    this.cdr.detectChanges();
  }

  clearLearnersSelection(): void {
    this.selectedLearnerIds = [];
    this.cdr.detectChanges();
  }

  onDueDateInputChange(val: string): void {
    this.dueAtLocal = val;
    this.clearDueAt = !val;
    this.cdr.detectChanges();
  }

  clearDeadline(): void {
    this.dueAtLocal = '';
    this.clearDueAt = true;
    this.cdr.detectChanges();
  }

  private toDateTimeLocalInput(isoDate: string): string {
    const dt = new Date(isoDate);
    if (isNaN(dt.getTime())) return '';
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
  }

  private toIsoDueAt(): string | null {
    if (!this.dueAtLocal) return null;
    const dt = new Date(this.dueAtLocal);
    if (isNaN(dt.getTime())) return null;
    return dt.toISOString();
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
    if (cats.length > 0 && !this.editingQuestionId) {
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
      void this.loadBankQuestions(this.templateId);
    }
    this.cdr.detectChanges();
  }

  // ----------------------------------------------------
  // Load Template
  // ----------------------------------------------------

  async loadTemplate(id: number): Promise<void> {
    this.loading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    try {
      let template: AssessmentTemplate | null = null;
      try {
        template = await firstValueFrom(this.api.getTemplate(id));
      } catch {
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

        this.assignmentScope =
          (template.assignment_scope as 'all' | 'cohort' | 'learner') || 'all';
        this.selectedCohortIds = [...(template.assigned_cohort_ids || [])];
        this.selectedLearnerIds = [...(template.assigned_learner_ids || [])];
        this.dueAtLocal = template.due_at ? this.toDateTimeLocalInput(template.due_at) : '';
        this.clearDueAt = false;

        const cats = CATEGORY_MAP[template.assessment_type] || [];
        if (cats.length > 0) {
          this.qCategory = cats[0].key;
        }

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
      const questions = await firstValueFrom(this.api.getBankQuestions(templateId, true));
      this.bankQuestions = Array.isArray(questions) ? questions : [];
    } catch (err: any) {
      console.warn('Bank questions load warning:', err);
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

    if (this.assignmentScope === 'cohort' && this.selectedCohortIds.length === 0) {
      this.errorMessage = 'Please select at least one cohort when assigning by Cohort.';
      this.cdr.detectChanges();
      return;
    }

    if (this.assignmentScope === 'learner' && this.selectedLearnerIds.length === 0) {
      this.errorMessage = 'Please select at least one student when assigning individually.';
      this.cdr.detectChanges();
      return;
    }

    const type = this.form.controls.assessment_type.value;
    const name = this.form.controls.name.value.trim();
    const description = this.form.controls.description.value.trim() || null;
    const questionCount = Number(this.form.controls.question_count.value) || 20;
    const dueIso = this.toIsoDueAt();
    const cohortIdsPayload = this.assignmentScope === 'cohort' ? this.selectedCohortIds : [];
    const learnerIdsPayload = this.assignmentScope === 'learner' ? this.selectedLearnerIds : [];

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
            category_config: catConfig,
            assignment_scope: this.assignmentScope,
            cohort_ids: cohortIdsPayload,
            learner_ids: learnerIdsPayload,
            due_at: dueIso,
            clear_due_at: !dueIso && (this.clearDueAt || Boolean(this.template?.due_at))
          })
        );
        this.template = updated;
        this.successMessage = 'Assessment settings and assignments successfully updated.';
      } else {
        const created = await firstValueFrom(
          this.api.createTemplate({
            name,
            assessment_type: type,
            description,
            question_count: questionCount,
            category_config: catConfig,
            assignment_scope: this.assignmentScope,
            cohort_ids: cohortIdsPayload,
            learner_ids: learnerIdsPayload,
            due_at: dueIso
          })
        );
        this.templateId = created.id;
        this.template = created;
        this.successMessage = 'Assessment created and assigned successfully! You can now add questions below.';
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
  // Full Assessment & Question Modals
  // ----------------------------------------------------

  openAssessmentPreview(): void {
    if (!this.templateId) return;
    this.previewSingleQuestion = null;
    this.previewModalTitle = this.previewDraftOverrides.name || 'Assessment Preview';
    this.isPreviewModalOpen = true;
    this.cdr.detectChanges();
  }

  previewBankQuestion(q: BankQuestion, index: number, total: number): void {
    this.previewSingleNumber = index + 1;
    this.previewSingleTotal = Math.max(1, total);
    this.previewModalTitle = this.template?.name || 'Question Bank Preview';
    this.previewSingleQuestion = {
      id: q.id,
      source: 'bank',
      category: q.category,
      difficulty: q.difficulty,
      question_type: q.question_type,
      question_text: q.question_text,
      instructions: q.instructions,
      options: q.options.map(o => ({ ...o })),
      display_order: q.display_order ?? (index + 1),
      max_score: q.max_score,
      negative_marks: q.negative_marks ?? 0,
      correct_option_id: q.correct_option_id ?? null,
      correct_option_ids: q.correct_option_ids ? [...q.correct_option_ids] : [],
      explanation: q.explanation ?? null,
    };
    this.isPreviewModalOpen = true;
    this.cdr.detectChanges();
  }

  closePreviewModal(): void {
    this.isPreviewModalOpen = false;
    this.previewSingleQuestion = null;
    this.cdr.detectChanges();
  }

  // ----------------------------------------------------
  // Manual Question Authoring Form (Create, Edit, Options, Live Preview)
  // ----------------------------------------------------

  toggleAddQuestion(): void {
    if (this.showAddQuestionForm) {
      this.closeQuestionForm();
    } else {
      this.openNewQuestionForm();
    }
  }

  openNewQuestionForm(): void {
    this.resetQuestionFormState();
    this.editingQuestionId = null;
    this.showAddQuestionForm = true;
    this.questionError = '';
    this.questionSuccess = '';
    this.cdr.detectChanges();
  }

  closeQuestionForm(): void {
    this.showAddQuestionForm = false;
    this.editingQuestionId = null;
    this.resetQuestionFormState();
    this.cdr.detectChanges();
  }

  startEditQuestion(q: BankQuestion): void {
    this.questionError = '';
    this.questionSuccess = '';
    this.editingQuestionId = q.id;
    this.showAddQuestionForm = true;
    this.showInlineQuestionPreview = false;
    this.inlinePreviewSelectedAnswer = '';

    const normalizedType = (q.question_type || 'multiple_choice').trim().toLowerCase();
    if (normalizedType === 'multiple_select') {
      this.qQuestionType = 'multiple_select';
    } else if (normalizedType === 'true_false') {
      this.qQuestionType = 'true_false';
    } else {
      this.qQuestionType = 'multiple_choice';
    }

    const foundInMap = Object.values(CATEGORY_MAP).some(list =>
      list.some(c => c.key === q.category)
    );
    if (foundInMap) {
      this.qCategory = q.category;
      this.qCustomCategory = '';
    } else {
      this.qCategory = '__custom__';
      this.qCustomCategory = q.category;
    }

    this.qDifficulty =
      q.difficulty === 'Easy' || q.difficulty === 'Hard' ? q.difficulty : 'Medium';
    this.qText = q.question_text || '';
    this.qInstructions = q.instructions || '';
    this.qExplanation = q.explanation || '';
    this.qMaxScore = Number(q.max_score) > 0 ? Number(q.max_score) : 1.0;
    this.qNegativeMarks = Number(q.negative_marks ?? 0) >= 0 ? Number(q.negative_marks ?? 0) : 0.0;
    this.qAddToAssessment = q.in_assessment !== false;

    const rawOptions = Array.isArray(q.options) && q.options.length >= 2
      ? q.options
      : defaultFourOptions();

    const oldToNewId = new Map<string, string>();
    this.qOptions = rawOptions.map((opt, idx) => {
      const nextId = String.fromCharCode(65 + idx);
      const oldId = String(opt.id || nextId).trim().toUpperCase();
      oldToNewId.set(oldId, nextId);
      return {
        id: nextId,
        text: opt.text || '',
      };
    });

    const sourceCorrect =
      Array.isArray(q.correct_option_ids) && q.correct_option_ids.length > 0
        ? q.correct_option_ids
        : q.correct_option_id
        ? [q.correct_option_id]
        : [];

    const mappedCorrect = sourceCorrect
      .map(id => oldToNewId.get(String(id).trim().toUpperCase()) || String(id).trim().toUpperCase())
      .filter(id => this.qOptions.some(o => o.id === id));

    this.qCorrectOptionIds =
      this.qQuestionType === 'multiple_select'
        ? Array.from(new Set(mappedCorrect))
        : mappedCorrect.slice(0, 1);

    this.cdr.detectChanges();

    setTimeout(() => {
      document.getElementById('manual-question-editor')?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }, 30);
  }

  private resetQuestionFormState(): void {
    const type = this.form.controls.assessment_type.value || 'logical_reasoning';
    const cats = CATEGORY_MAP[type] || [];
    this.qCategory = cats[0]?.key || 'general';
    this.qCustomCategory = '';
    this.qDifficulty = 'Medium';
    this.qQuestionType = 'multiple_choice';
    this.qText = '';
    this.qInstructions = '';
    this.qExplanation = '';
    this.qOptions = defaultFourOptions();
    this.qCorrectOptionIds = ['A'];
    this.qMaxScore = 1.0;
    this.qNegativeMarks = 0.0;
    this.qAddToAssessment = true;
    this.showInlineQuestionPreview = false;
    this.inlinePreviewMode = 'student';
    this.inlinePreviewSelectedAnswer = '';
  }

  onQuestionTypeChange(nextType: 'multiple_choice' | 'multiple_select' | 'true_false'): void {
    this.qQuestionType = nextType;
    this.inlinePreviewSelectedAnswer = '';

    if (nextType === 'true_false') {
      const firstText = this.qOptions[0]?.text?.trim();
      const secondText = this.qOptions[1]?.text?.trim();
      this.qOptions = [
        { id: 'A', text: firstText && firstText !== '' ? firstText : 'True' },
        { id: 'B', text: secondText && secondText !== '' ? secondText : 'False' },
      ];
      const valid = this.qCorrectOptionIds.filter(id => id === 'A' || id === 'B');
      this.qCorrectOptionIds = valid.length > 0 ? [valid[0]] : ['A'];
    } else if (nextType === 'multiple_choice') {
      if (this.qOptions.length === 2 && this.qOptions[0].text === 'True' && this.qOptions[1].text === 'False') {
        this.qOptions = defaultFourOptions();
      }
      const validIds = new Set(this.qOptions.map(o => o.id));
      const valid = this.qCorrectOptionIds.filter(id => validIds.has(id));
      this.qCorrectOptionIds = valid.length > 0 ? [valid[0]] : ['A'];
    } else {
      // multiple_select
      if (this.qOptions.length < 2) {
        this.qOptions = defaultFourOptions();
      }
      const validIds = new Set(this.qOptions.map(o => o.id));
      this.qCorrectOptionIds = this.qCorrectOptionIds.filter(id => validIds.has(id));
    }

    this.cdr.detectChanges();
  }

  addOption(): void {
    if (this.qQuestionType === 'true_false' || this.qOptions.length >= 10) {
      return;
    }
    const nextId = String.fromCharCode(65 + this.qOptions.length);
    this.qOptions = [...this.qOptions, { id: nextId, text: '' }];
    this.cdr.detectChanges();
  }

  removeOption(index: number): void {
    if (this.qQuestionType === 'true_false' || this.qOptions.length <= 2) {
      return;
    }
    const oldSelected = new Set(this.qCorrectOptionIds);
    const kept = this.qOptions
      .filter((_, i) => i !== index)
      .map(opt => ({
        text: opt.text,
        wasCorrect: oldSelected.has(opt.id),
      }));

    const relabeled: BankQuestionOption[] = [];
    const nextCorrect: string[] = [];
    kept.forEach((item, idx) => {
      const id = String.fromCharCode(65 + idx);
      relabeled.push({ id, text: item.text });
      if (item.wasCorrect) {
        nextCorrect.push(id);
      }
    });

    this.qOptions = relabeled;
    this.qCorrectOptionIds =
      this.qQuestionType === 'multiple_select' ? nextCorrect : nextCorrect.slice(0, 1);
    this.inlinePreviewSelectedAnswer = '';
    this.cdr.detectChanges();
  }

  isOptionCorrectSelected(optionId: string): boolean {
    return this.qCorrectOptionIds.includes(optionId);
  }

  onCorrectAnswerInputChange(optionId: string, checked?: boolean): void {
    if (this.qQuestionType === 'multiple_select') {
      const exists = this.qCorrectOptionIds.includes(optionId);
      const shouldSelect = checked !== undefined ? checked : !exists;
      if (shouldSelect && !exists) {
        this.qCorrectOptionIds = [...this.qCorrectOptionIds, optionId];
      } else if (!shouldSelect && exists) {
        this.qCorrectOptionIds = this.qCorrectOptionIds.filter(id => id !== optionId);
      }
    } else {
      this.qCorrectOptionIds = [optionId];
    }
    this.cdr.detectChanges();
  }

  toggleInlineQuestionPreview(): void {
    this.showInlineQuestionPreview = !this.showInlineQuestionPreview;
    this.inlinePreviewSelectedAnswer = '';
    this.cdr.detectChanges();
  }

  setInlinePreviewMode(mode: 'student' | 'admin'): void {
    this.inlinePreviewMode = mode;
    this.cdr.detectChanges();
  }

  onInlinePreviewAnswerChange(val: string): void {
    this.inlinePreviewSelectedAnswer = val;
    this.cdr.detectChanges();
  }

  onInlinePreviewAnswerClear(): void {
    this.inlinePreviewSelectedAnswer = '';
    this.cdr.detectChanges();
  }

  private resolveSelectedCategory(): string {
    let finalCategory = (this.qCategory || '').trim();
    if (this.qCategory === '__custom__') {
      finalCategory = (this.qCustomCategory || '').trim().toLowerCase().replaceAll(' ', '_');
    }
    if (!finalCategory || finalCategory.length < 2) {
      finalCategory = this.template?.assessment_type || 'general';
    }
    return finalCategory;
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

  async saveManualQuestion(): Promise<void> {
    if (!this.templateId) {
      this.questionError = 'Please save the assessment first before authoring questions.';
      this.cdr.detectChanges();
      return;
    }

    this.questionError = '';
    this.questionSuccess = '';

    const text = (this.qText || '').trim();
    if (!text) {
      this.questionError = 'Question statement is required.';
      this.cdr.detectChanges();
      return;
    }

    if (text.length < 5) {
      this.questionError = 'Question statement must be at least 5 characters long.';
      this.cdr.detectChanges();
      return;
    }

    if (this.qOptions.length < 2) {
      this.questionError = 'At least 2 answer options are required.';
      this.cdr.detectChanges();
      return;
    }

    if (this.qQuestionType === 'true_false' && this.qOptions.length !== 2) {
      this.questionError = 'True / False questions require exactly 2 answer options.';
      this.cdr.detectChanges();
      return;
    }

    const cleanOptions: BankQuestionOption[] = [];
    for (let i = 0; i < this.qOptions.length; i++) {
      const id = String.fromCharCode(65 + i);
      const optText = (this.qOptions[i].text || '').trim();
      if (!optText) {
        this.questionError = `Option ${id} cannot be empty. Please fill in text or remove unused options.`;
        this.cdr.detectChanges();
        return;
      }
      cleanOptions.push({ id, text: optText });
    }

    const validIds = new Set(cleanOptions.map(o => o.id));
    const orderedCorrect = cleanOptions
      .map(o => o.id)
      .filter(id => this.qCorrectOptionIds.includes(id));

    if (orderedCorrect.length === 0) {
      this.questionError = 'Please select at least one correct answer before saving.';
      this.cdr.detectChanges();
      return;
    }

    if (this.qQuestionType !== 'multiple_select' && orderedCorrect.length !== 1) {
      this.questionError = 'Single-choice questions require exactly one selected correct answer.';
      this.cdr.detectChanges();
      return;
    }

    if (orderedCorrect.some(id => !validIds.has(id))) {
      this.questionError = 'Selected correct answer does not match active options.';
      this.cdr.detectChanges();
      return;
    }

    const parsedScore = parseFloat(String(this.qMaxScore));
    if (isNaN(parsedScore) || parsedScore <= 0) {
      this.questionError = 'Marks for correct answer must be greater than 0.';
      this.cdr.detectChanges();
      return;
    }

    const parsedNeg = parseFloat(String(this.qNegativeMarks || 0));
    if (isNaN(parsedNeg) || parsedNeg < 0) {
      this.questionError = 'Negative marks cannot be negative.';
      this.cdr.detectChanges();
      return;
    }

    const finalCategory = this.resolveSelectedCategory();
    const instructionsVal = (this.qInstructions || '').trim() || null;
    const explanationVal = (this.qExplanation || '').trim() || null;

    this.savingQuestion = true;
    this.cdr.detectChanges();

    try {
      if (this.editingQuestionId) {
        const updatePayload: UpdateBankQuestionPayload = {
          category: finalCategory,
          difficulty: this.qDifficulty || 'Medium',
          question_type: this.qQuestionType,
          question_text: text,
          instructions: instructionsVal,
          explanation: explanationVal,
          options: cleanOptions,
          correct_option_id: orderedCorrect[0],
          correct_option_ids: orderedCorrect,
          max_score: parsedScore,
          negative_marks: parsedNeg,
        };
        const updated = await firstValueFrom(
          this.api.updateBankQuestion(this.templateId, this.editingQuestionId, updatePayload)
        );
        this.bankQuestions = this.bankQuestions.map(item =>
          item.id === updated.id ? updated : item
        );
        this.questionSuccess = `Question updated cleanly!`;
      } else {
        const createPayload: CreateBankQuestionPayload = {
          category: finalCategory,
          difficulty: this.qDifficulty || 'Medium',
          question_type: this.qQuestionType,
          question_text: text,
          instructions: instructionsVal,
          explanation: explanationVal,
          options: cleanOptions,
          correct_option_id: orderedCorrect[0],
          correct_option_ids: orderedCorrect,
          max_score: parsedScore,
          negative_marks: parsedNeg,
          in_assessment: this.qAddToAssessment,
        };
        const created = await firstValueFrom(
          this.api.createBankQuestion(this.templateId, createPayload)
        );
        this.bankQuestions = [...this.bankQuestions, created];
        this.questionSuccess = this.qAddToAssessment
          ? `Question added at position #${created.display_order || this.assignedQuestions.length}!`
          : `Question saved to reusable bank pool.`;
      }

      this.showAddQuestionForm = false;
      this.editingQuestionId = null;
      this.resetQuestionFormState();
    } catch (err: any) {
      console.error('Save question error:', err);
      this.questionError = this.parseErrorMessage(err, 'Failed to save question.');
    } finally {
      this.savingQuestion = false;
      this.cdr.detectChanges();
    }
  }

  // ----------------------------------------------------
  // Drag & Drop + Button Sequence Management
  // ----------------------------------------------------

  onDragStart(event: DragEvent, questionId: number): void {
    if (this.reorderingSequence) {
      event.preventDefault();
      return;
    }
    this.draggedQuestionId = questionId;
    this.dragOverQuestionId = null;
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', String(questionId));
    }
    this.cdr.detectChanges();
  }

  onDragOver(event: DragEvent, targetQuestionId: number): void {
    if (this.draggedQuestionId === null || this.draggedQuestionId === targetQuestionId) {
      return;
    }
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move';
    }
    if (this.dragOverQuestionId !== targetQuestionId) {
      this.dragOverQuestionId = targetQuestionId;
      this.cdr.detectChanges();
    }
  }

  onDragLeave(targetQuestionId: number): void {
    if (this.dragOverQuestionId === targetQuestionId) {
      this.dragOverQuestionId = null;
      this.cdr.detectChanges();
    }
  }

  onDrop(event: DragEvent, targetQuestionId: number): void {
    event.preventDefault();
    const rawId = event.dataTransfer?.getData('text/plain');
    const sourceId = this.draggedQuestionId ?? (rawId ? Number(rawId) : null);
    this.draggedQuestionId = null;
    this.dragOverQuestionId = null;

    if (!sourceId || sourceId === targetQuestionId) {
      this.cdr.detectChanges();
      return;
    }

    const current = this.assignedQuestions.slice();
    const fromIdx = current.findIndex(q => q.id === sourceId);
    const toIdx = current.findIndex(q => q.id === targetQuestionId);
    if (fromIdx < 0 || toIdx < 0 || fromIdx === toIdx) {
      this.cdr.detectChanges();
      return;
    }

    const [moved] = current.splice(fromIdx, 1);
    current.splice(toIdx, 0, moved);
    void this.persistQuestionSequence(current);
  }

  onDragEnd(): void {
    this.draggedQuestionId = null;
    this.dragOverQuestionId = null;
    this.cdr.detectChanges();
  }

  moveQuestionStep(index: number, delta: -1 | 1): void {
    if (this.reorderingSequence) return;
    const current = this.assignedQuestions.slice();
    const targetIdx = index + delta;
    if (index < 0 || targetIdx < 0 || targetIdx >= current.length) return;

    const [moved] = current.splice(index, 1);
    current.splice(targetIdx, 0, moved);
    void this.persistQuestionSequence(current);
  }

  private async persistQuestionSequence(orderedAssigned: BankQuestion[]): Promise<void> {
    if (!this.templateId) return;

    const previousSnapshot = this.bankQuestions.map(q => ({ ...q }));
    const unassigned = this.unassignedQuestions;

    // Optimistically update local display_order for instant responsiveness
    const optimisticAssigned = orderedAssigned.map((q, idx) => ({
      ...q,
      in_assessment: true,
      display_order: idx + 1,
    }));
    this.bankQuestions = [...optimisticAssigned, ...unassigned];
    this.reorderingSequence = true;
    this.sequenceStatus = 'saving';
    this.questionError = '';
    this.cdr.detectChanges();

    try {
      const orderedIds = orderedAssigned.map(q => q.id);
      const serverQuestions = await firstValueFrom(
        this.api.reorderBankQuestions(this.templateId, orderedIds)
      );
      if (Array.isArray(serverQuestions)) {
        this.bankQuestions = serverQuestions;
      }
      this.sequenceStatus = 'saved';
      this.cdr.detectChanges();

      setTimeout(() => {
        if (this.sequenceStatus === 'saved') {
          this.sequenceStatus = 'idle';
          this.cdr.detectChanges();
        }
      }, 2400);
    } catch (err: any) {
      console.error('Reorder failed:', err);
      this.bankQuestions = previousSnapshot;
      this.sequenceStatus = 'error';
      this.questionError = this.parseErrorMessage(
        err,
        'Failed to save new question sequence. Order has been restored.'
      );
    } finally {
      this.reorderingSequence = false;
      this.cdr.detectChanges();
    }
  }

  async removeQuestionFromAssessment(questionId: number): Promise<void> {
    if (!this.templateId || this.sequenceBusyQuestionId) return;
    this.sequenceBusyQuestionId = questionId;
    this.questionError = '';
    this.questionSuccess = '';
    this.cdr.detectChanges();

    try {
      const updated = await firstValueFrom(
        this.api.removeQuestionFromAssessment(this.templateId, questionId)
      );
      this.bankQuestions = Array.isArray(updated) ? updated : [];
      this.questionSuccess =
        'Question removed from assessment sequence and preserved in the Question Bank Pool.';
    } catch (err: any) {
      console.error('Remove from assessment error:', err);
      this.questionError = this.parseErrorMessage(
        err,
        'Failed to remove question from assessment.'
      );
    } finally {
      this.sequenceBusyQuestionId = null;
      this.cdr.detectChanges();
    }
  }

  async addQuestionToAssessment(questionId: number): Promise<void> {
    if (!this.templateId || this.sequenceBusyQuestionId) return;
    this.sequenceBusyQuestionId = questionId;
    this.questionError = '';
    this.questionSuccess = '';
    this.cdr.detectChanges();

    try {
      const updated = await firstValueFrom(
        this.api.assignQuestionToAssessment(this.templateId, questionId)
      );
      this.bankQuestions = Array.isArray(updated) ? updated : [];
      this.questionSuccess = 'Question added to assessment sequence.';
    } catch (err: any) {
      console.error('Assign to assessment error:', err);
      this.questionError = this.parseErrorMessage(
        err,
        'Failed to add question to assessment.'
      );
    } finally {
      this.sequenceBusyQuestionId = null;
      this.cdr.detectChanges();
    }
  }

  async deleteQuestion(questionId: number): Promise<void> {
    if (!this.templateId) return;

    if (!confirm('Permanently delete this question from the question bank? This action cannot be undone.')) {
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

      if (this.editingQuestionId === questionId) {
        this.closeQuestionForm();
      }
      await this.loadBankQuestions(this.templateId);
      this.questionSuccess = 'Question permanently deleted and remaining sequence updated.';
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

  questionTypeLabel(type?: string): string {
    switch ((type || 'multiple_choice').toLowerCase()) {
      case 'multiple_select':
        return 'Multi-Select';
      case 'true_false':
        return 'True / False';
      default:
        return 'Single MCQ';
    }
  }

  isQuestionOptionCorrect(q: BankQuestion, optionId: string): boolean {
    const norm = String(optionId || '').trim().toUpperCase();
    if (Array.isArray(q.correct_option_ids) && q.correct_option_ids.length > 0) {
      return q.correct_option_ids.some(id => String(id).trim().toUpperCase() === norm);
    }
    return String(q.correct_option_id || '').trim().toUpperCase() === norm;
  }

  cancel(): void {
    void this.router.navigate(['/assessments']);
  }
}
