import {
  Component,
  OnInit,
  OnDestroy,
  ChangeDetectorRef,
  inject
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import {
  AssessmentService,
  AssessmentQuestion,
  AssessmentAnswer
} from '../services/assessment';
import { AssessmentStatusService } from '../../../core/services/assessment-status.service';
import { OnboardingService } from '../../../core/services/onboarding.service';
import { QuestionRenderer } from '../components/question-renderer/question-renderer';

@Component({
  selector: 'app-assessment-taking',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, QuestionRenderer],
  templateUrl: './assessment-taking.html',
  styleUrl: './assessment-taking.scss'
})
export class AssessmentTaking implements OnInit, OnDestroy {

  private readonly api = inject(AssessmentService);
  private readonly assessmentStatusService = inject(AssessmentStatusService);
  private readonly onboardingService = inject(OnboardingService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  private timerHandle: ReturnType<typeof setInterval> | null = null;
  private deadlineTimestamp = 0;
  private readonly mountedTimestamp = Date.now();

  sessionId = 0;
  templateId = 0;
  templateName = 'Logical Reasoning Assessment';
  assessmentType = 'logical_reasoning';
  assessmentMode: 'mcq' | 'pdf_submission' = 'mcq';
  hasQuestionPdf = false;
  questionPdfName: string | null = null;
  maxMarks = 100;
  assignedSet = '';
  durationSeconds = 30 * 60; // 30 minutes default
  startedAt = '';
  expiresAt = '';

  // PDF Question Paper + GitHub / ZIP Submission state
  projectGithubUrl = '';
  projectNotes = '';
  projectZipFile: File | null = null;
  downloadingPdf = false;

  questions: AssessmentQuestion[] = [];
  answers: Record<number, string> = {};
  visitedQuestions: Set<number> = new Set();
  markedForReview: Set<number> = new Set();

  currentIndex = 0;

  loading = true;
  submitting = false;
  isExpired = false;
  isAlreadySubmitted = false;
  showSubmitModal = false;
  isMobileNavOpen = false;

  // Proctoring & Tab Switch Warning System (Max 3 Warnings)
  tabSwitchCount = 0;
  readonly maxTabSwitches = 3;
  showTabWarningModal = false;
  isTerminatedDueToViolation = false;
  private lastViolationTimestamp = 0;
  private visibilityListener: (() => void) | null = null;
  private windowBlurListener: (() => void) | null = null;
  private pageshowListener: ((event: PageTransitionEvent) => void) | null = null;
  private popstateListener: (() => void) | null = null;

  remainingSeconds = 1800; // 30:00
  errorMessage = '';

  async ngOnInit(): Promise<void> {
    this.sessionId = Number(this.route.snapshot.paramMap.get('sessionId'));

    if (!this.sessionId || !Number.isFinite(this.sessionId)) {
      this.errorMessage = 'Invalid assessment session.';
      this.loading = false;
      this.cdr.detectChanges();
      return;
    }

    // 1. Fast in-memory check for sessions submitted in current SPA session
    if (this.api.isSessionLocallySubmitted(this.sessionId)) {
      this.isAlreadySubmitted = true;
      this.loading = false;
      this.cdr.detectChanges();
      void this.router.navigate(['/assessments/report', this.sessionId], { replaceUrl: true });
      return;
    }

    // 2. Attach BFCache & popstate listeners to prevent back navigation reopening
    this.attachNavigationListeners();

    // 3. Authoritatively verify with backend before rendering questions
    await this.verifyAndLoadSession();
  }

  ngOnDestroy(): void {
    this.stopTimer();
    this.detachTabSwitchListeners();
    this.detachNavigationListeners();
  }

  private attachNavigationListeners(): void {
    this.detachNavigationListeners();

    this.pageshowListener = (event: PageTransitionEvent) => {
      // Handles browser Back/Forward Cache restorations
      if (event.persisted || this.api.isSessionLocallySubmitted(this.sessionId)) {
        void this.revalidateSession();
      }
    };

    this.popstateListener = () => {
      void this.revalidateSession();
    };

    window.addEventListener('pageshow', this.pageshowListener);
    window.addEventListener('popstate', this.popstateListener);
  }

  private detachNavigationListeners(): void {
    if (this.pageshowListener) {
      window.removeEventListener('pageshow', this.pageshowListener);
      this.pageshowListener = null;
    }
    if (this.popstateListener) {
      window.removeEventListener('popstate', this.popstateListener);
      this.popstateListener = null;
    }
  }

  private async revalidateSession(): Promise<void> {
    if (!this.sessionId) return;
    if (this.api.isSessionLocallySubmitted(this.sessionId)) {
      this.isAlreadySubmitted = true;
      this.loading = false;
      this.stopTimer();
      this.detachTabSwitchListeners();
      this.cdr.detectChanges();
      void this.router.navigate(['/assessments/report', this.sessionId], { replaceUrl: true });
      return;
    }

    try {
      const check = await firstValueFrom(this.api.checkSession(this.sessionId));
      if (check.is_submitted || check.status === 'completed' || check.status === 'submitted') {
        this.api.markSessionSubmitted(this.sessionId);
        this.isAlreadySubmitted = true;
        this.loading = false;
        this.stopTimer();
        this.detachTabSwitchListeners();
        this.cdr.detectChanges();
        const target = check.redirect_url || `/assessments/report/${this.sessionId}`;
        void this.router.navigate([target], { replaceUrl: true });
      }
    } catch {
      // Ignore network errors on passive revalidation
    }
  }

  private async verifyAndLoadSession(): Promise<void> {
    this.loading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    try {
      const check = await firstValueFrom(this.api.checkSession(this.sessionId));

      if (check.is_submitted || check.status === 'completed' || check.status === 'submitted') {
        this.api.markSessionSubmitted(this.sessionId);
        this.isAlreadySubmitted = true;
        this.loading = false;
        this.cdr.detectChanges();
        const target = check.redirect_url || `/assessments/report/${this.sessionId}`;
        void this.router.navigate([target], { replaceUrl: true });
        return;
      }

      if (check.is_expired) {
        this.isExpired = true;
        this.errorMessage = 'This assessment session has expired and cannot be resumed.';
        this.loading = false;
        this.api.notifyStatusChanged();
        this.cdr.detectChanges();
        return;
      }

      const state = history.state as {
        sessionId?: number;
        templateId?: number;
        questions?: AssessmentQuestion[];
        startedAt?: string;
        expiresAt?: string;
        durationMinutes?: number;
        remainingSeconds?: number;
        templateName?: string;
        assessmentType?: string;
        assessmentMode?: 'mcq' | 'pdf_submission' | string;
        hasQuestionPdf?: boolean;
        questionPdfName?: string | null;
        maxMarks?: number;
        assignedSet?: string;
      };

      const isPdfFromState = state?.assessmentMode === 'pdf_submission';

      if (
        state?.sessionId === this.sessionId &&
        state.startedAt &&
        (isPdfFromState || (Array.isArray(state.questions) && state.questions.length > 0))
      ) {
        if (state.templateId) this.templateId = Number(state.templateId);
        if (state.templateName) this.templateName = state.templateName;
        if (state.assessmentType) this.assessmentType = state.assessmentType;
        this.assessmentMode = isPdfFromState ? 'pdf_submission' : 'mcq';
        this.hasQuestionPdf = Boolean(state.hasQuestionPdf);
        this.questionPdfName = state.questionPdfName || null;
        if (state.maxMarks) this.maxMarks = Number(state.maxMarks) || 100;
        if (state.assignedSet) this.assignedSet = state.assignedSet;
        this.initializeAssessment(
          state.questions || [],
          state.startedAt,
          state.expiresAt,
          state.durationMinutes,
          check.remaining_seconds ?? state.remainingSeconds
        );
      } else {
        await this.resumeAssessment();
      }
    } catch (err: any) {
      console.warn('Initial session check error, falling back to resume:', err);
      await this.resumeAssessment();
    }
  }

  // ----------------------------------
  // Resume assessment from server
  // ----------------------------------

  private async resumeAssessment(): Promise<void> {
    this.loading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    try {
      const session = await firstValueFrom(
        this.api.resumeAssessment(this.sessionId)
      );

      if (session.status === 'expired') {
        this.isExpired = true;
        this.errorMessage = 'This assessment session has expired without submission and cannot be resumed.';
        this.loading = false;
        this.api.notifyStatusChanged();
        this.cdr.detectChanges();
        return;
      }

      if (session.status !== 'in_progress') {
        this.isAlreadySubmitted = true;
        this.api.markSessionSubmitted(this.sessionId);
        this.loading = false;
        this.cdr.detectChanges();
        void this.router.navigate(['/assessments/report', this.sessionId], { replaceUrl: true });
        return;
      }

      if (session.template_id) this.templateId = Number(session.template_id);
      if (session.template_name) this.templateName = session.template_name;
      if (session.assessment_type) this.assessmentType = session.assessment_type;
      this.assessmentMode = session.assessment_mode === 'pdf_submission' ? 'pdf_submission' : 'mcq';
      this.hasQuestionPdf = Boolean(session.has_question_pdf);
      this.questionPdfName = session.question_pdf_name || null;
      if (session.max_marks) this.maxMarks = Number(session.max_marks) || 100;
      if (session.assigned_set) this.assignedSet = session.assigned_set;

      if (session.saved_answers) {
        this.answers = { ...session.saved_answers };
      }
      if (Array.isArray(session.marked_for_review)) {
        this.markedForReview = new Set(session.marked_for_review);
      }

      this.initializeAssessment(
        session.questions,
        session.started_at,
        session.expires_at,
        session.duration_minutes,
        session.remaining_seconds
      );

    } catch (error: any) {
      console.error('Assessment resume failed:', error);
      const detail = String(error?.error?.detail || error?.message || '').toLowerCase();
      if (detail.includes('expired')) {
        this.isExpired = true;
        this.errorMessage =
          error?.error?.detail ||
          'This assessment session has expired without submission and is no longer available.';
        this.loading = false;
        this.api.notifyStatusChanged();
        this.cdr.detectChanges();
        return;
      }
      if (
        detail.includes('no longer in progress') ||
        detail.includes('already been submitted') ||
        detail.includes('already submitted')
      ) {
        this.isAlreadySubmitted = true;
        this.api.markSessionSubmitted(this.sessionId);
        this.loading = false;
        this.cdr.detectChanges();
        void this.router.navigate(['/assessments/report', this.sessionId], { replaceUrl: true });
        return;
      }

      this.errorMessage =
        error?.error?.detail ||
        error?.message ||
        'Unable to resume assessment. Please contact your administrator.';
      this.loading = false;
      this.cdr.detectChanges();
    }
  }

  // ----------------------------------
  // Initialize assessment state
  // ----------------------------------

  private initializeAssessment(
    questions: AssessmentQuestion[],
    startedAt: string,
    expiresAt?: string,
    durationMinutes?: number,
    remainingSec?: number
  ): void {
    if (this.assessmentMode !== 'pdf_submission' && !questions.length) {
      this.errorMessage = 'No assessment questions were found.';
      this.loading = false;
      this.cdr.detectChanges();
      return;
    }

    this.questions = questions;
    this.startedAt = startedAt;
    this.expiresAt = expiresAt || '';

    const minutes =
      durationMinutes ||
      ((this.assessmentType === 'logical_reasoning' || this.assessmentType === 'programming') ? 30 : 15);
    this.durationSeconds = minutes * 60;

    if (this.assessmentMode !== 'pdf_submission') {
      // Restore local cache as fallback/supplement
      this.restoreLocalCache();

      // Restore tab switch count from session storage if candidate previously switched
      const cachedViolations = sessionStorage.getItem(`lk_tab_switch_${this.sessionId}`);
      if (cachedViolations) {
        this.tabSwitchCount = Number(cachedViolations) || 0;
      }

      // Attach proctoring listeners for tab switching (MCQ mode only)
      this.attachTabSwitchListeners();

      // Mark current question as visited
      if (this.questions[this.currentIndex]) {
        this.visitedQuestions.add(this.questions[this.currentIndex].id);
      }
    }

    this.loading = false;
    this.startTimer(startedAt, expiresAt, remainingSec);
    this.api.notifyStatusChanged();
    this.cdr.detectChanges();
  }

  // ----------------------------------
  // Proctoring & Tab Switch Management (Max 3 Warnings)
  // ----------------------------------

  private attachTabSwitchListeners(): void {
    this.detachTabSwitchListeners();

    this.visibilityListener = () => {
      if (document.hidden) {
        this.handleTabSwitchViolation('tab_hidden');
      }
    };

    this.windowBlurListener = () => {
      // Trigger if window lost focus and document is not active
      if (!document.hidden) {
        this.handleTabSwitchViolation('window_blur');
      }
    };

    document.addEventListener('visibilitychange', this.visibilityListener);
    window.addEventListener('blur', this.windowBlurListener);
  }

  private detachTabSwitchListeners(): void {
    if (this.visibilityListener) {
      document.removeEventListener('visibilitychange', this.visibilityListener);
      this.visibilityListener = null;
    }
    if (this.windowBlurListener) {
      window.removeEventListener('blur', this.windowBlurListener);
      this.windowBlurListener = null;
    }
  }

  handleTabSwitchViolation(source = 'visibility'): void {
    if (
      this.loading ||
      this.submitting ||
      this.isExpired ||
      this.isAlreadySubmitted ||
      this.isTerminatedDueToViolation ||
      this.questions.length === 0
    ) {
      return;
    }

    const now = Date.now();
    // 2-second debounce to prevent double-firing
    if (now - this.lastViolationTimestamp < 2000) {
      return;
    }
    // Ignore first 2 seconds after page load
    if (now - this.mountedTimestamp < 2000) {
      return;
    }
    this.lastViolationTimestamp = now;

    this.tabSwitchCount++;
    try {
      sessionStorage.setItem(`lk_tab_switch_${this.sessionId}`, String(this.tabSwitchCount));
    } catch {
      // storage unavailable
    }

    // Persist live tab switch violation to server
    this.api.recordTabSwitch(this.sessionId, this.tabSwitchCount).subscribe({
      error: (err) => console.warn('Tab switch recording warning:', err)
    });

    this.showTabWarningModal = true;

    if (this.tabSwitchCount >= this.maxTabSwitches) {
      this.isTerminatedDueToViolation = true;
      this.stopTimer();
      this.detachTabSwitchListeners();

      // Automatically submit after 2.5 seconds to display final terminal warning
      setTimeout(() => {
        void this.submitFinal(true);
      }, 2500);
    }

    this.cdr.detectChanges();
  }

  dismissTabWarningModal(): void {
    if (this.tabSwitchCount < this.maxTabSwitches) {
      this.showTabWarningModal = false;
      this.cdr.detectChanges();
    }
  }

  // ----------------------------------
  // Countdown Timer & Server Date Parser
  // ----------------------------------

  private parseServerDate(dateStr?: string | null): number {
    if (!dateStr || typeof dateStr !== 'string') return 0;
    let s = dateStr.trim();
    if (!s) return 0;
    if (!s.endsWith('Z') && !/[+-]\d{2}(:?\d{2})?$/.test(s)) {
      s += 'Z';
    }
    const ts = new Date(s).getTime();
    return Number.isFinite(ts) ? ts : 0;
  }

  private startTimer(startedAt: string, expiresAt?: string, remainingSec?: number): void {
    this.stopTimer();

    // 1. If server sent a valid remaining_seconds > 0, trust it
    if (typeof remainingSec === 'number' && remainingSec > 0 && remainingSec <= this.durationSeconds) {
      this.remainingSeconds = remainingSec;
      this.deadlineTimestamp = Date.now() + remainingSec * 1000;
    } else {
      // 2. Client-side session storage to persist time accurately across reloads
      const storageKey = `ase_timer_start_${this.sessionId}`;
      const cachedStart = sessionStorage.getItem(storageKey);
      const now = Date.now();

      if (cachedStart) {
        const elapsedSec = Math.floor((now - Number(cachedStart)) / 1000);
        const rem = this.durationSeconds - elapsedSec;
        if (rem > 0 && rem <= this.durationSeconds) {
          this.remainingSeconds = rem;
          this.deadlineTimestamp = now + rem * 1000;
        } else {
          sessionStorage.setItem(storageKey, String(now));
          this.remainingSeconds = this.durationSeconds;
          this.deadlineTimestamp = now + this.durationSeconds * 1000;
        }
      } else {
        sessionStorage.setItem(storageKey, String(now));
        this.remainingSeconds = this.durationSeconds;
        this.deadlineTimestamp = now + this.durationSeconds * 1000;
      }
    }

    this.isExpired = false;

    const updateTimer = (): void => {
      const msRemaining = this.deadlineTimestamp - Date.now();
      const secondsLeft = Math.max(0, Math.floor(msRemaining / 1000));
      this.remainingSeconds = secondsLeft;

      // Only allow auto-submit after at least 10 seconds on page to guard against clock skew
      if (this.remainingSeconds <= 0 && (Date.now() - this.mountedTimestamp >= 10000)) {
        this.remainingSeconds = 0;
        this.isExpired = true;
        this.stopTimer();
        this.cdr.detectChanges();
        // Automatically submit assessment upon expiration
        void this.submitFinal(true);
        return;
      }

      this.cdr.detectChanges();
    };

    updateTimer();

    if (!this.isExpired) {
      this.timerHandle = setInterval(updateTimer, 1000);
    }
  }

  private stopTimer(): void {
    if (this.timerHandle !== null) {
      clearInterval(this.timerHandle);
      this.timerHandle = null;
    }
  }

  get formattedTime(): string {
    const minutes = Math.floor(this.remainingSeconds / 60);
    const seconds = this.remainingSeconds % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }

  get isTimerWarning(): boolean {
    return this.remainingSeconds < 600 && this.remainingSeconds >= 300; // < 10 mins
  }

  get isTimerCritical(): boolean {
    return this.remainingSeconds < 300; // < 5 mins
  }

  // ----------------------------------
  // Local storage helpers
  // ----------------------------------

  private get localKey(): string {
    return `lk-exam-${this.sessionId}`;
  }

  private restoreLocalCache(): void {
    try {
      const raw = sessionStorage.getItem(this.localKey);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (data.answers && typeof data.answers === 'object') {
        for (const [k, v] of Object.entries(data.answers)) {
          if (!this.answers[Number(k)] && typeof v === 'string') {
            this.answers[Number(k)] = v;
          }
        }
      }
      if (Array.isArray(data.reviews)) {
        for (const id of data.reviews) {
          this.markedForReview.add(Number(id));
        }
      }
      if (Array.isArray(data.visited)) {
        for (const id of data.visited) {
          this.visitedQuestions.add(Number(id));
        }
      }
    } catch (e) {
      console.warn('Could not restore local cache:', e);
    }
  }

  private persistLocal(): void {
    try {
      const payload = {
        answers: this.answers,
        reviews: Array.from(this.markedForReview),
        visited: Array.from(this.visitedQuestions),
      };
      sessionStorage.setItem(this.localKey, JSON.stringify(payload));
    } catch (e) {
      console.warn('Could not write local cache:', e);
    }
  }

  // ----------------------------------
  // Question & Navigation State
  // ----------------------------------

  get currentQuestion(): AssessmentQuestion | undefined {
    return this.questions[this.currentIndex];
  }

  get activePassageText(): string | null {
    const raw = (this.currentQuestion?.passage_text || '').trim();
    return raw.length > 0 ? raw : null;
  }

  get activeSetLabel(): string {
    return (this.assignedSet || this.currentQuestion?.question_set || 'A').toUpperCase();
  }

  get totalMaxScore(): number {
    if (!this.questions.length) return 0;
    const total = this.questions.reduce((sum, q) => sum + (Number(q.max_score ?? 1) || 1), 0);
    return Number(total.toFixed(2));
  }

  get answeredCount(): number {
    return this.questions.filter(q => Boolean((this.answers[q.id] || '').trim())).length;
  }

  get unansweredCount(): number {
    return Math.max(0, this.questions.length - this.answeredCount);
  }

  get markedCount(): number {
    return this.markedForReview.size;
  }

  get notAnsweredCount(): number {
    return this.questions.filter((q, i) => this.getQuestionState(q, i) === 'not-answered').length;
  }

  get notVisitedCount(): number {
    return this.questions.filter((q, i) => this.getQuestionState(q, i) === 'not-visited').length;
  }

  get progressPercentage(): number {
    if (!this.questions.length) return 0;
    return Math.round((this.answeredCount / this.questions.length) * 100);
  }

  get isCurrentQuestionMarked(): boolean {
    const q = this.currentQuestion;
    return q ? this.markedForReview.has(q.id) : false;
  }

  getQuestionState(question: AssessmentQuestion, index: number): string {
    const isAnswered = Boolean((this.answers[question.id] || '').trim());
    const isReview = this.markedForReview.has(question.id);
    const isVisited = this.visitedQuestions.has(question.id);

    if (isAnswered && isReview) return 'answered-review';
    if (isReview) return 'review';
    if (isAnswered) return 'answered';
    if (isVisited) return 'not-answered';
    return 'not-visited';
  }

  // ----------------------------------
  // Student Actions
  // ----------------------------------

  chooseAnswer(questionId: number, optionId: string): void {
    if (this.submitting || this.isExpired || this.isTerminatedDueToViolation) return;

    if (!optionId || !optionId.trim()) {
      this.clearAnswer(questionId);
      return;
    }

    this.answers = { ...this.answers, [questionId]: optionId };
    this.visitedQuestions.add(questionId);
    this.persistLocal();

    // Auto-save to backend asynchronously
    this.api.saveAnswer(this.sessionId, {
      question_id: questionId,
      answer: optionId,
      is_marked_for_review: this.markedForReview.has(questionId),
    }).subscribe({
      error: (err) => console.warn('Background auto-save error:', err)
    });

    this.cdr.detectChanges();
  }

  clearAnswer(questionId: number): void {
    if (this.submitting || this.isExpired || this.isTerminatedDueToViolation) return;

    const next = { ...this.answers };
    delete next[questionId];
    this.answers = next;
    this.persistLocal();

    this.api.saveAnswer(this.sessionId, {
      question_id: questionId,
      answer: '',
      is_marked_for_review: this.markedForReview.has(questionId),
    }).subscribe({
      error: (err) => console.warn('Background clear error:', err)
    });

    this.cdr.detectChanges();
  }

  toggleMarkForReview(questionId: number): void {
    if (this.submitting || this.isExpired || this.isTerminatedDueToViolation) return;

    if (this.markedForReview.has(questionId)) {
      this.markedForReview.delete(questionId);
    } else {
      this.markedForReview.add(questionId);
    }

    this.visitedQuestions.add(questionId);
    this.persistLocal();

    this.api.saveAnswer(this.sessionId, {
      question_id: questionId,
      answer: this.answers[questionId] || null,
      is_marked_for_review: this.markedForReview.has(questionId),
    }).subscribe({
      error: (err) => console.warn('Background review toggle error:', err)
    });

    this.cdr.detectChanges();
  }

  previous(): void {
    if (this.currentIndex > 0 && !this.submitting && !this.isTerminatedDueToViolation) {
      this.currentIndex--;
      if (this.questions[this.currentIndex]) {
        this.visitedQuestions.add(this.questions[this.currentIndex].id);
      }
      this.persistLocal();
      this.cdr.detectChanges();
    }
  }

  saveAndNext(): void {
    if (this.currentIndex < this.questions.length - 1 && !this.submitting && !this.isTerminatedDueToViolation) {
      this.currentIndex++;
      if (this.questions[this.currentIndex]) {
        this.visitedQuestions.add(this.questions[this.currentIndex].id);
      }
      this.persistLocal();
      this.cdr.detectChanges();
    }
  }

  goTo(index: number): void {
    if (index >= 0 && index < this.questions.length && !this.submitting && !this.isTerminatedDueToViolation) {
      this.currentIndex = index;
      if (this.questions[index]) {
        this.visitedQuestions.add(this.questions[index].id);
      }
      this.persistLocal();
      this.isMobileNavOpen = false;
      this.cdr.detectChanges();
    }
  }

  toggleMobileNav(): void {
    this.isMobileNavOpen = !this.isMobileNavOpen;
    this.cdr.detectChanges();
  }

  categoryLabel(category: string): string {
    return category
      .replaceAll('_', ' ')
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  // ----------------------------------
  // Submission Modal & Finalization
  // ----------------------------------

  openSubmitModal(): void {
    if (this.isTerminatedDueToViolation) return;
    this.showSubmitModal = true;
    this.cdr.detectChanges();
  }

  closeSubmitModal(): void {
    this.showSubmitModal = false;
    this.cdr.detectChanges();
  }

  onProjectFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.projectZipFile = input.files?.[0] || null;
    this.cdr.detectChanges();
  }

  async downloadQuestionPaper(): Promise<void> {
    if (!this.templateId || this.downloadingPdf) return;
    this.downloadingPdf = true;
    this.errorMessage = '';
    this.cdr.detectChanges();
    try {
      const blob = await firstValueFrom(this.api.downloadQuestionPdf(this.templateId));
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = this.questionPdfName || `${this.templateName.replace(/\s+/g, '_')}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      this.errorMessage = err?.error?.detail || 'Unable to download question paper PDF.';
    } finally {
      this.downloadingPdf = false;
      this.cdr.detectChanges();
    }
  }

  async submitProjectFinal(): Promise<void> {
    if (this.submitting) return;
    const cleanUrl = this.projectGithubUrl.trim();
    if (!cleanUrl && !this.projectZipFile) {
      this.errorMessage = 'Please provide a GitHub repository URL or upload a .zip / project file before submitting.';
      this.cdr.detectChanges();
      return;
    }

    this.submitting = true;
    this.errorMessage = '';
    this.stopTimer();
    this.cdr.detectChanges();

    const formData = new FormData();
    formData.append('github_url', cleanUrl);
    formData.append('notes', this.projectNotes.trim());
    if (this.projectZipFile) {
      formData.append('file', this.projectZipFile);
    }

    try {
      await firstValueFrom(this.api.submitProjectAssessment(this.sessionId, formData));
      try {
        sessionStorage.removeItem(`ase_timer_start_${this.sessionId}`);
      } catch { }
    } catch (error: any) {
      this.submitting = false;
      if (!this.isExpired && this.startedAt) {
        this.startTimer(this.startedAt, this.expiresAt);
      }
      this.errorMessage = error?.error?.detail || 'Unable to submit project assessment. Please try again.';
      this.cdr.detectChanges();
      return;
    }

    try {
      const statusRes = await this.assessmentStatusService.getStatus(true);
      if (statusRes.status === 'completed' || statusRes.all_completed === true) {
        try {
          await this.onboardingService.completeAssessments();
        } catch { }
      }
      const perms = await this.onboardingService.getPermissions(true);
      this.submitting = false;
      this.cdr.detectChanges();

      if (!statusRes.all_completed) {
        await this.router.navigate(['/my-assessments']);
      } else if (perms.can_select_department && !perms.department_approved) {
        await this.router.navigate(['/department-selection']);
      } else {
        await this.router.navigate(['/my-results']);
      }
    } catch {
      this.submitting = false;
      this.cdr.detectChanges();
      await this.router.navigate(['/my-assessments']);
    }
  }

  async submitFinal(automatic = false): Promise<void> {
    if (this.assessmentMode === 'pdf_submission') {
      if (automatic && !this.projectGithubUrl.trim() && !this.projectZipFile) {
        this.errorMessage = 'Time limit reached. Please attach your GitHub link or ZIP file and submit immediately.';
        this.cdr.detectChanges();
        return;
      }
      await this.submitProjectFinal();
      return;
    }
    if (this.submitting) return;

    this.submitting = true;
    this.showSubmitModal = false;
    this.stopTimer();
    this.detachTabSwitchListeners();

    if (this.isTerminatedDueToViolation) {
      this.errorMessage = 'Maximum tab switches reached (3/3). Submitting examination due to security violation...';
    } else if (automatic) {
      this.errorMessage = 'Time is up! Submitting your examination answers...';
    } else {
      this.errorMessage = '';
    }
    this.cdr.detectChanges();

    const payload: AssessmentAnswer[] = this.questions
      .filter(question => Boolean((this.answers[question.id] || '').trim()))
      .map(question => ({
        question_id: question.id,
        answer: this.answers[question.id],
      }));

    try {
      const response = await firstValueFrom(
        this.api.submitAssessment(this.sessionId, payload, this.tabSwitchCount)
      );

      if (response.status !== 'completed') {
        throw new Error('The server did not confirm assessment completion.');
      }

      this.api.markSessionSubmitted(this.sessionId);

      try {
        history.replaceState(null, '', window.location.href);
      } catch {
        // ignore
      }

      try {
        sessionStorage.removeItem(this.localKey);
        sessionStorage.removeItem(`lk_tab_switch_${this.sessionId}`);
        sessionStorage.removeItem(`ase_timer_start_${this.sessionId}`);
      } catch {
        // clean up local cache
      }

    } catch (error: any) {
      console.error('Assessment submission failed:', error);
      const detail = String(error?.error?.detail || error?.message || '').toLowerCase();
      if (
        detail.includes('already submitted') ||
        detail.includes('already been submitted') ||
        detail.includes('no longer in progress')
      ) {
        this.api.markSessionSubmitted(this.sessionId);
        this.isAlreadySubmitted = true;
        this.submitting = false;
        this.cdr.detectChanges();
        await this.router.navigate(['/assessments/report', this.sessionId], { replaceUrl: true });
        return;
      }

      this.submitting = false;

      if (!this.isExpired && !this.isTerminatedDueToViolation && this.startedAt) {
        this.startTimer(this.startedAt, this.expiresAt);
        this.attachTabSwitchListeners();
      }

      this.errorMessage =
        error?.error?.detail ||
        error?.message ||
        'Unable to submit assessment. Please try again.';
      this.cdr.detectChanges();
      return;
    }

    // Step 2: Generate official report card (best-effort) & enforce completion flow
    try {
      await firstValueFrom(this.api.generateReport(this.sessionId));
    } catch {
      // Report generation failure must not block post-submission navigation
    }

    try {
      const statusRes = await this.assessmentStatusService.getStatus(true);
      const allDone =
        statusRes.status === 'completed' || statusRes.all_completed === true;

      if (allDone) {
        try {
          await this.onboardingService.completeAssessments();
        } catch {
          // Backend submit_assessment already syncs completion when eligible
        }
      }

      const perms = await this.onboardingService.getPermissions(true);
      this.submitting = false;
      this.cdr.detectChanges();

      if (!allDone) {
        await this.router.navigate(['/my-assessments'], { replaceUrl: true });
        return;
      }

      if (perms.is_unlocked || statusRes.has_approved_department) {
        await this.router.navigate(['/assessments/report', this.sessionId], { replaceUrl: true });
      } else if (perms.can_select_department) {
        await this.router.navigate(['/department-selection'], { replaceUrl: true });
      } else {
        await this.router.navigate(['/assessments/results', this.sessionId], { replaceUrl: true });
      }
    } catch {
      this.submitting = false;
      this.cdr.detectChanges();
      await this.router.navigate(['/my-assessments'], { replaceUrl: true });
    }
  }
}
