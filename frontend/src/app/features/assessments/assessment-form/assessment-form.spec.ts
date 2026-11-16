import { describe, it, expect, beforeEach, vi } from 'vitest';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { AssessmentForm } from './assessment-form';
import { AssessmentService } from '../services/assessment';
import { LearningService } from '../../../core/services/learning.service';
import { AuthService } from '../../../core/services/auth.service';

describe('AssessmentForm', () => {
  let component: AssessmentForm;
  let fixture: ComponentFixture<AssessmentForm>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssessmentForm],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        {
          provide: AssessmentService,
          useValue: {
            getAssignableTargets: vi.fn(() => of({ cohorts: [], learners: [] })),
            getTemplates: vi.fn(() => of([])),
            getTemplate: vi.fn(() => of(null)),
            getBankQuestions: vi.fn(() => of([])),
          },
        },
        {
          provide: AuthService,
          useValue: {
            hasRole: (...roles: string[]) => roles.includes('superadmin'),
            getCurrentUserSnapshot: () => ({ id: 1, role: 'superadmin', full_name: 'Super Admin', email: 'sa@lk.test', is_active: true }),
          },
        },
        {
          provide: LearningService,
          useValue: {
            getDepartments: vi.fn(async () => [
              { id: 1, name: 'All / Common', description: 'Common track', is_active: true },
              { id: 2, name: 'Python', description: 'Python track', is_active: true },
            ]),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AssessmentForm);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  });

  it('should create and default question count for assessment domains', () => {
    expect(component).toBeTruthy();
    expect(component.form.controls.question_count.value).toBe(25);

    component.onTypeChange('programming');
    expect(component.form.controls.question_count.value).toBe(20);
    expect(component.qCategory).toBe('programming_logic');
  });
});
