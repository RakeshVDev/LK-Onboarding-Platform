import { describe, it, expect, vi } from 'vitest';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';

import { DepartmentSelection } from './department-selection';
import { LearningService } from '../../../core/services/learning.service';
import { OnboardingService } from '../../../core/services/onboarding.service';

describe('DepartmentSelection Component', () => {
  it('excludes All / Common and submits chosen specialization department when activated', async () => {
    const onboardingMock = {
      getPermissions: vi.fn(async () => ({
        role: 'learner',
        onboarding_stage: 'department_selection',
        all_assessments_completed: true,
        is_activated_by_admin: true,
        selected_department_id: null,
        selected_department_name: null,
        department_approved: false,
        is_unlocked: false,
        assessment_only_mode: true,
        can_select_department: true,
        redirect_to: '/department-selection',
        allowed_items: ['assessment', 'result', 'report'],
        locked_items: [],
        nav_items: [],
        status_message: 'Select dept'
      })),
      selectMyDepartment: vi.fn(async () => ({
        id: 11,
        full_name: 'Joinee',
        email: 'joinee@lk.local',
        role: 'learner',
        is_active: true,
        selected_department_id: '3',
        selected_department_name: 'Python'
      }))
    };

    const learningMock = {
      getDepartments: vi.fn(async () => [
        { id: 1, name: 'PHP', description: 'PHP track', is_active: true },
        { id: 3, name: 'Python', description: 'Python track', is_active: true },
        { id: 6, name: 'All / Common', description: 'Common track', is_active: true }
      ])
    };

    TestBed.configureTestingModule({
      imports: [DepartmentSelection],
      providers: [
        provideZonelessChangeDetection(),
        provideRouter([]),
        { provide: OnboardingService, useValue: onboardingMock },
        { provide: LearningService, useValue: learningMock }
      ]
    });

    const fixture: ComponentFixture<DepartmentSelection> = TestBed.createComponent(DepartmentSelection);
    fixture.detectChanges();
    await fixture.componentInstance.loadData(true);
    fixture.detectChanges();

    const cards = Array.from(
      fixture.nativeElement.querySelectorAll('.dept-card')
    ) as HTMLButtonElement[];
    expect(cards.length).toBe(2);
    expect(fixture.nativeElement.textContent).not.toContain('All / Common');

    cards[1].click();
    fixture.detectChanges();

    const submitBtn = fixture.nativeElement.querySelector('.btn-submit') as HTMLButtonElement;
    submitBtn.click();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(onboardingMock.selectMyDepartment).toHaveBeenCalledWith(3, null);
    expect(fixture.nativeElement.textContent).toContain('Python');
  });
});

