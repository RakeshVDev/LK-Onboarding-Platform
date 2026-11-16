import '@angular/compiler';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';
import { OnboardingService, NavigationPermissions } from './onboarding.service';

describe('OnboardingService', () => {
  const lockedPerms: NavigationPermissions = {
    role: 'learner',
    onboarding_stage: 'assessment_pending',
    all_assessments_completed: false,
    is_activated_by_admin: false,
    selected_department_id: null,
    selected_department_name: null,
    department_approved: false,
    is_unlocked: false,
    assessment_only_mode: true,
    can_select_department: false,
    redirect_to: '/my-assessments',
    allowed_items: ['assessment', 'result', 'report'],
    locked_items: ['dashboard', 'courses', 'cohorts', 'departments', 'users', 'profile'],
    nav_items: [
      { key: 'assessment', label: 'Assessment', route: '/my-assessments', allowed: true },
      { key: 'result', label: 'Result', route: '/my-results', allowed: true },
      { key: 'report', label: 'Report', route: '/my-reports', allowed: true }
    ],
    status_message: 'Complete all assigned assessments.'
  };

  let mockHttp: { get: ReturnType<typeof vi.fn>; post: ReturnType<typeof vi.fn> };
  let mockAuth: {
    getToken: ReturnType<typeof vi.fn>;
    getCurrentUser: ReturnType<typeof vi.fn>;
  };
  let service: OnboardingService;

  beforeEach(() => {
    vi.restoreAllMocks();
    mockHttp = {
      get: vi.fn(),
      post: vi.fn()
    };
    mockAuth = {
      getToken: vi.fn().mockReturnValue('token-1'),
      getCurrentUser: vi.fn().mockResolvedValue({ id: 5, role: 'learner' })
    };
    service = new OnboardingService(mockHttp as any, mockAuth as any);
  });

  it('fetches and caches /api/navigation/permissions and updates signal state', async () => {
    mockHttp.get.mockReturnValue(of(lockedPerms));

    const first = await service.getPermissions();
    const second = await service.getPermissions();

    expect(first.allowed_items).toEqual(['assessment', 'result', 'report']);
    expect(second.is_unlocked).toBe(false);
    expect(service.permissionsState()?.onboarding_stage).toBe('assessment_pending');
    expect(mockHttp.get).toHaveBeenCalledTimes(1);
    expect(mockHttp.get.mock.calls[0][0]).toBe('/api/navigation/permissions');

    mockAuth.getToken.mockReturnValue('token-2');
    await service.getPermissions();
    expect(mockHttp.get).toHaveBeenCalledTimes(2);
  });

  it('submits POST /api/assessments/complete and refreshes permissions and user', async () => {
    const activatedReady: NavigationPermissions = {
      ...lockedPerms,
      onboarding_stage: 'awaiting_activation',
      all_assessments_completed: true
    };
    mockHttp.post.mockReturnValue(
      of({
        user: { id: 5, role: 'learner', all_assessments_completed: true },
        permissions: activatedReady,
        total_assigned: 2,
        completed_count: 2,
        pending_count: 0,
        message: 'Done'
      })
    );

    const res = await service.completeAssessments();
    expect(mockHttp.post.mock.calls[0][0]).toBe('/api/assessments/complete');
    expect(res.permissions.onboarding_stage).toBe('awaiting_activation');
    expect(service.permissionsState()?.all_assessments_completed).toBe(true);
    expect(mockAuth.getCurrentUser).toHaveBeenCalledWith(true);
  });

  it('calls admin activate, joinee department select, and admin department approve endpoints', async () => {
    mockHttp.post.mockReturnValue(of({ id: 5, is_activated_by_admin: true }));
    const activated = await service.activateUserOnboarding(5);
    expect(mockHttp.post.mock.calls[0][0]).toBe('/api/admin/users/5/activate');
    expect(activated.is_activated_by_admin).toBe(true);

    mockHttp.get.mockReturnValue(
      of({ ...lockedPerms, onboarding_stage: 'department_pending_approval', is_activated_by_admin: true })
    );
    mockHttp.post.mockReturnValue(of({ id: 5, selected_department_id: '3' }));
    const selected = await service.selectMyDepartment(3, 'Python interest');
    expect(mockHttp.post.mock.calls[1][0]).toBe('/api/users/me/select-department');
    expect(mockHttp.post.mock.calls[1][1]).toEqual({ department_id: 3, notes: 'Python interest' });
    expect(selected.selected_department_id).toBe('3');

    mockHttp.post.mockReturnValue(of({ id: 5, department_approved: true }));
    const approved = await service.approveUserDepartment(5);
    expect(mockHttp.post.mock.calls[2][0]).toBe('/api/admin/users/5/approve-department');
    expect(approved.department_approved).toBe(true);
  });
});

