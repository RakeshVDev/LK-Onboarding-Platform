
import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import {
  CreateUserRequest,
  ManagedRole,
  ManagedUser,
  UserManagementService
} from '../../core/services/user-management.service';
import { AuthService, CurrentUser } from '../../core/services/auth.service';
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
  readonly currentUser = signal<CurrentUser | null>(null);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly showForm = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');

  search = '';
  fullName = '';
  email = '';
  password = '';
  role: ManagedRole = 'learner';

  constructor(
    private readonly userService: UserManagementService,
    private readonly authService: AuthService
  ) {}

  get isSuperadmin(): boolean {
    return this.currentUser()?.role === 'superadmin';
  }

  get canCreateAdmin(): boolean {
    return this.isSuperadmin;
  }

  async ngOnInit(): Promise<void> {
    try {
      this.currentUser.set(await this.authService.getCurrentUser());
      await this.loadUsers();
    } catch (error: unknown) {
      this.errorMessage.set(this.messageFor(error));
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
      role: this.role
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
      `${nextStatus ? 'Activate' : 'Deactivate'} ${user.full_name}'s account?`
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
        `${updated.full_name}'s account is now ${updated.is_active ? 'active' : 'inactive'}.`
      );
    } catch (error: unknown) {
      this.errorMessage.set(this.messageFor(error));
    }
  }

  private resetForm(): void {
    this.fullName = '';
    this.email = '';
    this.password = '';
    this.role = 'learner';
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
        return 'Identity API is unavailable. Check that port 8000 is running.';
      }

      return error.error?.detail || 'The request could not be completed.';
    }

    return error instanceof Error
      ? error.message
      : 'An unexpected error occurred.';
  }
}
