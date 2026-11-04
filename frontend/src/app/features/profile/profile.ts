import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService, CurrentUser } from '../../core/services/auth.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './profile.html',
  styleUrl: './profile.scss'
})
export class Profile implements OnInit {
  readonly user = signal<CurrentUser | null>(null);
  readonly loading = signal(true);
  readonly activeTab = signal<'general' | 'security' | 'permissions'>('general');

  // Edit profile state
  editName = '';
  isSavingProfile = false;
  profileSuccess = '';
  profileError = '';

  // Password change state
  currentPassword = '';
  newPassword = '';
  confirmPassword = '';
  isChangingPassword = false;
  passwordSuccess = '';
  passwordError = '';

  constructor(private readonly authService: AuthService) {}

  async ngOnInit(): Promise<void> {
    try {
      const current = await this.authService.getCurrentUser();
      this.user.set(current);
      this.editName = current.full_name;
    } catch (err: any) {
      this.profileError = 'Unable to load profile data.';
    } finally {
      this.loading.set(false);
    }
  }

  get userInitial(): string {
    return this.user()?.full_name?.charAt(0)?.toUpperCase() || 'U';
  }

  get roleDisplayName(): string {
    switch (this.user()?.role) {
      case 'superadmin': return 'Super Administrator';
      case 'admin': return 'Administrator';
      case 'teacher': return 'Instructor / Academic Faculty';
      case 'learner': return 'Learner / New Joinee';
      default: return 'User';
    }
  }

  get formattedJoinDate(): string {
    const raw = this.user()?.created_at;
    if (!raw) return 'Active Member';
    try {
      const date = new Date(raw);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return 'Active Member';
    }
  }

  setTab(tab: 'general' | 'security' | 'permissions'): void {
    this.activeTab.set(tab);
    this.profileSuccess = '';
    this.profileError = '';
    this.passwordSuccess = '';
    this.passwordError = '';
  }

  async saveProfile(): Promise<void> {
    if (!this.editName.trim()) {
      this.profileError = 'Full name cannot be blank.';
      return;
    }

    this.isSavingProfile = true;
    this.profileSuccess = '';
    this.profileError = '';

    try {
      const updated = await this.authService.updateProfile(this.editName.trim());
      this.user.set(updated);
      this.profileSuccess = 'Profile details updated successfully!';
    } catch (err: any) {
      this.profileError = err?.error?.detail || err?.message || 'Failed to update profile.';
    } finally {
      this.isSavingProfile = false;
    }
  }

  async changePassword(): Promise<void> {
    this.passwordSuccess = '';
    this.passwordError = '';

    if (!this.currentPassword) {
      this.passwordError = 'Please enter your current password.';
      return;
    }

    if (!this.newPassword || this.newPassword.length < 8) {
      this.passwordError = 'New password must be at least 8 characters long.';
      return;
    }

    if (this.newPassword !== this.confirmPassword) {
      this.passwordError = 'New password and confirmation do not match.';
      return;
    }

    this.isChangingPassword = true;

    try {
      const res = await this.authService.changePassword(this.currentPassword, this.newPassword);
      this.passwordSuccess = res.message || 'Password changed successfully!';
      this.currentPassword = '';
      this.newPassword = '';
      this.confirmPassword = '';
    } catch (err: any) {
      this.passwordError = err?.error?.detail || err?.message || 'Failed to update password.';
    } finally {
      this.isChangingPassword = false;
    }
  }
}
