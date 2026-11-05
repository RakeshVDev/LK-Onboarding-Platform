import {
  Component,
  OnInit,
  ChangeDetectorRef,
  inject
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { forkJoin } from 'rxjs';

import {
  AssessmentService,
  AssessmentTemplate,
  UserAssessmentResultItem
} from '../services/assessment';

@Component({
  selector: 'app-learner-assessments',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './learner-assessments.html',
  styleUrl: './learner-assessments.scss'
})
export class LearnerAssessments implements OnInit {

  private readonly api = inject(AssessmentService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  templates: AssessmentTemplate[] = [];
  myResults: UserAssessmentResultItem[] = [];

  loading = true;
  startingId: number | null = null;

  errorMessage = '';

  selectedInstructionTemplate: AssessmentTemplate | null = null;
  showConfirmStartDialog = false;

  ngOnInit(): void {
    this.loadAssessments();
  }

  getCompletedResult(template: AssessmentTemplate): UserAssessmentResultItem | undefined {
    return this.myResults.find(
      r => (r.template_id === template.id || r.assessment_type === template.assessment_type) && r.status === 'completed'
    );
  }

  getInProgressResult(template: AssessmentTemplate): UserAssessmentResultItem | undefined {
    return this.myResults.find(
      r => (r.template_id === template.id || r.assessment_type === template.assessment_type) && r.status === 'in_progress'
    );
  }

  openInstructions(template: AssessmentTemplate): void {
    // If already completed, don't allow opening instructions to start
    if (this.getCompletedResult(template)) return;

    this.selectedInstructionTemplate = template;
    this.showConfirmStartDialog = false;
    this.cdr.detectChanges();
  }

  closeInstructions(): void {
    this.selectedInstructionTemplate = null;
    this.showConfirmStartDialog = false;
    this.cdr.detectChanges();
  }

  requestStart(): void {
    this.showConfirmStartDialog = true;
    this.cdr.detectChanges();
  }

  cancelStart(): void {
    this.showConfirmStartDialog = false;
    this.cdr.detectChanges();
  }

  confirmAndStart(): void {
    if (!this.selectedInstructionTemplate) return;
    const template = this.selectedInstructionTemplate;
    this.showConfirmStartDialog = false;
    this.startAssessment(template);
  }

  getDurationMinutes(template: AssessmentTemplate): number {
    return template.assessment_type === 'logical_reasoning' ? 30 : 15;
  }

  loadAssessments(): void {
    this.loading = true;
    this.errorMessage = '';

    forkJoin({
      templates: this.api.getTemplates(),
      results: this.api.getMyResults()
    }).subscribe({
      next: ({ templates, results }) => {
        if (!Array.isArray(templates)) {
          this.templates = [];
          this.errorMessage = 'Invalid assessment response received from server.';
        } else {
          this.templates = templates.filter(item => item.is_active);
          this.myResults = Array.isArray(results) ? results : [];

          // Check if user came with query params like ?start=logical_reasoning
          const startType = this.route.snapshot.queryParamMap.get('start') || this.route.snapshot.queryParamMap.get('type');
          if (startType) {
            const matched = this.templates.find(
              t => t.assessment_type === startType || t.name.toLowerCase().includes(startType.toLowerCase())
            );
            if (matched && !this.getCompletedResult(matched)) {
              this.openInstructions(matched);
            }
          }
        }

        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Assessment loading error:', error);
        this.errorMessage =
          error.error?.detail ||
          'Unable to load assessments. Please try again.';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  startAssessment(template: AssessmentTemplate): void {
    // Client-side guard
    if (this.getCompletedResult(template)) {
      this.errorMessage = `You have already completed the ${template.name}. Only one attempt is permitted.`;
      this.cdr.detectChanges();
      return;
    }

    this.startingId = template.id;
    this.errorMessage = '';

    this.api.startAssessment(template.id, false).subscribe({
      next: (session) => {
        this.startingId = null;
        this.selectedInstructionTemplate = null;
        this.showConfirmStartDialog = false;
        this.cdr.detectChanges();

        void this.router.navigate(
          ['/assessments/take', session.session_id],
          {
            state: {
              sessionId: session.session_id,
              questions: session.questions,
              startedAt: session.started_at,
              expiresAt: session.expires_at,
              durationMinutes: session.duration_minutes || this.getDurationMinutes(template),
              remainingSeconds: session.remaining_seconds,
              templateName: session.template_name || template.name,
              assessmentType: session.assessment_type || template.assessment_type,
            }
          }
        );
      },
      error: (error) => {
        console.error('Assessment start error:', error);
        this.startingId = null;
        this.selectedInstructionTemplate = null;
        this.showConfirmStartDialog = false;

        const detail = error.error?.detail || '';
        this.errorMessage = detail || 'Unable to start assessment. Please try again.';
        this.cdr.detectChanges();
      }
    });
  }
}
