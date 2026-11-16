import {
  ChangeDetectorRef,
  Component,
  OnInit,
  computed,
  inject,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import {
  AssessmentService,
  UserAssessmentResultItem
} from '../services/assessment';
import {
  AssessmentRadarChartComponent,
  RadarChartSeries
} from '../components/assessment-radar-chart/assessment-radar-chart';

@Component({
  selector: 'app-learner-results',
  standalone: true,
  imports: [CommonModule, RouterModule, AssessmentRadarChartComponent],
  templateUrl: './learner-results.html',
  styleUrl: './learner-results.scss'
})
export class LearnerResults implements OnInit {
  private readonly api = inject(AssessmentService);
  private readonly router = inject(Router);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly results = signal<UserAssessmentResultItem[]>([]);
  readonly loading = signal(true);
  readonly errorMessage = signal('');

  readonly competencyRadarAxes = computed<string[]>(() => {
    const completed = this.results().filter((r) => r.status === 'completed');
    if (completed.length === 0) return [];
    const dimMap = new Map<string, number[]>();
    for (const item of completed) {
      if (item.categories?.length) {
        for (const cat of item.categories) {
          const label = this.categoryLabel(cat.category);
          const list = dimMap.get(label) ?? [];
          list.push(Number(cat.percentage ?? 0));
          dimMap.set(label, list);
        }
      } else {
        const label = this.typeLabel(item.assessment_type);
        const list = dimMap.get(label) ?? [];
        list.push(Number(item.overall_percentage ?? 0));
        dimMap.set(label, list);
      }
    }
    return Array.from(dimMap.keys()).slice(0, 10);
  });

  readonly competencyRadarSeries = computed<RadarChartSeries[]>(() => {
    const axes = this.competencyRadarAxes();
    const completed = this.results().filter((r) => r.status === 'completed');
    if (axes.length === 0 || completed.length === 0) return [];

    const buckets = new Map<string, number[]>();
    for (const item of completed) {
      if (item.categories?.length) {
        for (const cat of item.categories) {
          const label = this.categoryLabel(cat.category);
          const arr = buckets.get(label) ?? [];
          arr.push(Number(cat.percentage ?? 0));
          buckets.set(label, arr);
        }
      } else {
        const label = this.typeLabel(item.assessment_type);
        const arr = buckets.get(label) ?? [];
        arr.push(Number(item.overall_percentage ?? 0));
        buckets.set(label, arr);
      }
    }

    const values = axes.map((ax) => {
      const vals = buckets.get(ax) ?? [0];
      return Number((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1));
    });

    return [
      {
        id: 'learner-overall-competency',
        label: 'Your Cross-Assessment Profile',
        values,
        borderColor: '#4f46e5',
        backgroundColor: 'rgba(79, 70, 229, 0.18)',
        seriesType: 'candidate',
        overallPercentage: this.averageScore,
      },
    ];
  });

  ngOnInit(): void {
    this.loadResults();
  }

  loadResults(): void {
    this.loading.set(true);
    this.errorMessage.set('');

    this.api.getMyResults().subscribe({
      next: (data) => {
        this.results.set(Array.isArray(data) ? data : []);
        this.loading.set(false);
        this.cdr.detectChanges();
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(
          error.error?.detail || 'Unable to load your assessment results.'
        );
        this.loading.set(false);
        this.cdr.detectChanges();
      }
    });
  }

  get completedResults(): UserAssessmentResultItem[] {
    return this.results().filter(r => r.status === 'completed');
  }

  get inProgressResults(): UserAssessmentResultItem[] {
    return this.results().filter(r => r.status === 'in_progress');
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
      case 'composition': return 'Composition';
      case 'logical_reasoning': return 'Logical Reasoning';
      case 'cognitive': return 'Cognitive Aptitude';
      case 'programming': return 'Programming';
      case 'algorithm': return 'Algorithms';
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
