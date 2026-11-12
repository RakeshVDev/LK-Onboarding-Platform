import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of, throwError } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';

import { AuthService, CurrentUser } from './auth.service';
import { ManagedUser, UserManagementService } from './user-management.service';
import { CohortService } from './cohort.service';

describe('Cohorts Platform Integration (AuthService, UserManagementService, CohortService)', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it('syncs AuthService signal and sessionStorage across getCurrentUser, updateProfile, and logout', async () => {
    const teacher: CurrentUser = {
      id: 42,
      full_name: 'Neha Verma',
      email: 'neha.verma@example.com',
      role: 'teacher',
      is_active: true
    };
    const updatedTeacher: CurrentUser = { ...teacher, full_name: 'Neha V.' };

    const mockHttp = {
      get: vi.fn().mockReturnValue(of(teacher)),
      put: vi.fn().mockReturnValue(of(updatedTeacher))
    } as any;

    const auth = new AuthService(mockHttp);
    sessionStorage.setItem('lk_access_token', 'jwt-token');

    const loaded = await auth.getCurrentUser();
    expect(loaded.full_name).toBe('Neha Verma');
    expect(auth.hasRole('teacher', 'admin', 'superadmin')).toBe(true);
    expect(auth.hasRole('learner')).toBe(false);
    expect(JSON.parse(sessionStorage.getItem('lk_current_user') || '{}').email).toBe('neha.verma@example.com');

    await auth.updateProfile('Neha V.');
    expect(auth.getCurrentUserSnapshot()?.full_name).toBe('Neha V.');
    expect(JSON.parse(sessionStorage.getItem('lk_current_user') || '{}').full_name).toBe('Neha V.');

    auth.logout();
    expect(auth.getToken()).toBeNull();
    expect(auth.getCurrentUserSnapshot()).toBeNull();
    expect(sessionStorage.getItem('lk_current_user')).toBeNull();
    expect(auth.hasRole('teacher')).toBe(false);
  });

  it('provides listTeachers/getTeachers and listLearners/getLearners with loop-free cache sync and 403-safe teacher fallback', async () => {
    const directory: ManagedUser[] = [
      { id: 1, full_name: 'Super Admin', email: 'sa@example.com', role: 'superadmin', is_active: true, created_at: '2026-10-01' },
      { id: 2, full_name: 'Instructor One', email: 't1@example.com', role: 'teacher', is_active: true, created_at: '2026-10-02' },
      { id: 3, full_name: 'Inactive Teacher', email: 't2@example.com', role: 'teacher', is_active: false, created_at: '2026-10-02' },
      { id: 4, full_name: 'Learner One', email: 'l1@example.com', role: 'learner', is_active: true, created_at: '2026-10-03' },
      { id: 5, full_name: 'Inactive Learner', email: 'l2@example.com', role: 'learner', is_active: false, created_at: '2026-10-03' }
    ];

    const mockHttp = {
      get: vi.fn().mockReturnValue(of(directory)),
      post: vi.fn().mockReturnValue(
        of({
          id: 6,
          full_name: 'Learner Two',
          email: 'l2new@example.com',
          role: 'learner',
          is_active: true,
          created_at: '2026-10-04'
        } satisfies ManagedUser)
      ),
      patch: vi.fn().mockReturnValue(
        of({
          id: 4,
          full_name: 'Learner One',
          email: 'l1@example.com',
          role: 'learner',
          is_active: false,
          created_at: '2026-10-03'
        } satisfies ManagedUser)
      )
    } as any;

    const auth = new AuthService({
      get: vi.fn().mockReturnValue(
        of({ id: 1, full_name: 'Super Admin', email: 'sa@example.com', role: 'superadmin', is_active: true })
      )
    } as any);
    sessionStorage.setItem('lk_access_token', 'admin-jwt');
    await auth.getCurrentUser();

    const events: string[] = [];
    window.addEventListener('ase_users_changed', () => events.push('changed'));

    const userMgmt = new UserManagementService(mockHttp, auth);

    // First fetch populates cache and notifies once; second identical fetch emits 0 extra events
    const teachers = await userMgmt.listTeachers();
    expect(teachers.map(t => t.full_name)).toEqual(['Instructor One']);
    expect(events.length).toBe(1);

    const learners = await userMgmt.listLearners();
    expect(learners.map(l => l.full_name)).toEqual(['Learner One']);
    expect(events.length).toBe(1);

    // Creating a user merges into cache and emits event
    await userMgmt.createUser({
      full_name: 'Learner Two',
      email: 'l2new@example.com',
      password: 'Password@123',
      role: 'learner'
    });
    expect(userMgmt.getLearners().map(l => l.full_name)).toEqual(['Learner One', 'Learner Two']);
    expect(events.length).toBe(2);

    // Deactivating Learner One removes them from active learners getter
    await userMgmt.updateStatus(4, false);
    expect(userMgmt.getLearners().map(l => l.full_name)).toEqual(['Learner Two']);

    // Switching to teacher role: listTeachers/listLearners uses cached directory without throwing 403
    const teacherAuth = new AuthService({
      get: vi.fn().mockReturnValue(
        of({ id: 2, full_name: 'Instructor One', email: 't1@example.com', role: 'teacher', is_active: true })
      )
    } as any);
    sessionStorage.setItem('lk_access_token', 'teacher-jwt');
    await teacherAuth.getCurrentUser();

    const forbiddenHttp = {
      get: vi.fn().mockReturnValue(throwError(() => new HttpErrorResponse({ status: 403 })))
    } as any;
    const teacherUserMgmt = new UserManagementService(forbiddenHttp, teacherAuth);

    expect((await teacherUserMgmt.listTeachers()).map(t => t.full_name)).toEqual(['Instructor One']);
    expect((await teacherUserMgmt.listLearners()).map(l => l.full_name)).toEqual(['Learner Two']);
    expect(forbiddenHttp.get).not.toHaveBeenCalled();
  });

  it('attributes CohortService actions to active AuthService user and avoids learner name leaking into trainer fields', async () => {
    const learnerUser: CurrentUser = {
      id: 99,
      full_name: 'Kiran Patel',
      email: 'kiran.patel@example.com',
      role: 'learner',
      is_active: true
    };
    const auth = new AuthService({
      get: vi.fn().mockReturnValue(of(learnerUser))
    } as any);
    sessionStorage.setItem('lk_access_token', 'learner-jwt');
    await auth.getCurrentUser();

    const cohortService = new CohortService({} as any, auth);
    expect(cohortService.getCurrentUser().full_name).toBe('Kiran Patel');

    const state = cohortService.getCohortData();
    expect(state.members.some(m => m.email === 'kiran.patel@example.com')).toBe(true);
    expect(state.attendanceMatrix.students.some(s => s.name === 'Kiran Patel')).toBe(true);

    // Trainer names must never be overwritten with the logged-in learner's name
    cohortService.sanitizeTrainerNames();
    expect(cohortService.getCohortData().sessions.every(s => s.trainer !== 'Kiran Patel')).toBe(true);

    const post = cohortService.createDiscussionPost('Signal question', 'Technical Q&A', 'How do signals interact?');
    expect(post.author).toBe('Kiran Patel');
    expect(post.authorRole).toBe('Learner');
  });
});

