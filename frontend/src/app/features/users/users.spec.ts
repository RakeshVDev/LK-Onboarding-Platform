import { describe, it, expect, vi } from 'vitest';
import { provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Users } from './users';
import { ManagedUser, UserManagementService } from '../../core/services/user-management.service';
import { AuthService } from '../../core/services/auth.service';
import { LearningService } from '../../core/services/learning.service';
import { OnboardingService } from '../../core/services/onboarding.service';

describe('Users Component (Admin Activation & Department Approval Controls)', () => {
  const sampleUsers: ManagedUser[] = [
    {
      id: 101,
      full_name: 'Incomplete Learner',
      email: 'incomplete@lk.local',
      role: 'learner',
      is_active: true,
      all_assessments_completed: false,
      is_activated_by_admin: false,
      selected_department_id: null,
      department_approved: false,
      onboarding_stage: 'assessment_pending',
      created_at: '2026-11-13T10:00:00Z'
    },
    {
      id: 102,
      full_name: 'Ready Learner',
      email: 'ready@lk.local',
      role: 'learner',
      is_active: true,
      all_assessments_completed: true,
      is_activated_by_admin: false,
      selected_department_id: null,
      department_approved: false,
      onboarding_stage: 'awaiting_activation',
      created_at: '2026-11-13T10:00:00Z'
    },
    {
      id: 103,
      full_name: 'Pending Approval Learner',
      email: 'pendingdept@lk.local',
      role: 'learner',
      is_active: true,
      all_assessments_completed: true,
      is_activated_by_admin: true,
      selected_department_id: '3',
      selected_department_name: 'Python',
      department_approved: false,
      onboarding_stage: 'department_pending_approval',
      created_at: '2026-11-13T10:00:00Z'
    }
  ];

  async function setup(): Promise<{
    fixture: ComponentFixture<Users>;
    onboardingMock: {
      activateUserOnboarding: ReturnType<typeof vi.fn>;
      approveUserDepartment: ReturnType<typeof vi.fn>;
    };
  }> {
    const onboardingMock = {
      activateUserOnboarding: vi.fn(async (id: number) => ({
        ...sampleUsers[1],
        id,
        is_activated_by_admin: true,
        onboarding_stage: 'department_selection'
      })),
      approveUserDepartment: vi.fn(async (id: number) => ({
        ...sampleUsers[2],
        id,
        department_approved: true,
        onboarding_stage: 'unlocked'
      }))
    };

    TestBed.configureTestingModule({
      imports: [Users],
      providers: [
        provideZonelessChangeDetection(),
        {
          provide: AuthService,
          useValue: {
            getCurrentUser: vi.fn(async () => ({
              id: 1,
              full_name: 'Super Admin',
              email: 'admin@lk.local',
              role: 'superadmin',
              is_active: true
            }))
          }
        },
        {
          provide: UserManagementService,
          useValue: {
            listUsers: vi.fn(async () => sampleUsers.map(u => ({ ...u }))),
            mergeUser: vi.fn(),
            createUser: vi.fn(),
            updateStatus: vi.fn(),
            assignTeacherDepartments: vi.fn(async (id: number, departmentIds: number[]) => ({
              id,
              full_name: 'Teacher One',
              email: 'teacher1@lk.local',
              role: 'teacher',
              is_active: true,
              assigned_department_ids: departmentIds,
              assigned_department_names: departmentIds.map(d => `Dept ${d}`),
              created_at: '2026-11-13T10:00:00Z'
            }))
          }
        },
        {
          provide: LearningService,
          useValue: {
            getDepartments: vi.fn(async () => [
              { id: 1, name: 'All / Common', description: 'Common', is_active: true },
              { id: 2, name: 'Python', description: 'Python', is_active: true },
              { id: 3, name: 'Java', description: 'Java', is_active: true },
              { id: 4, name: 'PHP', description: 'PHP', is_active: true },
              { id: 5, name: '.NET', description: '.NET', is_active: true },
              { id: 6, name: 'Database Engineer', description: 'DB', is_active: true }
            ])
          }
        },
        {
          provide: OnboardingService,
          useValue: onboardingMock
        }
      ]
    });

    const fixture = TestBed.createComponent(Users);
    fixture.detectChanges();
    await fixture.componentInstance.ngOnInit();
    fixture.detectChanges();
    return { fixture, onboardingMock };
  }

  it('enables Activate only after assessments finish and approves department when submitted', async () => {
    const { fixture, onboardingMock } = await setup();
    const rows = Array.from(
      fixture.nativeElement.querySelectorAll('tbody tr')
    ) as HTMLTableRowElement[];

    expect(rows.length).toBe(3);

    const row1Activate = rows[0].querySelector('.btn-onboarding-activate') as HTMLButtonElement;
    const row2Activate = rows[1].querySelector('.btn-onboarding-activate') as HTMLButtonElement;
    const row3Approve = rows[2].querySelector('.btn-onboarding-approve') as HTMLButtonElement;

    expect(row1Activate.disabled).toBe(true);
    expect(row2Activate.disabled).toBe(false);
    expect(row3Approve.disabled).toBe(false);

    row2Activate.click();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(onboardingMock.activateUserOnboarding).toHaveBeenCalledWith(102);

    row3Approve.click();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(onboardingMock.approveUserDepartment).toHaveBeenCalledWith(103);
    expect(fixture.nativeElement.textContent).toContain('✓ Unlocked');
  });

  it('excludes All / Common and caps SuperAdmin teacher department selection at 4 tracks', async () => {
    const { fixture } = await setup();
    const comp = fixture.componentInstance;

    const concreteIds = comp.assignableDepartments().map(d => d.id);
    expect(concreteIds).not.toContain(1);
    expect(concreteIds).toEqual([2, 3, 4, 5, 6]);

    comp.openAssignDepartmentsModal({
      id: 201,
      full_name: 'Teacher One',
      email: 'teacher1@lk.local',
      role: 'teacher',
      is_active: true,
      assigned_department_ids: [2],
      assigned_department_names: ['Python'],
      created_at: '2026-11-13T10:00:00Z'
    });
    for (const id of [3, 4, 5, 6]) {
      comp.toggleModalDept(id);
    }
    expect(comp.selectedModalDeptIds()).toEqual([2, 3, 4, 5]);
    await comp.saveTeacherDepartments();
    expect(comp.assigningTeacher()).toBeNull();
  });
});

