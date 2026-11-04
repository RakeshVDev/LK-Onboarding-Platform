import {
  ChangeDetectorRef,
  Component,
  OnInit,
  inject
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import {
  AssessmentService,
  UserAssessmentResultItem
} from '../services/assessment';

@Component({
  selector: 'app-learner-results',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './learner-results.html',
  styleUrl: './learner-results.scss'
})
export class LearnerResults implements OnInit {
  private readonly api = inject(AssessmentService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  results: UserAssessmentResultItem[] = [];
  loading = true;
  errorMessage = '';

  ngOnInit(): void {
    this.loadResults();
  }

  loadResults(): void {
    this.loading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    this.api.getMyResults().subscribe({
      next: (data) => {
        this.results = Array.isArray(data) ? data : [];
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage =
          error.error?.detail || 'Unable to load your assessment results.';
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  get completedResults(): UserAssessmentResultItem[] {
    return this.results.filter(r => r.status === 'completed');
  }

  get inProgressResults(): UserAssessmentResultItem[] {
    return this.results.filter(r => r.status === 'in_progress');
  }

  get totalCompleted(): number {
    return this.completedResults.length;
  }

  get averageScore(): number {
    if (!this.completedResults.length) return 0;
    const total = this.completedResults.reduce((acc, r) => acc + r.overall_percentage, 0);
    return Math.round((total / this.completedResults.length) * 10) / 10;
  }

  get bestScore(): number {
    if (!this.completedResults.length) return 0;
    return Math.max(...this.completedResults.map(r => r.overall_percentage));
  }

  viewReport(sessionId: number): void {
    void this.router.navigate(['/assessments/report', sessionId]);
  }

  viewScores(sessionId: number): void {
    void this.router.navigate(['/assessments/results', sessionId]);
  }

  resumeSession(sessionId: number): void {
    void this.router.navigate(['/assessments/take', sessionId]);
  }

  goToAssessments(): void {
    void this.router.navigate(['/my-assessments']);
  }

  categoryLabel(category: string): string {
    return category
      .replaceAll('_', ' ')
      .replace(/\b\w/g, char => char.toUpperCase());
  }

  typeLabel(type: string): string {
    switch (type) {
      case 'psychometric': return 'Psychometric';
      case 'technical': return 'Technical';
      case 'english_grammar': return 'English Grammar';
      default: return type.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
    }
  }

  getGrade(percentage: number): { label: string; class: string } {
    if (percentage >= 85) return { label: 'Exceptional', class: 'grade-exceptional' };
    if (percentage >= 70) return { label: 'Proficient', class: 'grade-proficient' };
    if (percentage >= 50) return { label: 'Developing', class: 'grade-developing' };
    return { label: 'Needs Focus', class: 'grade-focus' };
  }
}
