
import { Component, OnInit, signal, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import {
  CreateUserRequest,
  ManagedRole,
  ManagedUser,
  UserManagementService
} from '../../core/services/user-management.service';
import { AuthService, CurrentUser } from '../../core/services/auth.service';
import { Department, LearningService } from '../../core/services/learning.service';
import { OnboardingService } from '../../core/services/onboarding.service';
import { HttpErrorResponse } from '@angular/common/http';

@Component({
  selector: 'app-users',
  standalone: true,
  imports: [FormsModule, DatePipe],
  templateUrl: './users.html',
  styleUrl: './users.scss'
})
export class Users implements OnInit {
  readonly users = signal<ManagedUser[]>([]);
  readonly assignableDepartments = signal<Department[]>([]);
  readonly currentUser = signal<CurrentUser | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly actionUserId = signal<number | null>(null);
  readonly showForm = signal(false);
  readonly selectedCreateDeptIds = signal<number[]>([]);
  readonly assigningTeacher = signal<ManagedUser | null>(null);
  readonly selectedModalDeptIds = signal<number[]>([]);
  readonly savingDepartments = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');

  readonly selectedRoleFilter = signal<string>('all');
  readonly selectedStatusFilter = signal<string>('all');

  readonly totalUsersCount = computed(() => this.users().length);
  readonly activeUsersCount = computed(() => this.users().filter(u => u.is_active).length);
  readonly inactiveUsersCount = computed(() => this.users().filter(u => !u.is_active).length);
  readonly adminUsersCount = computed(() => this.users().filter(u => u.role === 'admin' || u.role === 'superadmin').length);
  readonly teacherUsersCount = computed(() => this.users().filter(u => u.role === 'teacher').length);
  readonly learnerUsersCount = computed(() => this.users().filter(u => u.role === 'learner').length);

  readonly filteredUsers = computed(() => {
    let list = this.users();
    const roleF = this.selectedRoleFilter();
    if (roleF !== 'all') {
      list = list.filter(u => u.role === roleF);
    }
    const statusF = this.selectedStatusFilter();
    if (statusF === 'active') {
      list = list.filter(u => u.is_active);
    } else if (statusF === 'inactive') {
      list = list.filter(u => !u.is_active);
    }
    return list;
  });

  search = '';
  fullName = '';
  email = '';
  password = '';
  role: ManagedRole = 'learner';

  constructor(
    private readonly userService: UserManagementService,
    private readonly authService: AuthService,
    private readonly learningService: LearningService,
    private readonly onboardingService: OnboardingService
  ) { }

  get isSuperadmin(): boolean {
    return this.currentUser()?.role === 'superadmin';
  }

  get canCreateAdmin(): boolean {
    return this.isSuperadmin;
  }

  async ngOnInit(): Promise<void> {
    try {
      this.currentUser.set(await this.authService.getCurrentUser());
      await Promise.all([this.loadUsers(), this.loadAssignableDepartments()]);
    } catch (error: unknown) {
      this.errorMessage.set(this.messageFor(error));
    }
  }

  private async loadAssignableDepartments(): Promise<void> {
    try {
      const list = await this.learningService.getDepartments();
      this.assignableDepartments.set(
        (Array.isArray(list) ? list : []).filter(d => {
          if (!d.is_active) return false;
          const norm = (d.name || '').trim().toLowerCase();
          return norm !== 'all / common' && norm !== 'all/common' && norm !== 'common';
        })
      );
    } catch {
      this.assignableDepartments.set([]);
    }
  }

  async loadUsers(): Promise<void> {
    this.loading.set(true);
    this.errorMessage.set('');

    try {
      this.users.set(await this.userService.listUsers(this.search));
    } catch (error: unknown) {
      this.errorMessage.set(this.messageFor(error));
    } finally {
      this.loading.set(false);
    }
  }

  openCreateForm(): void {
    this.resetForm();
    this.showForm.set(true);
  }

  closeCreateForm(): void {
    this.showForm.set(false);
    this.resetForm();
  }

  async createUser(): Promise<void> {
    this.errorMessage.set('');
    this.successMessage.set('');

    const fullName = this.fullName.trim();
    const normalizedEmail = this.email.trim().toLowerCase();

    if (fullName.length < 2) {
      this.errorMessage.set('Enter a name with at least 2 characters.');
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      this.errorMessage.set('Enter a valid email address.');
      return;
    }

    if (this.password.length < 10) {
      this.errorMessage.set('Password must contain at least 10 characters.');
      return;
    }

    if (this.password.length > 128) {
      this.errorMessage.set('Password cannot exceed 128 characters.');
      return;
    }

    if (this.role === 'admin' && !this.isSuperadmin) {
      this.errorMessage.set('Only a Superadmin can create Admin accounts.');
      return;
    }

    const payload: CreateUserRequest = {
      full_name: fullName,
      email: normalizedEmail,
      password: this.password,
      role: this.role,
      ...(this.role === 'teacher' && this.isSuperadmin && this.selectedCreateDeptIds().length > 0
        ? { assigned_department_ids: this.selectedCreateDeptIds() }
        : {})
    };

    this.saving.set(true);

    try {
      await this.userService.createUser(payload);
      this.successMessage.set('User account created successfully.');
      this.closeCreateForm();
      await this.loadUsers();
    } catch (error: unknown) {
      this.errorMessage.set(this.messageFor(error));
    } finally {
      this.saving.set(false);
    }
  }

  async toggleStatus(user: ManagedUser): Promise<void> {
    this.errorMessage.set('');
    this.successMessage.set('');

    const nextStatus = !user.is_active;

    if (!window.confirm(
      `${nextStatus ? 'Enable login for' : 'Disable login for'} ${user.full_name}'s account?`
    )) {
      return;
    }

    try {
      const updated = await this.userService.updateStatus(
        user.id,
        nextStatus
      );

      this.users.update(items =>
        items.map(item => item.id === updated.id ? updated : item)
      );

      this.successMessage.set(
        `${updated.full_name}'s login status is now ${updated.is_active ? 'active' : 'inactive'}.`
      );
    } catch (error: unknown) {
      this.errorMessage.set(this.messageFor(error));
    }
  }

  onboardingStageLabel(user: ManagedUser): string {
    if (user.role !== 'learner') return 'Full Staff Access';
    if (!user.all_assessments_completed) return 'Assessments Pending';
    if (!user.is_activated_by_admin) return 'Assessments Complete';
    if (!user.department_approved) {
      return user.selected_department_id
        ? `Pending Dept Approval (${user.selected_department_name || user.selected_department_id})`
        : 'Awaiting Dept Selection';
    }
    return `Approved (${user.selected_department_name || user.selected_department_id || 'Unlocked'})`;
  }

  async activateOnboarding(user: ManagedUser): Promise<void> {
    if (this.actionUserId() !== null) return;
    this.errorMessage.set('');
    this.successMessage.set('');
    this.actionUserId.set(user.id);

    try {
      const updated = await this.onboardingService.activateUserOnboarding(user.id);
      this.userService.mergeUser(updated);
      this.users.update(items =>
        items.map(item => item.id === updated.id ? updated : item)
      );
      this.successMessage.set(
        `${updated.full_name} is now activated to choose their department.`
      );
    } catch (error: unknown) {
      this.errorMessage.set(this.messageFor(error));
    } finally {
      this.actionUserId.set(null);
    }
  }

  async approveDepartment(user: ManagedUser): Promise<void> {
    if (this.actionUserId() !== null) return;
    this.errorMessage.set('');
    this.successMessage.set('');
    this.actionUserId.set(user.id);

    try {
      const updated = await this.onboardingService.approveUserDepartment(user.id);
      this.userService.mergeUser(updated);
      this.users.update(items =>
        items.map(item => item.id === updated.id ? updated : item)
      );
      this.successMessage.set(
        `Approved ${updated.selected_department_name || 'department'} for ${updated.full_name}. Full workspace unlocked.`
      );
    } catch (error: unknown) {
      this.errorMessage.set(this.messageFor(error));
    } finally {
      this.actionUserId.set(null);
    }
  }

  toggleCreateDept(deptId: number): void {
    const current = this.selectedCreateDeptIds();
    if (current.includes(deptId)) {
      this.selectedCreateDeptIds.set(current.filter(id => id !== deptId));
      return;
    }
    if (current.length >= 4) {
      this.errorMessage.set('A teacher can be assigned at most 4 departments.');
      return;
    }
    this.errorMessage.set('');
    this.selectedCreateDeptIds.set([...current, deptId]);
  }

  openAssignDepartmentsModal(user: ManagedUser): void {
    if (!this.isSuperadmin || user.role !== 'teacher') return;
    this.errorMessage.set('');
    this.successMessage.set('');
    this.assigningTeacher.set(user);
    this.selectedModalDeptIds.set([...(user.assigned_department_ids || [])]);
  }

  closeAssignDepartmentsModal(): void {
    this.assigningTeacher.set(null);
    this.selectedModalDeptIds.set([]);
  }

  toggleModalDept(deptId: number): void {
    const current = this.selectedModalDeptIds();
    if (current.includes(deptId)) {
      this.selectedModalDeptIds.set(current.filter(id => id !== deptId));
      return;
    }
    if (current.length >= 4) {
      return;
    }
    this.selectedModalDeptIds.set([...current, deptId]);
  }

  async saveTeacherDepartments(): Promise<void> {
    const teacher = this.assigningTeacher();
    if (!teacher || this.savingDepartments()) return;

    const deptIds = this.selectedModalDeptIds();
    if (deptIds.length < 1 || deptIds.length > 4) {
      this.errorMessage.set('Select between 1 and 4 concrete departments for this teacher.');
      return;
    }

    this.savingDepartments.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');
    try {
      const updated = await this.userService.assignTeacherDepartments(teacher.id, deptIds);
      this.users.update(items =>
        items.map(item => item.id === updated.id ? updated : item)
      );
      this.successMessage.set(
        `Assigned ${updated.assigned_department_names?.join(', ') || `${deptIds.length} department(s)`} to ${updated.full_name}.`
      );
      this.closeAssignDepartmentsModal();
    } catch (error: unknown) {
      this.errorMessage.set(this.messageFor(error));
    } finally {
      this.savingDepartments.set(false);
    }
  }

  private resetForm(): void {
    this.fullName = '';
    this.email = '';
    this.password = '';
    this.role = 'learner';
    this.selectedCreateDeptIds.set([]);
  }

  private messageFor(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      if (error.status === 401) {
        return 'Your session has expired. Please sign in again.';
      }

      if (error.status === 403) {
        return 'You do not have permission to perform this action.';
      }

      if (error.status === 409) {
        return error.error?.detail || 'This email is already registered.';
      }

      if (error.status === 0) {
        return 'Identity API is unavailable. Check that port 8001 is running.';
      }

      return error.error?.detail || 'The request could not be completed.';
    }

    return error instanceof Error
      ? error.message
      : 'An unexpected error occurred.';
  }
}
