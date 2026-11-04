
import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators
} from '@angular/forms';

import { ActivatedRoute, Router } from '@angular/router';

import {
  AssessmentService,
  AssessmentCategory
} from '../services/assessment';

const CATEGORY_CONFIG: Record<string, AssessmentCategory> = {

  personality_work_preferences: {
    label: 'Personality & Work Preferences',
    question_count: 4
  },

  logical_reasoning: {
    label: 'Logical Reasoning',
    question_count: 4
  },

  situational_judgement: {
    label: 'Situational Judgement',
    question_count: 4
  },

  emotional_intelligence: {
    label: 'Emotional Intelligence',
    question_count: 4
  },

  learning_adaptability: {
    label: 'Learning & Adaptability',
    question_count: 4
  }

};

const LOGICAL_REASONING_CONFIG: Record<string, AssessmentCategory> = {
  number_series: { label: 'Number Series', question_count: 4 },
  alphabet_series: { label: 'Alphabet Series', question_count: 3 },
  coding_decoding: { label: 'Coding-Decoding', question_count: 3 },
  blood_relations: { label: 'Blood Relations', question_count: 3 },
  direction_distance: { label: 'Direction and Distance', question_count: 3 },
  pattern_recognition: { label: 'Pattern Recognition', question_count: 3 },
  logical_statements: { label: 'Logical Statements', question_count: 2 },
  odd_one_out: { label: 'Odd One Out', question_count: 2 },
  analogy: { label: 'Analogy', question_count: 2 },
};

@Component({
  selector: 'app-assessment-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule
  ],
  templateUrl: './assessment-form.html',
  styleUrl: './assessment-form.scss'
})
export class AssessmentForm implements OnInit {

  private fb = inject(FormBuilder);
  private api = inject(AssessmentService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  templateId: number | null = null;

  loading = false;
  saving = false;

  errorMessage = '';

  form = this.fb.nonNullable.group({
    name: [
      '',
      [
        Validators.required,
        Validators.minLength(3),
        Validators.maxLength(200)
      ]
    ],

    description: ['']
  });

  ngOnInit(): void {

    const id = Number(
      this.route.snapshot.paramMap.get('id')
    );

    if (id > 0) {

      this.templateId = id;
      this.loadTemplate(id);

    }

  }

  loadTemplate(id: number): void {

    this.loading = true;

    this.api.getTemplates().subscribe({

      next: templates => {

        const template = templates.find(
          item => item.id === id
        );

        if (!template) {

          this.errorMessage = 'Assessment template not found.';

        } else {

          this.form.patchValue({
            name: template.name,
            description: template.description ?? ''
          });

        }

        this.loading = false;

      },

      error: error => {

        this.errorMessage =
          error.error?.detail || 'Unable to load template.';

        this.loading = false;

      }

    });

  }

  save(): void {

    this.errorMessage = '';

    if (this.form.invalid) {

      this.form.markAllAsTouched();
      return;

    }

    const payload = {

      name: this.form.controls.name.value.trim(),

      description:
        this.form.controls.description.value.trim() || null,

      question_count: 20,

      category_config: CATEGORY_CONFIG

    };

    this.saving = true;

    const request = this.templateId

      ? this.api.updateTemplate(
          this.templateId,
          payload
        )

      : this.api.createTemplate(payload);

    request.subscribe({

      next: () => {

        this.saving = false;

        void this.router.navigate(['/assessments']);

      },

      error: error => {

        this.saving = false;

        this.errorMessage =
          error.error?.detail || 'Unable to save assessment.';

      }

    });

  }

  cancel(): void {

    void this.router.navigate(['/assessments']);

  }

}
