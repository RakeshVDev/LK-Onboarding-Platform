
import {
  Component,
  OnInit,
  ChangeDetectorRef,
  inject,
  signal
} from '@angular/core';

import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';

import {
  AssessmentService,
  AssessmentTemplate
} from '../services/assessment';
import { AssessmentPreviewModal } from '../components/assessment-preview-modal/assessment-preview-modal';

@Component({
  selector: 'app-assessment-management',
  standalone: true,
  imports: [CommonModule, RouterModule, AssessmentPreviewModal],
  templateUrl: './assessment-management.html',
  styleUrl: './assessment-management.scss'
})
export class AssessmentManagement implements OnInit {

  private readonly assessmentService = inject(AssessmentService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  templates: AssessmentTemplate[] = [];
  previewTemplateId: number | null = null;
  isPreviewOpen = false;

  readonly loading = signal(false);
  readonly errorMessage = signal('');

  ngOnInit(): void {
    this.loadTemplates();
  }

  loadTemplates(): void {
    this.loading.set(true);
    this.errorMessage.set('');

    this.assessmentService.getTemplates().subscribe({
      next: (data) => {
        if (!Array.isArray(data)) {
          this.templates = [];
          this.errorMessage.set('Invalid assessment data received from server.');
        } else {
          this.templates = data;
        }

        this.loading.set(false);
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Template loading failed:', error);
        this.errorMessage.set(
          error.error?.detail ||
          'Unable to load assessment templates.'
        );
        this.loading.set(false);
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

  manageQuestions(id: number): void {
    void this.router.navigate(['/assessments/edit', id], {
      queryParams: { tab: 'questions' }
    });
  }

  previewAssessment(id: number): void {
    this.previewTemplateId = id;
    this.isPreviewOpen = true;
    this.cdr.detectChanges();
  }

  closePreview(): void {
    this.isPreviewOpen = false;
    this.previewTemplateId = null;
    this.cdr.detectChanges();
  }

  getTypeLabel(type?: string): string {
    switch (type) {
      case 'logical_reasoning': return 'Logical Reasoning';
      case 'english_grammar': return 'English Grammar';
      case 'technical': return 'Technical Skills';
      case 'programming': return 'Programming & Coding';
      case 'psychometric': return 'Psychometric Profile';
      default: return 'General Assessment';
    }
  }

  getTypeIcon(type?: string): string {
    switch (type) {
      case 'logical_reasoning': return '⚡';
      case 'english_grammar': return '✍';
      case 'technical': return '💻';
      case 'programming': return '⌘';
      case 'psychometric': return '✦';
      default: return '▤';
    }
  }

  getDurationMinutes(template: AssessmentTemplate): number {
    if (template.duration_minutes && template.duration_minutes > 0) {
      return template.duration_minutes;
    }
    return (template.assessment_type === 'logical_reasoning' || template.assessment_type === 'programming') ? 30 : 15;
  }

  toggleStatus(template: AssessmentTemplate): void {

    this.errorMessage.set('');

    this.assessmentService.updateTemplate(template.id, {
      is_active: !template.is_active
    }).subscribe({

      next: () => {
        this.loadTemplates();
        this.cdr.detectChanges();
      },

      error: (error) => {

        console.error('Status update failed:', error);

        this.errorMessage.set(
          error.error?.detail ||
          'Unable to update assessment status.'
        );

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
