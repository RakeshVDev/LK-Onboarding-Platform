import {
  ChangeDetectorRef,
  Component,
  OnInit,
  inject
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import {
  AssessmentService,
  AssessmentTemplate,
  UserAssessmentResultItem,
  AdminAssessmentResultsResponse
} from '../services/assessment';

@Component({
  selector: 'app-admin-results',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './admin-results.html',
  styleUrl: './admin-results.scss'
})
export class AdminResults implements OnInit {
  private readonly api = inject(AssessmentService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  results: UserAssessmentResultItem[] = [];
  templates: AssessmentTemplate[] = [];

  loading = true;
  errorMessage = '';

  // Filter state
  searchQuery = '';
  selectedTemplateId: number | null = null;
  selectedStatus = 'all';

  // Summary stats
  totalAssessments = 0;
  completedCount = 0;
  averageScore = 0;
  uniqueLearners = 0;

  ngOnInit(): void {
    this.loadTemplates();
    this.loadResults();
  }

  loadTemplates(): void {
    this.api.getTemplates().subscribe({
      next: (data) => {
        this.templates = Array.isArray(data) ? data : [];
        this.cdr.detectChanges();
      },
      error: (err) => console.warn('Could not load templates for filter:', err)
    });
  }

  loadResults(): void {
    this.loading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    const params: {
      template_id?: number;
      status?: string;
      search?: string;
    } = {};

    if (this.selectedTemplateId) {
      params.template_id = this.selectedTemplateId;
    }
    if (this.selectedStatus && this.selectedStatus !== 'all') {
      params.status = this.selectedStatus;
    }
    if (this.searchQuery.trim()) {
      params.search = this.searchQuery.trim();
    }

    this.api.getAdminResults(params).subscribe({
      next: (data: AdminAssessmentResultsResponse) => {
        this.results = data.results || [];
        this.totalAssessments = data.total_assessments;
        this.completedCount = data.completed_count;
        this.averageScore = data.average_score;
        this.uniqueLearners = data.unique_learners;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage =
          error.error?.detail || 'Unable to load learner assessment results.';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  onFilterChange(): void {
    this.loadResults();
  }

  clearFilters(): void {
    this.searchQuery = '';
    this.selectedTemplateId = null;
    this.selectedStatus = 'all';
    this.loadResults();
  }

  viewReport(sessionId: number): void {
    void this.router.navigate(['/assessments/report', sessionId]);
  }

  viewScores(sessionId: number): void {
    void this.router.navigate(['/assessments/results', sessionId]);
  }

  typeLabel(type: string): string {
    switch (type) {
      case 'psychometric': return 'Psychometric';
      case 'technical': return 'Technical';
      case 'english_grammar': return 'English Grammar';
      default: return type.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
    }
  }

  getUserInitials(name?: string): string {
    if (!name) return 'U';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return parts[0].substring(0, 2).toUpperCase();
  }

  getGrade(percentage: number): { label: string; class: string } {
    if (percentage >= 85) return { label: 'Exceptional', class: 'grade-exceptional' };
    if (percentage >= 70) return { label: 'Proficient', class: 'grade-proficient' };
    if (percentage >= 50) return { label: 'Developing', class: 'grade-developing' };
    return { label: 'Needs Focus', class: 'grade-focus' };
  }
}
