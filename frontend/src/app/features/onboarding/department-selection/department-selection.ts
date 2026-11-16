import {
  Component,
  OnInit,
  computed,
  inject,
  signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';

import {
  Department,
  LearningService
} from '../../../core/services/learning.service';
import {
  NavigationPermissions,
  OnboardingService
} from '../../../core/services/onboarding.service';

@Component({
  selector: 'app-department-selection',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './department-selection.html',
  styleUrl: './department-selection.scss'
})
export class DepartmentSelection implements OnInit {
  private readonly onboardingService = inject(OnboardingService);
  private readonly learningService = inject(LearningService);
  private readonly router = inject(Router);

  readonly loading = signal(true);
  readonly submitting = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');

  readonly permissions = signal<NavigationPermissions | null>(null);
  readonly departments = signal<Department[]>([]);
  readonly selectedDeptId = signal<number | null>(null);
  notes = '';

  readonly selectableDepartments = computed(() =>
    this.departments().filter(
      d =>
        d.is_active &&
        !['all / common', 'all/common', 'common'].includes(
          d.name.trim().toLowerCase()
        )
    )
  );

  readonly isActivated = computed(
    () => Boolean(this.permissions()?.is_activated_by_admin)
  );
  readonly isPendingApproval = computed(
    () =>
      this.permissions()?.onboarding_stage === 'department_pending_approval'
  );
  readonly isUnlocked = computed(
    () => Boolean(this.permissions()?.is_unlocked)
  );

  async ngOnInit(): Promise<void> {
    await this.loadData();
  }

  async loadData(forcePermissions = true): Promise<void> {
    this.loading.set(true);
    this.errorMessage.set('');

    try {
      const [perms, depts] = await Promise.all([
        this.onboardingService.getPermissions(forcePermissions),
        this.learningService.getDepartments()
      ]);

      this.permissions.set(perms);
      this.departments.set(depts);

      if (perms.is_unlocked) {
        await this.router.navigateByUrl('/dashboard');
        return;
      }

      if (perms.selected_department_id) {
        const parsed = Number(perms.selected_department_id);
        if (!Number.isNaN(parsed) && parsed > 0) {
          this.selectedDeptId.set(parsed);
        }
      }
    } catch (err: unknown) {
      this.errorMessage.set(this.extractError(err, 'Unable to load department selection options.'));
    } finally {
      this.loading.set(false);
    }
  }

  chooseDepartment(deptId: number): void {
    this.selectedDeptId.set(deptId);
    this.errorMessage.set('');
  }

  async submitChoice(): Promise<void> {
    const deptId = this.selectedDeptId();
    if (!deptId || this.submitting()) {
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    try {
      const updated = await this.onboardingService.selectMyDepartment(
        deptId,
        this.notes.trim() || null
      );
      const perms = await this.onboardingService.getPermissions(true);
      this.permissions.set(perms);
      const deptLabel =
        updated.selected_department_name ||
        perms.selected_department_name ||
        'selected department';
      this.successMessage.set(
        `Your preference (${deptLabel}) has been submitted for Administrator approval.`
      );
    } catch (err: unknown) {
      this.errorMessage.set(
        this.extractError(err, 'Could not submit department selection.')
      );
    } finally {
      this.submitting.set(false);
    }
  }

  private extractError(error: unknown, fallback: string): string {
    if (error instanceof HttpErrorResponse) {
      return error.error?.detail || fallback;
    }
    return error instanceof Error ? error.message : fallback;
  }
}
