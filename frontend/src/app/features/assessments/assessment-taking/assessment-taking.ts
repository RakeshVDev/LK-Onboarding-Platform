
import {
  Component,
  OnInit,
  OnDestroy,
  ChangeDetectorRef,
  inject
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import {
  AssessmentService,
  AssessmentQuestion,
  AssessmentAnswer
} from '../services/assessment';

@Component({
  selector: 'app-assessment-taking',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './assessment-taking.html',
  styleUrl: './assessment-taking.scss'
})
export class AssessmentTaking implements OnInit, OnDestroy {

  private readonly api = inject(AssessmentService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  private timerHandle: ReturnType<typeof setInterval> | null = null;

  private readonly durationSeconds = 15 * 60;

  sessionId = 0;

  questions: AssessmentQuestion[] = [];

  answers: Record<number, string> = {};

  currentIndex = 0;

  loading = true;
  submitting = false;
  isExpired = false;

  remainingSeconds = 900;

  errorMessage = '';

  ngOnInit(): void {

    this.sessionId = Number(
      this.route.snapshot.paramMap.get('sessionId')
    );

    if (!this.sessionId || !Number.isFinite(this.sessionId)) {
      this.errorMessage = 'Invalid assessment session.';
      this.loading = false;
      return;
    }

    const state = history.state as {
      sessionId?: number;
      questions?: AssessmentQuestion[];
      startedAt?: string;
    };

    // Use navigation state when available.
    // Otherwise, recover the session from the backend after refresh.
    if (
      state?.sessionId === this.sessionId &&
      Array.isArray(state.questions) &&
      state.questions.length > 0 &&
      state.startedAt
    ) {
      this.initializeAssessment(
        state.questions,
        state.startedAt
      );
    } else {
      this.resumeAssessment();
    }

    this.cdr.detectChanges();
  }

  ngOnDestroy(): void {
    this.stopTimer();
  }

  // ----------------------------------
  // Resume assessment after refresh
  // ----------------------------------

  private async resumeAssessment(): Promise<void> {

    this.loading = true;
    this.errorMessage = '';

    try {

      const session = await firstValueFrom(
        this.api.resumeAssessment(this.sessionId)
      );

      if (session.status !== 'in_progress') {
        throw new Error('This assessment is no longer in progress.');
      }

      this.initializeAssessment(
        session.questions,
        session.started_at
      );

    } catch (error: any) {

      console.error('Assessment resume failed:', error);

      this.errorMessage =
        error?.error?.detail ||
        error?.message ||
        'Unable to resume assessment. Please contact your administrator.';

      this.loading = false;
      this.cdr.detectChanges();
    }
  }

  // ----------------------------------
  // Initialize assessment
  // ----------------------------------

  private initializeAssessment(
    questions: AssessmentQuestion[],
    startedAt: string
  ): void {

    if (!questions.length) {
      this.errorMessage = 'No assessment questions were found.';
      this.loading = false;
      this.cdr.detectChanges();
      return;
    }

    this.questions = questions;
    this.loading = false;

    this.startTimer(startedAt);

    this.cdr.detectChanges();
  }

  // ----------------------------------
  // Countdown timer
  // ----------------------------------

  private startTimer(startedAt: string): void {

    this.stopTimer();

    const startTimestamp = new Date(startedAt).getTime();

    if (!Number.isFinite(startTimestamp)) {
      this.errorMessage = 'Invalid assessment start time received from server.';
      this.cdr.detectChanges();
      return;
    }

    const deadline =
      startTimestamp + this.durationSeconds * 1000;

    const updateTimer = (): void => {

      const millisecondsRemaining =
        deadline - Date.now();

      this.remainingSeconds = Math.max(
        0,
        Math.ceil(millisecondsRemaining / 1000)
      );

      if (this.remainingSeconds <= 0) {

        this.remainingSeconds = 0;
        this.isExpired = true;

        this.stopTimer();

        this.cdr.detectChanges();

        // Automatically submit partial or empty answers.
        void this.submit(true);

        return;
      }

      this.cdr.detectChanges();
    };

    // Calculate immediately, then update every second.
    updateTimer();

    if (!this.isExpired) {
      this.timerHandle = setInterval(
        updateTimer,
        1000
      );
    }
  }

  private stopTimer(): void {

    if (this.timerHandle !== null) {
      clearInterval(this.timerHandle);
      this.timerHandle = null;
    }
  }

  get formattedTime(): string {

    const minutes = Math.floor(
      this.remainingSeconds / 60
    );

    const seconds = this.remainingSeconds % 60;

    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }

  // ----------------------------------
  // Question navigation
  // ----------------------------------

  get currentQuestion(): AssessmentQuestion | undefined {
    return this.questions[this.currentIndex];
  }

  get answeredCount(): number {
    return Object.keys(this.answers).length;
  }

  get progress(): number {

    if (!this.questions.length) return 0;

    return (
      this.answeredCount / this.questions.length
    ) * 100;
  }

  chooseAnswer(
    questionId: number,
    optionId: string
  ): void {

    if (this.submitting || this.isExpired) return;

    this.answers[questionId] = optionId;

    this.cdr.detectChanges();
  }

  previous(): void {

    if (
      this.currentIndex > 0 &&
      !this.submitting
    ) {
      this.currentIndex--;
      this.cdr.detectChanges();
    }
  }

  next(): void {

    if (
      this.currentIndex < this.questions.length - 1 &&
      !this.submitting
    ) {
      this.currentIndex++;
      this.cdr.detectChanges();
    }
  }

  goTo(index: number): void {

    if (
      index >= 0 &&
      index < this.questions.length &&
      !this.submitting
    ) {
      this.currentIndex = index;
      this.cdr.detectChanges();
    }
  }

  categoryLabel(category: string): string {

    return category
      .replaceAll('_', ' ')
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  // ----------------------------------
  // Submit assessment
  // ----------------------------------

  async submit(automatic = false): Promise<void> {

    if (this.submitting) return;

    if (!this.questions.length) {
      this.errorMessage = 'Assessment questions are unavailable.';
      this.cdr.detectChanges();
      return;
    }

    if (!automatic && this.isExpired) {
      return;
    }

    if (
      !automatic &&
      this.answeredCount !== this.questions.length
    ) {

      this.errorMessage =
        `Please answer all questions. ${
          this.questions.length - this.answeredCount
        } questions remaining.`;

      this.cdr.detectChanges();
      return;
    }

    if (
      !automatic &&
      !window.confirm(
        'Are you sure you want to submit your assessment? You cannot change your answers afterwards.'
      )
    ) {
      return;
    }

    // Submit only answered questions.
    // Empty and partial submissions are allowed after timeout.
    const payload: AssessmentAnswer[] =
      this.questions
        .filter(question => !!this.answers[question.id])
        .map(question => ({
          question_id: question.id,
          answer: this.answers[question.id]
        }));

    this.submitting = true;
    this.stopTimer();

    this.errorMessage = automatic
      ? 'Time is up. Submitting your assessment...'
      : '';

    this.cdr.detectChanges();

    // Step 1: Submit and save scores.
    try {

      const response = await firstValueFrom(
        this.api.submitAssessment(
          this.sessionId,
          payload
        )
      );

      if (response.status !== 'completed') {
        throw new Error(
          'The server did not confirm assessment completion.'
        );
      }

    } catch (error: any) {

      console.error('Assessment submission failed:', error);

      this.submitting = false;

      this.errorMessage =
        error?.error?.detail ||
        error?.message ||
        'Unable to submit assessment. Please try again.';

      this.cdr.detectChanges();
      return;
    }

    // Step 2: Generate the report.
    try {

      await firstValueFrom(
        this.api.generateReport(this.sessionId)
      );

      this.submitting = false;
      this.cdr.detectChanges();

      await this.router.navigate([
        '/assessments/report',
        this.sessionId
      ]);

    } catch (error) {

      console.error('Report generation failed:', error);

      // Assessment is already completed.
      // Never submit it again.
      this.submitting = false;

      this.cdr.detectChanges();

      await this.router.navigate(
        ['/assessments/results', this.sessionId],
        {
          state: {
            reportGenerationFailed: true
          }
        }
      );
    }
  }
}
