
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
  selector: 'app-assessment-management',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './assessment-management.html',
  styleUrl: './assessment-management.scss'
})
export class AssessmentManagement implements OnInit {

  private readonly assessmentService = inject(AssessmentService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  templates: AssessmentTemplate[] = [];

  loading = false;
  errorMessage = '';

  ngOnInit(): void {
    this.loadTemplates();
  }

  loadTemplates(): void {

    this.loading = true;
    this.errorMessage = '';

    this.cdr.detectChanges();

    this.assessmentService.getTemplates().subscribe({

      next: (data) => {

        console.log('Assessment templates:', data);

        if (!Array.isArray(data)) {
          this.templates = [];
          this.errorMessage =
            'Invalid assessment data received from server.';
        } else {
          this.templates = data;
        }

        this.loading = false;

        this.cdr.detectChanges();
      },

      error: (error) => {

        console.error('Template loading failed:', error);

        this.errorMessage =
          error.error?.detail ||
          'Unable to load assessment templates.';

        this.loading = false;

        this.cdr.detectChanges();
      }

    });

  }

  createAssessment(): void {
    void this.router.navigate(['/assessments/create']);
  }

  editAssessment(id: number): void {
    void this.router.navigate(['/assessments/edit', id]);
  }

  toggleStatus(template: AssessmentTemplate): void {

    this.errorMessage = '';

    this.assessmentService.updateTemplate(template.id, {
      is_active: !template.is_active
    }).subscribe({

      next: () => {
        this.loadTemplates();
        this.cdr.detectChanges();
      },

      error: (error) => {

        console.error('Status update failed:', error);

        this.errorMessage =
          error.error?.detail ||
          'Unable to update assessment status.';

        this.cdr.detectChanges();
      }

    });

  }

  get activeCount(): number {
    return this.templates.filter(t => t.is_active).length;
  }

  get totalQuestions(): number {
    return this.templates.reduce(
      (total, t) => total + t.question_count,
      0
    );
  }

}
