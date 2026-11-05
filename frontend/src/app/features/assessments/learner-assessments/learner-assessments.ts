
import {
  Component,
  OnInit,
  ChangeDetectorRef,
  inject
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';

import {
  AssessmentService,
  AssessmentTemplate
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
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  templates: AssessmentTemplate[] = [];

  loading = true;
  startingId: number | null = null;

  errorMessage = '';

  selectedInstructionTemplate: AssessmentTemplate | null = null;
  showConfirmStartDialog = false;

  ngOnInit(): void {
    this.loadAssessments();
  }

  openInstructions(template: AssessmentTemplate): void {
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

    this.api.getTemplates().subscribe({

      next: (data) => {

        console.log('Assessment templates response:', data);

        if (!Array.isArray(data)) {
          this.templates = [];
          this.errorMessage =
            'Invalid assessment response received from server.';
        } else {
          this.templates = data.filter(
            item => item.is_active
          );
        }

        this.loading = false;

        // Required for reliable updates in zoneless Angular.
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

    this.startingId = template.id;
    this.errorMessage = '';

    this.api.startAssessment(template.id).subscribe({

      next: (session) => {

        this.startingId = null;

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

        const detail = error.error?.detail || '';
        const match = /Session ID:\s*(\d+)/i.exec(detail);
        if (match && match[1]) {
          void this.router.navigate(['/assessments/take', match[1]]);
          return;
        }

        this.errorMessage =
          detail ||
          'Unable to start assessment. Please try again.';

        this.cdr.detectChanges();
      }

    });

  }

}
