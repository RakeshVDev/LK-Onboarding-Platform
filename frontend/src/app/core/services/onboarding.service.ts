import { Injectable, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService, CurrentUser } from './auth.service';
import { ManagedUser } from './user-management.service';

export type OnboardingStage =
  | 'assessment_pending'
  | 'awaiting_activation'
  | 'department_selection'
  | 'department_pending_approval'
  | 'unlocked'
  | 'staff';

export interface NavItemPermission {
  key: string;
  label: string;
  route: string;
  allowed: boolean;
}

export interface NavigationPermissions {
  role: string;
  onboarding_stage: OnboardingStage;
  all_assessments_completed: boolean;
  is_activated_by_admin: boolean;
  selected_department_id: string | null;
  selected_department_name: string | null;
  department_approved: boolean;
  is_unlocked: boolean;
  assessment_only_mode: boolean;
  can_select_department: boolean;
  redirect_to: string;
  allowed_items: string[];
  locked_items: string[];
  nav_items: NavItemPermission[];
  status_message: string;
}

export interface AssessmentCompletionResponse {
  user: CurrentUser;
  permissions: NavigationPermissions;
  total_assigned: number;
  completed_count: number;
  pending_count: number;
  message: string;
}

@Injectable({ providedIn: 'root' })
export class OnboardingService {
  readonly permissionsState = signal<NavigationPermissions | null>(null);

  private cachedPermissions: NavigationPermissions | null = null;
  private cachedToken: string | null = null;
  private pendingPromise: Promise<NavigationPermissions> | null = null;

  constructor(
    private readonly http: HttpClient,
    private readonly authService: AuthService
  ) {}

  private authOptions(): { headers: HttpHeaders } {
    const token = this.authService.getToken();
    if (!token) {
      throw new Error('Your session has expired. Please sign in again.');
    }
    return {
      headers: new HttpHeaders({
        Authorization: `Bearer ${token}`
      })
    };
  }

  async getPermissions(force = false): Promise<NavigationPermissions> {
    const activeToken = this.authService.getToken();
    if (this.cachedToken !== activeToken) {
      this.clearCache();
      this.cachedToken = activeToken;
    }

    if (!force && this.cachedPermissions) {
      this.permissionsState.set(this.cachedPermissions);
      return this.cachedPermissions;
    }

    if (!force && this.pendingPromise) {
      return this.pendingPromise;
    }

    this.pendingPromise = (async () => {
      try {
        const res = await firstValueFrom(
          this.http.get<NavigationPermissions>(
            '/api/navigation/permissions',
            this.authOptions()
          )
        );
        this.cachedToken = this.authService.getToken();
        this.cachedPermissions = res;
        this.permissionsState.set(res);
        return res;
      } finally {
        this.pendingPromise = null;
      }
    })();

    return this.pendingPromise;
  }

  async completeAssessments(): Promise<AssessmentCompletionResponse> {
    const res = await firstValueFrom(
      this.http.post<AssessmentCompletionResponse>(
        '/api/assessments/complete',
        {},
        this.authOptions()
      )
    );
    this.cachedPermissions = res.permissions;
    this.permissionsState.set(res.permissions);
    try {
      await this.authService.getCurrentUser(true);
    } catch {
      // Non-fatal if session refresh runs elsewhere
    }
    return res;
  }

  async activateUserOnboarding(userId: number): Promise<ManagedUser> {
    return firstValueFrom(
      this.http.post<ManagedUser>(
        `/api/admin/users/${userId}/activate`,
        {},
        this.authOptions()
      )
    );
  }

  async selectMyDepartment(
    departmentId: string | number,
    notes?: string | null
  ): Promise<CurrentUser> {
    const res = await firstValueFrom(
      this.http.post<CurrentUser>(
        '/api/users/me/select-department',
        { department_id: departmentId, notes: notes ?? null },
        this.authOptions()
      )
    );
    await this.getPermissions(true);
    try {
      await this.authService.getCurrentUser(true);
    } catch {
      // Ignore refresh error
    }
    return res;
  }

  async approveUserDepartment(
    userId: number,
    departmentId?: string | number | null,
    notes?: string | null
  ): Promise<ManagedUser> {
    const body =
      departmentId !== undefined || notes !== undefined
        ? {
            department_id: departmentId ?? null,
            notes: notes ?? null
          }
        : {};
    return firstValueFrom(
      this.http.post<ManagedUser>(
        `/api/admin/users/${userId}/approve-department`,
        body,
        this.authOptions()
      )
    );
  }

  clearCache(): void {
    this.cachedPermissions = null;
    this.cachedToken = null;
    this.pendingPromise = null;
    this.permissionsState.set(null);
  }
}

