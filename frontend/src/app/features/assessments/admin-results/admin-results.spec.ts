import { describe, it, expect, beforeEach, vi } from 'vitest';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { AdminResults } from './admin-results';
import { AssessmentService, AdminAssessmentResultsResponse } from '../services/assessment';
import { AuthService } from '../../../core/services/auth.service';

describe('AdminResults (SuperAdmin Joinee-First Flow)', () => {
  let component: AdminResults;
  let fixture: ComponentFixture<AdminResults>;
  let getAdminResultsSpy: ReturnType<typeof vi.fn>;

  const allRows: AdminAssessmentResultsResponse = {
    total_assessments: 3,
    completed_count: 2,
    in_progress_count: 0,
    expired_count: 0,
    not_started_count: 1,
    attended_count: 2,
    average_score: 78,
    unique_learners: 2,
    results: [
      {
        session_id: 101,
        template_id: 1,
        template_name: 'Python Core Test',
        assessment_type: 'programming',
        learner_user_id: 21,
        learner_name: 'Kabir Mehta',
        learner_email: 'student1@lkplatform.com',
        status: 'completed',
        total_score: 8,
        max_score: 10,
        overall_percentage: 80,
        has_report: true,
        tab_switch_count: 0,
        question_count: 10,
        categories: [],
      },
      {
        session_id: 102,
        template_id: 2,
        template_name: 'Grammar Check',
        assessment_type: 'english_grammar',
        learner_user_id: 21,
        learner_name: 'Kabir Mehta',
        learner_email: 'student1@lkplatform.com',
        status: 'completed',
        total_score: 7.6,
        max_score: 10,
        overall_percentage: 76,
        has_report: true,
        tab_switch_count: 0,
        question_count: 10,
        categories: [],
      },
      {
        session_id: null,
        template_id: 1,
        template_name: 'Python Core Test',
        assessment_type: 'programming',
        learner_user_id: 22,
        learner_name: 'Diya Kulkarni',
        learner_email: 'student2@lkplatform.com',
        status: 'not_started',
        total_score: 0,
        max_score: 10,
        overall_percentage: 0,
        has_report: false,
        tab_switch_count: 0,
        question_count: 10,
        categories: [],
      },
    ],
  };

  beforeEach(async () => {
    getAdminResultsSpy = vi.fn((params?: any) => {
      if (params?.learner_user_id === 21) {
        return of({
          ...allRows,
          results: allRows.results.filter((r) => r.learner_user_id === 21),
        });
      }
      return of(allRows);
    });

    await TestBed.configureTestingModule({
      imports: [AdminResults],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        {
          provide: AssessmentService,
          useValue: {
            getTemplates: vi.fn(() => of([])),
            getAdminResults: getAdminResultsSpy,
          },
        },
        {
          provide: AuthService,
          useValue: {
            hasRole: (...roles: string[]) => roles.includes('superadmin'),
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AdminResults);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  });

  it('shows only joinee names initially for superadmin and displays only selected joinee results on click', async () => {
    const el: HTMLElement = fixture.nativeElement;
    const joineeRows = el.querySelectorAll('.joinee-name-row');
    expect(joineeRows.length).toBe(2);
    expect(el.textContent).toContain('Kabir Mehta');
    expect(el.textContent).toContain('Diya Kulkarni');
    // Results table is hidden until a joinee Result button is clicked
    expect(el.querySelector('.results-table')).toBeNull();

    // Click Result on Kabir Mehta
    const kabirEntry = component.joineeDirectory().find((j) => j.userId === 21)!;
    component.openJoineeResults(kabirEntry);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(component.selectedJoinee()?.userId).toBe(21);
    expect(component.selectedJoineeResults().length).toBe(2);
    expect(component.selectedJoineeResults().every((r) => r.learner_user_id === 21)).toBe(true);
    expect(el.querySelector('.results-table')).not.toBeNull();
    expect(el.textContent).toContain('Python Core Test');
    expect(el.textContent).toContain('Grammar Check');
    expect(el.textContent).not.toContain('Diya Kulkarni');
  });

  it('uses the same learner-first name list and Result drill-down for admin and teacher roles', async () => {
    for (const role of ['admin', 'teacher']) {
      TestBed.resetTestingModule();
      await TestBed.configureTestingModule({
        imports: [AdminResults],
        providers: [
          provideZonelessChangeDetection(),
          provideRouter([]),
          {
            provide: AssessmentService,
            useValue: {
              getTemplates: vi.fn(() => of([])),
              getAdminResults: getAdminResultsSpy,
            },
          },
          {
            provide: AuthService,
            useValue: {
              hasRole: (...roles: string[]) => roles.includes(role),
            },
          },
        ],
      }).compileComponents();

      const roleFixture = TestBed.createComponent(AdminResults);
      const roleComp = roleFixture.componentInstance;
      roleFixture.detectChanges();
      await roleFixture.whenStable();
      roleFixture.detectChanges();

      const roleEl: HTMLElement = roleFixture.nativeElement;
      expect(roleComp.isStaffDirectoryView()).toBe(true);
      expect(roleEl.querySelectorAll('.joinee-name-row').length).toBe(2);
      expect(roleEl.querySelector('.results-table')).toBeNull();
    }
  });
});
