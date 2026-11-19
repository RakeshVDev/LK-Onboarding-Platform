import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';

import { Departments } from './departments';
import { AuthService, UserRole } from '../../core/services/auth.service';
import {
  Department,
  DepartmentMembersResponse,
  LearningService
} from '../../core/services/learning.service';

const MOCK_DEPARTMENTS: Department[] = [
  {
    id: 1,
    name: 'Python Engineering',
    description: 'Backend APIs and automation',
    is_active: true
  }
];

const MOCK_ROSTER_SUPERADMIN: DepartmentMembersResponse = {
  department_id: 1,
  department_name: 'Python Engineering',
  teachers: [
    {
      id: 10,
      full_name: 'Priya Mentor',
      email: 'priya@example.com',
      role: 'teacher',
      is_active: true
    }
  ],
  students: [
    {
      id: 20,
      full_name: 'Aarav Learner',
      email: 'aarav@example.com',
      role: 'learner',
      is_active: true
    }
  ]
};

describe('Departments roster & card cleanup', () => {
  const createComponentForRole = async (role: UserRole, roster: DepartmentMembersResponse) => {
    TestBed.resetTestingModule();

    const learningServiceStub = {
      getDepartments: vi.fn().mockResolvedValue(MOCK_DEPARTMENTS),
      getDepartmentRequests: vi.fn().mockResolvedValue([]),
      getDeletionRequests: vi.fn().mockResolvedValue([]),
      getDepartmentMembers: vi.fn().mockResolvedValue(roster)
    };

    const authServiceStub = {
      hasRole: (...roles: UserRole[]) => roles.includes(role),
      getCurrentUserSnapshot: () => ({ id: 1, role })
    };

    await TestBed.configureTestingModule({
      imports: [Departments],
      providers: [
        { provide: LearningService, useValue: learningServiceStub },
        { provide: AuthService, useValue: authServiceStub }
      ]
    }).compileComponents();

    const fixture = TestBed.createComponent(Departments);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return { fixture, learningServiceStub };
  };

  it('removes Department #no badge and shows Teacher and Student sections when superadmin clicks a department card', async () => {
    const { fixture, learningServiceStub } = await createComponentForRole(
      'superadmin',
      MOCK_ROSTER_SUPERADMIN
    );

    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).toContain('Python Engineering');
    expect(host.textContent).not.toContain('Department #1');

    const card = host.querySelector('.dept-card') as HTMLElement;
    expect(card).toBeTruthy();
    card.click();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(learningServiceStub.getDepartmentMembers).toHaveBeenCalledWith(1);
    const headings = Array.from(host.querySelectorAll('.roster-section-head h3')).map(el =>
      el.textContent?.trim()
    );
    expect(headings).toEqual(['Teacher', 'Student']);
    expect(host.textContent).toContain('Priya Mentor');
    expect(host.textContent).toContain('Aarav Learner');
  });

  it('allows teachers to click an assigned department card and view Student roster without admin tabs', async () => {
    const { fixture, learningServiceStub } = await createComponentForRole('teacher', {
      ...MOCK_ROSTER_SUPERADMIN,
      teachers: []
    });

    const host = fixture.nativeElement as HTMLElement;
    expect(host.textContent).not.toContain('Department #1');
    expect(host.textContent).not.toContain('Joinee Track Requests');

    const card = host.querySelector('.dept-card') as HTMLElement;
    card.click();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(learningServiceStub.getDepartmentMembers).toHaveBeenCalledWith(1);
    const headings = Array.from(host.querySelectorAll('.roster-section-head h3')).map(el =>
      el.textContent?.trim()
    );
    expect(headings).toEqual(['Student']);
    expect(host.textContent).toContain('Aarav Learner');
  });
});
