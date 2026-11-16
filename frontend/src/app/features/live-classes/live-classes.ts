import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/services/auth.service';
import { Department, LearningService } from '../../core/services/learning.service';
import {
  AssignableHost,
  LiveClassCreatePayload,
  LiveClassSession,
  LiveClassStatus,
  LiveClassesService,
} from '../../core/services/live-classes.service';
import { BrandLogo } from '../../shared/components/brand-logo/brand-logo';
import { SkeletonLoader } from '../../shared/components/skeleton-loader/skeleton-loader';

@Component({
  selector: 'app-live-classes',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, BrandLogo, SkeletonLoader],
  templateUrl: './live-classes.html',
  styleUrl: './live-classes.scss',
})
export class LiveClassesPage implements OnInit {
  private readonly liveClassesService = inject(LiveClassesService);
  private readonly learningService = inject(LearningService);
  public readonly authService = inject(AuthService);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly joiningId = signal<number | null>(null);
  readonly sessions = signal<LiveClassSession[]>([]);
  readonly departments = signal<Department[]>([]);
  readonly assignableHosts = signal<AssignableHost[]>([]);
  readonly currentUserSnapshot = signal<ReturnType<AuthService['getCurrentUserSnapshot']>>(null);
  readonly approvedDepartmentId = signal<number | null>(null);
  readonly restrictedReason = signal<string | null>(null);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');

  showScheduleModal = false;
  filterDepartmentId: number | null = null;

  // Scheduler Form Fields
  formTitle = '';
  formDepartmentId: number | null = null;
  formInstructorUserId: number | null = null;
  formScheduledLocal = '';
  formDurationMinutes = 60;
  formPlatform = 'Jitsi Meet';
  formMeetingUrl = '';
  formDescription = '';

  get isStaff(): boolean {
    return this.authService.hasRole('superadmin', 'admin', 'teacher');
  }

  get isTeacher(): boolean {
    return this.authService.hasRole('teacher');
  }

  get hasAssignedDepartments(): boolean {
    return !this.isTeacher || this.departments().length > 0;
  }

  canAssignOtherHost(): boolean {
    return this.isStaff;
  }

  private allowedHostRoles(): string[] {
    if (this.authService.hasRole('superadmin')) {
      return ['superadmin', 'admin', 'teacher'];
    }
    if (this.authService.hasRole('admin')) {
      return ['admin', 'teacher'];
    }
    if (this.authService.hasRole('teacher')) {
      return ['teacher'];
    }
    return [];
  }

  formatHostRole(role: string): string {
    switch ((role || '').toLowerCase()) {
      case 'superadmin':
        return 'SuperAdmin';
      case 'admin':
        return 'Admin';
      case 'teacher':
        return 'Teacher';
      default:
        return role || 'Staff';
    }
  }

  canControlSessionStream(session: LiveClassSession): boolean {
    if (!this.isStaff) return false;
    const snap = this.currentUserSnapshot();
    if (!snap || typeof snap.id !== 'number') {
      return false;
    }
    return session.instructor_user_id === snap.id;
  }

  get approvedDepartmentName(): string {
    const id = this.approvedDepartmentId();
    if (!id) return 'Your Approved Department';
    return this.departments().find(d => d.id === id)?.name || `Department #${id}`;
  }

  async ngOnInit(): Promise<void> {
    const snap = this.authService.getCurrentUserSnapshot?.() ?? null;
    this.currentUserSnapshot.set(snap);
    if (!snap && this.authService.getCurrentUser) {
      try {
        const loaded = await this.authService.getCurrentUser();
        this.currentUserSnapshot.set(loaded);
      } catch {
        // Minimal auth mocks may not expose getCurrentUser
      }
    }
    await Promise.all([
      this.loadDepartments(),
      this.isStaff ? this.loadAssignableHosts() : Promise.resolve(),
      this.loadSessions(),
    ]);
  }

  async loadAssignableHosts(): Promise<void> {
    if (!this.isStaff || !this.liveClassesService.getAssignableHosts) {
      return;
    }
    const allowedRoles = new Set(this.allowedHostRoles());
    const snap = this.currentUserSnapshot();
    try {
      const hosts = await firstValueFrom(this.liveClassesService.getAssignableHosts());
      const filtered = (Array.isArray(hosts) ? hosts : []).filter(h =>
        allowedRoles.has((h.role || '').toLowerCase())
      );
      if (filtered.length === 0 && snap && typeof snap.id === 'number') {
        const snapRole = (snap.role || 'teacher').toLowerCase();
        if (allowedRoles.has(snapRole)) {
          filtered.push({
            id: snap.id,
            full_name: snap.full_name || 'Instructor',
            email: snap.email || '',
            role: snapRole,
          });
        }
      }
      this.assignableHosts.set(filtered);
      if (
        filtered.length > 0 &&
        (!this.formInstructorUserId || !filtered.some(h => h.id === this.formInstructorUserId))
      ) {
        const selfId = snap?.id;
        const selfMatch = selfId ? filtered.find(h => h.id === selfId) : undefined;
        this.formInstructorUserId = selfMatch ? selfMatch.id : filtered[0].id;
      }
    } catch (err) {
      console.warn('Could not load assignable instructors:', err);
      if (this.assignableHosts().length === 0 && snap && typeof snap.id === 'number') {
        const snapRole = (snap.role || 'teacher').toLowerCase();
        if (allowedRoles.has(snapRole)) {
          this.assignableHosts.set([
            {
              id: snap.id,
              full_name: snap.full_name || 'Instructor',
              email: snap.email || '',
              role: snapRole,
            },
          ]);
          this.formInstructorUserId = snap.id;
        }
      }
    } finally {
      this.cdr.detectChanges();
    }
  }

  async loadDepartments(): Promise<void> {
    try {
      const list = await this.learningService.getDepartments();
      const active = (Array.isArray(list) ? list : []).filter(d => {
        if (!d.is_active) return false;
        const norm = (d.name || '').trim().toLowerCase();
        return norm !== 'all / common' && norm !== 'all/common' && norm !== 'common';
      });
      this.departments.set(active);
      if (active.length > 0 && !this.formDepartmentId) {
        this.formDepartmentId = active[0].id;
      }
    } catch (err) {
      console.warn('Could not load active departments:', err);
    }
  }

  async loadSessions(): Promise<void> {
    this.loading.set(true);
    this.errorMessage.set('');
    try {
      const res = await firstValueFrom(
        this.liveClassesService.listSessions(
          this.isStaff ? this.filterDepartmentId : undefined
        )
      );
      this.sessions.set(Array.isArray(res?.sessions) ? res.sessions : []);
      this.approvedDepartmentId.set(res?.approved_department_id ?? null);
      this.restrictedReason.set(res?.restricted_reason ?? null);
    } catch (err: any) {
      this.errorMessage.set(err?.error?.detail || 'Unable to load live class sessions.');
      this.sessions.set([]);
    } finally {
      this.loading.set(false);
      this.cdr.detectChanges();
    }
  }

  openScheduler(): void {
    this.errorMessage.set('');
    this.successMessage.set('');
    if (!this.hasAssignedDepartments) {
      this.errorMessage.set(
        'No departments have been assigned to your teacher account yet. A SuperAdmin must assign 1–4 departments before you can schedule live classes.'
      );
      this.cdr.detectChanges();
      return;
    }
    this.formTitle = '';
    this.formDescription = '';
    this.formMeetingUrl = '';
    this.formPlatform = 'Jitsi Meet';
    this.formDurationMinutes = 60;
    const soon = new Date(Date.now() + 60 * 60 * 1000);
    const pad = (n: number) => String(n).padStart(2, '0');
    this.formScheduledLocal = `${soon.getFullYear()}-${pad(soon.getMonth() + 1)}-${pad(soon.getDate())}T${pad(soon.getHours())}:${pad(soon.getMinutes())}`;
    if (!this.formDepartmentId && this.departments().length > 0) {
      this.formDepartmentId = this.departments()[0].id;
    }
    if (this.isStaff) {
      void this.loadAssignableHosts();
      if (!this.formInstructorUserId) {
        const selfId = this.currentUserSnapshot()?.id ?? null;
        this.formInstructorUserId = selfId ?? (this.assignableHosts()[0]?.id ?? null);
      }
    } else {
      this.formInstructorUserId = null;
    }
    this.showScheduleModal = true;
    this.cdr.detectChanges();
  }

  closeScheduler(): void {
    this.showScheduleModal = false;
    this.cdr.detectChanges();
  }

  async createSession(): Promise<void> {
    this.errorMessage.set('');
    this.successMessage.set('');

    if (!this.formDepartmentId) {
      this.errorMessage.set('Please select a target Department before scheduling a live class.');
      return;
    }
    if (!this.formTitle.trim() || this.formTitle.trim().length < 3) {
      this.errorMessage.set('Session title must be at least 3 characters.');
      return;
    }
    if (!this.formScheduledLocal) {
      this.errorMessage.set('Please specify a scheduled date and time.');
      return;
    }
    if (!this.formMeetingUrl.trim()) {
      this.errorMessage.set('Please enter a valid video meeting link (e.g. https://...).');
      return;
    }

    const startDate = new Date(this.formScheduledLocal);
    if (isNaN(startDate.getTime())) {
      this.errorMessage.set('Scheduled start date/time is invalid.');
      return;
    }

    if (
      this.isStaff &&
      this.assignableHosts().length > 0 &&
      !this.formInstructorUserId
    ) {
      this.errorMessage.set('Please select a Teacher / Host for this live class.');
      return;
    }

    const payload: LiveClassCreatePayload = {
      title: this.formTitle.trim(),
      description: this.formDescription.trim() || null,
      department_id: Number(this.formDepartmentId),
      instructor_user_id: this.formInstructorUserId ?? null,
      scheduled_start: startDate.toISOString(),
      duration_minutes: Math.max(5, Math.min(480, Number(this.formDurationMinutes) || 60)),
      meeting_url: this.formMeetingUrl.trim(),
      platform: this.formPlatform || 'Video Call',
    };

    this.saving.set(true);
    try {
      const created = await firstValueFrom(this.liveClassesService.createSession(payload));
      this.showScheduleModal = false;
      this.successMessage.set(
        `Scheduled "${created.title}" (Instructor: ${created.instructor_name || 'Assigned Host'}) for ${created.department_name || 'Department #' + created.department_id}.`
      );
      await this.loadSessions();
    } catch (err: any) {
      this.errorMessage.set(err?.error?.detail || 'Failed to schedule live session.');
    } finally {
      this.saving.set(false);
      this.cdr.detectChanges();
    }
  }

  async updateStatus(session: LiveClassSession, status: LiveClassStatus): Promise<void> {
    try {
      await firstValueFrom(this.liveClassesService.updateSession(session.id, { status }));
      this.successMessage.set(`Updated "${session.title}" status to ${status.toUpperCase()}.`);
      await this.loadSessions();
    } catch (err: any) {
      this.errorMessage.set(err?.error?.detail || 'Unable to update session status.');
    }
  }

  async deleteSession(session: LiveClassSession): Promise<void> {
    if (!confirm(`Delete live session "${session.title}"?`)) return;
    try {
      await firstValueFrom(this.liveClassesService.deleteSession(session.id));
      this.successMessage.set(`Removed live session "${session.title}".`);
      await this.loadSessions();
    } catch (err: any) {
      this.errorMessage.set(err?.error?.detail || 'Unable to remove live session.');
    }
  }

  async joinSession(session: LiveClassSession): Promise<void> {
    this.errorMessage.set('');
    this.joiningId.set(session.id);
    try {
      const joinRes = await firstValueFrom(this.liveClassesService.joinSession(session.id));
      if (joinRes?.meeting_url) {
        window.open(joinRes.meeting_url, '_blank', 'noopener,noreferrer');
      }
    } catch (err: any) {
      this.errorMessage.set(
        err?.error?.detail || 'Access denied: unable to join this live session.'
      );
    } finally {
      this.joiningId.set(null);
      this.cdr.detectChanges();
    }
  }
}

