
import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';

import {
  AssessmentService,
  AssessmentScoresResponse,
  AssessmentReport
} from '../services/assessment';

@Component({
  selector: 'app-assessment-results',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './assessment-results.html',
  styleUrl: './assessment-results.scss'
})
export class AssessmentResults implements OnInit {

  private api = inject(AssessmentService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  sessionId = 0;

  results: AssessmentScoresResponse | null = null;
  report: AssessmentReport | null = null;

  loading = true;
  reportLoading = false;

  errorMessage = '';

  ngOnInit(): void {

    this.sessionId = Number(
      this.route.snapshot.paramMap.get('sessionId')
    );

    if (!this.sessionId || this.sessionId <= 0) {

      this.errorMessage = 'Invalid assessment session.';
      this.loading = false;
      return;

    }

    this.loadResults();

  }

  loadResults(): void {

    this.api.getResults(this.sessionId).subscribe({

      next: data => {

        this.results = data;
        this.loading = false;

      },

      error: error => {

        this.errorMessage =
          error.error?.detail || 'Unable to load assessment results.';

        this.loading = false;

      }

    });

  }

  generateReport(): void {

    this.reportLoading = true;
    this.errorMessage = '';

    this.api.generateReport(this.sessionId).subscribe({

      next: report => {

        this.report = report;
        this.reportLoading = false;

      },

      error: error => {

        this.reportLoading = false;

        this.errorMessage =
          error.error?.detail || 'Unable to generate report.';

      }

    });

  }

  viewReport(): void {

    void this.router.navigate([
      '/assessments/report',
      this.sessionId
    ]);

  }

  categoryLabel(category: string): string {

    return category
      .replaceAll('_', ' ')
      .replace(/\b\w/g, char => char.toUpperCase());

  }

}
