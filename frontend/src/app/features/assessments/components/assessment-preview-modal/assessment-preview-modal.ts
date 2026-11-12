import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  HostListener,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { firstValueFrom } from 'rxjs';

import {
  AssessmentService,
  AssessmentTemplatePreview,
  PreviewQuestionItem,
} from '../../services/assessment';
import { QuestionRenderer } from '../question-renderer/question-renderer';

export interface PreviewDraftOverrides {
  name?: string;
  description?: string | null;
  assessment_type?: string;
}

@Component({
  selector: 'app-assessment-preview-modal',
  standalone: true,
  imports: [CommonModule, QuestionRenderer],
  templateUrl: './assessment-preview-modal.html',
  styleUrl: './assessment-preview-modal.scss',
})
export class AssessmentPreviewModal implements OnChanges {
  private readonly api = inject(AssessmentService);
  private readonly cdr = inject(ChangeDetectorRef);

  @Input() isOpen = false;
  @Input() templateId: number | null = null;
  @Input() draftOverrides: PreviewDraftOverrides | null = null;

  // Optional single-question preview mode (e.g., clicking Preview on a bank question card)
  @Input() singleQuestion: PreviewQuestionItem | null = null;
  @Input() singleQuestionNumber = 1;
  @Input() singleTotalQuestions = 1;
  @Input() contextTitle = 'Question Preview';

  @Output() closed = new EventEmitter<void>();

  previewMode: 'student' | 'admin' = 'student';
  customOnly = false;
  showInstructions = true;

  loading = false;
  errorMessage = '';
  previewData: AssessmentTemplatePreview | null = null;
  hasBothCustomAndBuiltin = false;

  currentIndex = 0;
  localAnswers: Record<number, string> = {};
  visitedQuestions: Set<number> = new Set();
  markedForReview: Set<number> = new Set();
  showSummaryView = false;

  ngOnChanges(changes: SimpleChanges): void {
    const openedNow = Boolean(changes['isOpen']?.currentValue);
    const templateChanged = Boolean(changes['templateId']);
    const singleChanged = Boolean(changes['singleQuestion']);

    if (!this.isOpen) {
      return;
    }

    if (openedNow || singleChanged || templateChanged) {
      this.showSummaryView = false;
      this.errorMessage = '';

      if (this.singleQuestion) {
        this.previewData = null;
        this.localAnswers = {};
        this.visitedQuestions = new Set([this.singleQuestion.id || 0]);
        this.markedForReview = new Set();
        this.cdr.detectChanges();
        return;
      }

      if (this.templateId) {
        this.currentIndex = 0;
        this.localAnswers = {};
        this.visitedQuestions = new Set();
        this.markedForReview = new Set();
        this.customOnly = false;
        void this.loadTemplatePreview();
      }
    }
  }

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    if (this.isOpen) {
      this.close();
    }
  }

  async loadTemplatePreview(): Promise<void> {
    if (!this.templateId) return;
    this.loading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    try {
      const data = await firstValueFrom(
        this.api.previewTemplate(this.templateId, this.previewMode, this.customOnly)
      );
      this.previewData = data;
      if (!this.customOnly) {
        this.hasBothCustomAndBuiltin =
          data.custom_question_count > 0 && data.builtin_question_count > 0;
      }
      if (data.questions.length > 0) {
        if (this.currentIndex >= data.questions.length) {
          this.currentIndex = 0;
        }
        this.visitedQuestions.add(data.questions[this.currentIndex].id);
      }
    } catch (err: any) {
      console.error('Assessment preview failed:', err);
      this.errorMessage =
        err?.error?.detail || err?.message || 'Unable to load assessment preview.';
    } finally {
      this.loading = false;
      this.cdr.detectChanges();
    }
  }

  get isSingleQuestionMode(): boolean {
    return !!this.singleQuestion;
  }

  get rendererMode(): 'student_preview' | 'admin_preview' {
    return this.previewMode === 'admin' ? 'admin_preview' : 'student_preview';
  }

  get displayTitle(): string {
    if (this.draftOverrides?.name && this.draftOverrides.name.trim()) {
      return this.draftOverrides.name.trim();
    }
    return this.previewData?.template_name || this.contextTitle;
  }

  get displayInstructions(): string {
    if (!this.previewData) return '';
    if (this.draftOverrides?.description !== undefined) {
      const desc = (this.draftOverrides.description || '').trim();
      const totalQ = this.previewData.total_questions;
      const totalM = this.previewData.total_marks;
      const dur = this.previewData.duration_minutes;
      const base = `This assessment contains ${totalQ} question(s) worth ${totalM} total mark(s), with a strict time limit of ${dur} minutes. Select the best answer(s) before submitting.`;
      return desc ? `${desc}\n\n${base}` : base;
    }
    return this.previewData.instructions;
  }

  get formattedDuration(): string {
    const mins = this.previewData?.duration_minutes ?? 15;
    return `${String(mins).padStart(2, '0')}:00`;
  }

  get questions(): PreviewQuestionItem[] {
    return this.previewData?.questions || [];
  }

  get currentQuestion(): PreviewQuestionItem | null {
    if (this.singleQuestion) {
      return this.sanitizeQuestion(this.singleQuestion);
    }
    const q = this.questions[this.currentIndex] || null;
    return q ? this.sanitizeQuestion(q) : null;
  }

  private sanitizeQuestion(q: PreviewQuestionItem): PreviewQuestionItem {
    if (this.previewMode === 'admin') {
      return q;
    }
    // Enforce zero answer-key leakage in Student Preview
    return {
      ...q,
      correct_option_id: null,
      correct_option_ids: null,
      explanation: null,
    };
  }

  get singleSelectedAnswer(): string {
    if (!this.singleQuestion) return '';
    return this.localAnswers[this.singleQuestion.id || 0] || '';
  }

  get currentQuestionAnswer(): string {
    const q = this.currentQuestion;
    if (!q) return '';
    return this.localAnswers[q.id || 0] || '';
  }

  get answeredCount(): number {
    return this.questions.filter(q => Boolean((this.localAnswers[q.id] || '').trim())).length;
  }

  get unansweredCount(): number {
    return Math.max(0, this.questions.length - this.answeredCount);
  }

  get markedCount(): number {
    return this.markedForReview.size;
  }

  get simulatedScoreSummary(): { earned: number; max: number; correct: number } {
    let earned = 0;
    let max = 0;
    let correct = 0;

    for (const q of this.questions) {
      const qMax = Number(q.max_score || 1);
      const qNeg = Number(q.negative_marks || 0);
      max += qMax;

      const userAns = (this.localAnswers[q.id] || '').trim();
      if (!userAns) continue;

      const expected = new Set(
        (q.correct_option_ids && q.correct_option_ids.length
          ? q.correct_option_ids
          : q.correct_option_id
          ? [q.correct_option_id]
          : []
        ).map(s => String(s).trim().toUpperCase())
      );

      if (expected.size === 0) continue;

      const actual = new Set(
        userAns
          .split(',')
          .map(s => s.trim().toUpperCase())
          .filter(Boolean)
      );

      const exactMatch =
        actual.size === expected.size &&
        Array.from(expected).every(k => actual.has(k));

      if (exactMatch) {
        earned += qMax;
        correct += 1;
      } else if (qNeg > 0) {
        earned -= qNeg;
      }
    }

    return {
      earned: Math.max(0, Number(earned.toFixed(2))),
      max: Number(max.toFixed(2)),
      correct,
    };
  }

  setMode(mode: 'student' | 'admin'): void {
    if (this.previewMode === mode) return;
    this.previewMode = mode;
    if (this.templateId && !this.singleQuestion) {
      void this.loadTemplatePreview();
    } else {
      this.cdr.detectChanges();
    }
  }

  toggleScope(customOnly: boolean): void {
    if (this.customOnly === customOnly || !this.templateId) return;
    this.customOnly = customOnly;
    this.currentIndex = 0;
    this.showSummaryView = false;
    void this.loadTemplatePreview();
  }

  toggleInstructions(): void {
    this.showInstructions = !this.showInstructions;
    this.cdr.detectChanges();
  }

  getQuestionState(q: PreviewQuestionItem): string {
    const isAnswered = Boolean((this.localAnswers[q.id] || '').trim());
    const isReview = this.markedForReview.has(q.id);
    const isVisited = this.visitedQuestions.has(q.id);
    if (isAnswered && isReview) return 'answered-review';
    if (isReview) return 'review';
    if (isAnswered) return 'answered';
    if (isVisited) return 'not-answered';
    return 'not-visited';
  }

  onAnswerSelected(questionId: number | undefined, value: string): void {
    const key = questionId ?? 0;
    const next = { ...this.localAnswers };
    if (!value || !value.trim()) {
      delete next[key];
    } else {
      next[key] = value;
    }
    this.localAnswers = next;
    this.visitedQuestions.add(key);
    this.cdr.detectChanges();
  }

  onClearAnswer(questionId: number | undefined): void {
    const key = questionId ?? 0;
    const next = { ...this.localAnswers };
    delete next[key];
    this.localAnswers = next;
    this.cdr.detectChanges();
  }

  toggleReview(questionId: number): void {
    if (this.markedForReview.has(questionId)) {
      this.markedForReview.delete(questionId);
    } else {
      this.markedForReview.add(questionId);
    }
    this.visitedQuestions.add(questionId);
    this.cdr.detectChanges();
  }

  goTo(index: number): void {
    if (index < 0 || index >= this.questions.length) return;
    this.showSummaryView = false;
    this.currentIndex = index;
    this.visitedQuestions.add(this.questions[index].id);
    this.cdr.detectChanges();
  }

  previous(): void {
    if (this.currentIndex > 0) {
      this.goTo(this.currentIndex - 1);
    }
  }

  next(): void {
    if (this.currentIndex < this.questions.length - 1) {
      this.goTo(this.currentIndex + 1);
    }
  }

  openSummarySimulation(): void {
    this.showSummaryView = true;
    this.cdr.detectChanges();
  }

  backToQuestions(): void {
    this.showSummaryView = false;
    this.cdr.detectChanges();
  }

  resetSimulation(): void {
    this.localAnswers = {};
    this.markedForReview = new Set();
    this.visitedQuestions = new Set(
      this.questions[0] ? [this.questions[0].id] : []
    );
    this.currentIndex = 0;
    this.showSummaryView = false;
    this.cdr.detectChanges();
  }

  close(): void {
    this.closed.emit();
  }
}
