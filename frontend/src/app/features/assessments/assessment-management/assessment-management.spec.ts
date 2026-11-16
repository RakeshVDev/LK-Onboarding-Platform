import { describe, it, expect, beforeEach, vi } from 'vitest';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { AssessmentManagement } from './assessment-management';
import { AssessmentService, AssessmentTemplate } from '../services/assessment';
import { AuthService } from '../../../core/services/auth.service';

describe('AssessmentManagement', () => {
  let component: AssessmentManagement;
  let fixture: ComponentFixture<AssessmentManagement>;

  const sampleTemplates: AssessmentTemplate[] = [
    {
      id: 1,
      name: 'ASE Python Pre-Assessment',
      assessment_type: 'programming',
      assessment_tag: 'Pre-Assessment',
      description: 'Core Python & OOP',
      question_count: 20,
      duration_minutes: 30,
      category_config: { programming_logic: { label: 'Programming Logic', question_count: 20 } },
      is_active: true,
      created_by_user_id: 1,
      created_at: '2026-11-15T10:00:00Z',
    },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssessmentManagement],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        {
          provide: AssessmentService,
          useValue: {
            getTemplates: vi.fn(() => of(sampleTemplates)),
            deleteTemplate: vi.fn(() => of({})),
          },
        },
        {
          provide: AuthService,
          useValue: {
            hasRole: (...roles: string[]) => roles.includes('superadmin'),
            getCurrentUserSnapshot: () => ({ id: 1, role: 'superadmin', full_name: 'SA', email: 'sa@lk.test', is_active: true }),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AssessmentManagement);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  });

  it('should create and load assessment templates', () => {
    expect(component).toBeTruthy();
    expect(component.templates.length).toBe(1);
    expect(component.templates[0].name).toBe('ASE Python Pre-Assessment');
  });
});
