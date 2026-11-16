import { describe, expect, it, vi } from 'vitest';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { QuestionRenderer, RenderableQuestion } from './question-renderer';

describe('QuestionRenderer (Free-Response & MCQ)', () => {
  async function createFixture(): Promise<{
    fixture: ComponentFixture<QuestionRenderer>;
    component: QuestionRenderer;
  }> {
    await TestBed.configureTestingModule({
      imports: [QuestionRenderer],
      providers: [provideZonelessChangeDetection()],
    }).compileComponents();

    const fixture = TestBed.createComponent(QuestionRenderer);
    return { fixture, component: fixture.componentInstance };
  }

  it('renders Python code sandbox for code_submission with debounced input and blur flush', async () => {
    vi.useFakeTimers();
    try {
      const { fixture, component } = await createFixture();
      const question: RenderableQuestion = {
        id: 101,
        category: 'algorithms',
        difficulty: 'Medium',
        question_type: 'code_submission',
        question_text: 'Implement two_sum(nums, target) returning index pairs.',
        max_score: 5,
      };

      const emitted: string[] = [];
      component.answerChange.subscribe((val) => emitted.push(val));

      fixture.componentRef.setInput('question', question);
      fixture.componentRef.setInput('mode', 'exam');
      fixture.detectChanges();
      await fixture.whenStable();

      const textarea = fixture.nativeElement.querySelector('textarea.fr-input') as HTMLTextAreaElement;
      expect(textarea).toBeTruthy();
      expect(textarea.classList.contains('fr-code-input')).toBe(true);
      expect(fixture.nativeElement.querySelector('.fr-mode-tag')?.textContent).toContain('Python Code Sandbox');

      // Typing should debounce emission for 300ms
      textarea.value = 'def two_sum(a, t):\n    return [0, 1]';
      textarea.dispatchEvent(new Event('input'));
      fixture.detectChanges();

      expect(emitted).toEqual([]);
      expect(fixture.nativeElement.querySelector('.fr-metrics')?.textContent).toContain('2 lines');

      vi.advanceTimersByTime(300);
      expect(emitted).toEqual(['def two_sum(a, t):\n    return [0, 1]']);

      // Blur flushes immediately before timer expires
      textarea.value = 'def two_sum(a, t):\n    return [1, 2]';
      textarea.dispatchEvent(new Event('input'));
      textarea.dispatchEvent(new Event('blur'));
      fixture.detectChanges();

      expect(emitted).toEqual([
        'def two_sum(a, t):\n    return [0, 1]',
        'def two_sum(a, t):\n    return [1, 2]',
      ]);
    } finally {
      vi.useRealTimers();
    }
  });

  it('renders composition prose editor, word counter, clear action, and admin preview note', async () => {
    const { fixture, component } = await createFixture();
    const clearedSpy = vi.fn();
    component.answerClear.subscribe(clearedSpy);

    fixture.componentRef.setInput('question', {
      id: 202,
      category: 'written_communication',
      question_type: 'composition',
      question_text: 'Summarize your technical handoff plan for a production incident.',
      explanation: 'Clear summary, timeline, and mitigation next steps.',
    });
    fixture.componentRef.setInput('mode', 'admin_preview');
    fixture.componentRef.setInput('selectedAnswer', 'Incident mitigated after rollback.');
    fixture.detectChanges();
    await fixture.whenStable();

    expect(fixture.nativeElement.querySelector('.fr-mode-tag')?.textContent).toContain('Structured Text Response');
    expect(fixture.nativeElement.querySelector('.fr-metrics')?.textContent).toContain('4 words');
    expect(fixture.nativeElement.querySelector('.admin-solution-panel')?.textContent).toContain(
      'Local TF-IDF'
    );

    const clearBtn = fixture.nativeElement.querySelector('.btn-clear') as HTMLButtonElement;
    expect(clearBtn).toBeTruthy();
    clearBtn.click();
    fixture.detectChanges();

    expect(clearedSpy).toHaveBeenCalledTimes(1);
    expect(component.openTextDraft).toBe('');
  });

  it('preserves MCQ option rendering and hides admin answer keys in exam mode', async () => {
    const { fixture, component } = await createFixture();
    const emitted: string[] = [];
    component.answerChange.subscribe((val) => emitted.push(val));

    fixture.componentRef.setInput('question', {
      id: 303,
      category: 'cognitive_reasoning',
      question_type: 'multiple_choice',
      question_text: 'Which structure guarantees O(1) average lookup?',
      correct_option_id: 'B',
      options: [
        { id: 'A', text: 'Linked List' },
        { id: 'B', text: 'Hash Map' },
      ],
    });
    fixture.componentRef.setInput('mode', 'exam');
    fixture.detectChanges();
    await fixture.whenStable();

    expect(fixture.nativeElement.querySelector('.admin-solution-panel')).toBeNull();
    const cards = fixture.nativeElement.querySelectorAll('.option-card') as NodeListOf<HTMLButtonElement>;
    expect(cards.length).toBe(2);
    cards[1].click();
    fixture.detectChanges();

    expect(emitted).toEqual(['B']);
  });
});

