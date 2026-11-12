import {
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { AssessmentOption } from '../../services/assessment';

export interface RenderableQuestion {
  id?: number;
  category?: string;
  difficulty?: string;
  question_type?: string;
  question_text?: string;
  instructions?: string | null;
  options?: AssessmentOption[];
  max_score?: number;
  negative_marks?: number;
  correct_option_id?: string | null;
  correct_option_ids?: string[] | null;
  explanation?: string | null;
}

@Component({
  selector: 'app-question-renderer',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './question-renderer.html',
  styleUrl: './question-renderer.scss',
})
export class QuestionRenderer {
  @Input() question: RenderableQuestion | null = null;
  @Input() questionNumber = 1;
  @Input() totalQuestions = 1;
  @Input() mode: 'exam' | 'student_preview' | 'admin_preview' = 'exam';
  @Input() selectedAnswer = '';
  @Input() disabled = false;
  @Input() showClear = true;

  @Output() answerChange = new EventEmitter<string>();
  @Output() answerClear = new EventEmitter<void>();

  get isAdminPreview(): boolean {
    return this.mode === 'admin_preview';
  }

  get normalizedType(): string {
    return (this.question?.question_type || 'multiple_choice').trim().toLowerCase();
  }

  get isMultiSelect(): boolean {
    return this.normalizedType === 'multiple_select';
  }

  get isTrueFalse(): boolean {
    return this.normalizedType === 'true_false';
  }

  get typeBadgeLabel(): string {
    switch (this.normalizedType) {
      case 'multiple_select':
        return 'Multi-Select';
      case 'true_false':
        return 'True / False';
      case 'single_choice':
      case 'multiple_choice':
        return 'Single-Choice MCQ';
      case 'psychometric':
        return 'Behavioral';
      default:
        return this.normalizedType.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
    }
  }

  get optionsList(): AssessmentOption[] {
    return Array.isArray(this.question?.options) ? this.question!.options : [];
  }

  get helperInstruction(): string {
    const count = this.optionsList.length;
    if (this.isMultiSelect) {
      return 'Select all correct answers from the choices below:';
    }
    if (this.isTrueFalse) {
      return 'Choose whether the statement is True or False:';
    }
    return `Choose the correct answer from the ${count} ${count === 1 ? 'choice' : 'choices'} below:`;
  }

  get selectedTokens(): Set<string> {
    const raw = String(this.selectedAnswer || '').trim();
    if (!raw) return new Set();
    if (this.isMultiSelect) {
      return new Set(
        raw
          .split(',')
          .map(s => s.trim().toUpperCase())
          .filter(Boolean)
      );
    }
    return new Set([raw.toUpperCase()]);
  }

  get hasSelection(): boolean {
    return this.selectedTokens.size > 0;
  }

  get formattedMarks(): string {
    const val = Number(this.question?.max_score ?? 1);
    const clean = Number.isFinite(val) && val > 0 ? val : 1;
    const text = clean % 1 === 0 ? clean.toFixed(1) : String(Number(clean.toFixed(2)));
    return `+${text} ${clean === 1 ? 'Mark' : 'Marks'}`;
  }

  get negativeMarksValue(): number {
    const val = Number(this.question?.negative_marks ?? 0);
    return Number.isFinite(val) && val > 0 ? Number(val.toFixed(2)) : 0;
  }

  get formattedNegativeMarks(): string {
    const neg = this.negativeMarksValue;
    if (neg <= 0) return 'No Negative';
    const text = neg % 1 === 0 ? neg.toFixed(1) : String(neg);
    return `-${text} Negative`;
  }

  get correctAnswerSet(): Set<string> {
    // Strictly block correct answer exposure outside admin preview mode
    if (!this.isAdminPreview || !this.question) {
      return new Set();
    }
    const result = new Set<string>();
    if (Array.isArray(this.question.correct_option_ids)) {
      for (const id of this.question.correct_option_ids) {
        const clean = String(id || '').trim().toUpperCase();
        if (clean) result.add(clean);
      }
    }
    if (result.size === 0 && this.question.correct_option_id) {
      const clean = String(this.question.correct_option_id).trim().toUpperCase();
      if (clean) result.add(clean);
    }
    return result;
  }

  get correctAnswerDisplay(): string {
    return Array.from(this.correctAnswerSet).join(', ');
  }

  categoryLabel(category?: string): string {
    if (!category) return 'General';
    return category
      .replaceAll('_', ' ')
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  isSelected(optionId: string): boolean {
    return this.selectedTokens.has(String(optionId || '').trim().toUpperCase());
  }

  isCorrectOption(optionId: string): boolean {
    if (!this.isAdminPreview) return false;
    return this.correctAnswerSet.has(String(optionId || '').trim().toUpperCase());
  }

  onSelectOption(optionId: string): void {
    if (this.disabled) return;
    const norm = String(optionId || '').trim().toUpperCase();
    if (!norm) return;

    if (this.isMultiSelect) {
      const next = new Set(this.selectedTokens);
      if (next.has(norm)) {
        next.delete(norm);
      } else {
        next.add(norm);
      }
      if (next.size === 0) {
        this.answerClear.emit();
        this.answerChange.emit('');
      } else {
        const orderMap = new Map(
          this.optionsList.map((o, idx) => [String(o.id).trim().toUpperCase(), idx])
        );
        const sorted = Array.from(next).sort((a, b) => {
          const ia = orderMap.get(a) ?? 999;
          const ib = orderMap.get(b) ?? 999;
          return ia !== ib ? ia - ib : a.localeCompare(b);
        });
        this.answerChange.emit(sorted.join(','));
      }
      return;
    }

    this.answerChange.emit(norm);
  }

  onClearClick(): void {
    if (this.disabled) return;
    this.answerClear.emit();
  }
}
