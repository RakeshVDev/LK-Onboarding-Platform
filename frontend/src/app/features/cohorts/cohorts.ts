import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { AuthService, CurrentUser } from '../../core/services/auth.service';
import {
  LearningService,
  Cohort,
  CohortMember,
  Department
} from '../../core/services/learning.service';
import { UserManagementService, ManagedUser } from '../../core/services/user-management.service';

@Component({
  selector: 'app-cohorts',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './cohorts.html',
  styleUrl: './cohorts.scss'
})
export class Cohorts implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly learningService = inject(LearningService);
  private readonly userService = inject(UserManagementService);

  readonly user = signal<CurrentUser | null>(null);
  readonly canManage = signal(false);

  readonly cohorts = signal<Cohort[]>([]);
  readonly departments = signal<Department[]>([]);
  readonly learners = signal<ManagedUser[]>([]);

  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');

  // Active modal: 'create' | 'edit' | 'members' | null
  readonly activeModal = signal<'create' | 'edit' | 'members' | null>(null);
  readonly selectedCohort = signal<Cohort | null>(null);

  // ---------- Cohort Form State ----------
  cohortName = '';
  cohortDeptId = 1;
  cohortStartDate = '';
  cohortEndDate = '';
  cohortStatus: 'active' | 'planned' | 'completed' = 'active';

  // ---------- Cohort Members State ----------
  readonly members = signal<CohortMember[]>([]);
  readonly membersLoading = signal(false);
  addMemberUserId: number | null = null;
  addMemberStatus = 'active';

  ngOnInit(): void {
    const current = this.authService.getCurrentUserSnapshot();
    this.user.set(current);

    this.canManage.set(
      current?.role === 'superadmin' ||
      current?.role === 'admin' ||
      current?.role === 'teacher'
    );

    void this.loadInitialData();
  }

  async loadInitialData(): Promise<void> {
    this.loading.set(true);
    this.errorMessage.set('');

    try {
      const [cohortsList, deptsList, usersList] = await Promise.all([
        this.learningService.getCohorts(),
        this.learningService.getDepartments().catch(() => []),
        this.userService.listUsers().catch(() => [])
      ]);

      this.cohorts.set(cohortsList);
      this.departments.set(deptsList);
      this.learners.set(usersList.filter(u => u.role === 'learner'));

      if (deptsList.length > 0) {
        this.cohortDeptId = deptsList[0].id;
      }
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    } finally {
      this.loading.set(false);
    }
  }

  getDepartmentName(deptId: number): string {
    const dept = this.departments().find(d => d.id === deptId);
    return dept ? dept.name : `Dept #${deptId}`;
  }

  getUserName(userId: number): string {
    const found = this.learners().find(u => u.id === userId);
    return found ? `${found.full_name} (${found.email})` : `Learner #${userId}`;
  }

  // ----------------------------------
  // Create / Edit Cohort
  // ----------------------------------

  openCreateModal(): void {
    this.selectedCohort.set(null);
    this.cohortName = '';
    this.cohortStartDate = '';
    this.cohortEndDate = '';
    this.cohortStatus = 'active';
    if (this.departments().length > 0) {
      this.cohortDeptId = this.departments()[0].id;
    }
    this.errorMessage.set('');
    this.successMessage.set('');
    this.activeModal.set('create');
  }

  openEditModal(cohort: Cohort): void {
    this.selectedCohort.set(cohort);
    this.cohortName = cohort.name;
    this.cohortDeptId = cohort.department_id;
    this.cohortStartDate = cohort.start_date ? cohort.start_date.split('T')[0] : '';
    this.cohortEndDate = cohort.end_date ? cohort.end_date.split('T')[0] : '';
    this.cohortStatus = cohort.status;
    this.errorMessage.set('');
    this.successMessage.set('');
    this.activeModal.set('edit');
  }

  async saveCohort(): Promise<void> {
    if (!this.cohortName.trim()) {
      this.errorMessage.set('Cohort name is required.');
      return;
    }

    this.saving.set(true);
    this.errorMessage.set('');

    try {
      const payload = {
        name: this.cohortName.trim(),
        department_id: Number(this.cohortDeptId),
        start_date: this.cohortStartDate ? new Date(this.cohortStartDate).toISOString() : null,
        end_date: this.cohortEndDate ? new Date(this.cohortEndDate).toISOString() : null,
        status: this.cohortStatus
      };

      const existing = this.selectedCohort();
      if (existing) {
        const updated = await this.learningService.updateCohort(existing.id, payload);
        this.cohorts.update(list => list.map(c => c.id === updated.id ? updated : c));
        this.successMessage.set(`Cohort "${updated.name}" updated successfully!`);
      } else {
        const created = await this.learningService.createCohort(payload);
        this.cohorts.update(list => [created, ...list]);
        this.successMessage.set(`Cohort "${created.name}" created successfully!`);
      }
      this.closeModal();
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    } finally {
      this.saving.set(false);
    }
  }

  async deleteCohort(cohort: Cohort): Promise<void> {
    if (!confirm(`Are you sure you want to delete cohort "${cohort.name}"?`)) return;

    try {
      await this.learningService.deleteCohort(cohort.id);
      this.cohorts.update(list => list.filter(c => c.id !== cohort.id));
      this.successMessage.set(`Cohort "${cohort.name}" removed.`);
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    }
  }

  // ----------------------------------
  // Cohort Members Roster
  // ----------------------------------

  async openMembersModal(cohort: Cohort): Promise<void> {
    this.selectedCohort.set(cohort);
    this.members.set([]);
    this.addMemberUserId = null;
    this.addMemberStatus = 'active';
    this.errorMessage.set('');
    this.successMessage.set('');
    this.activeModal.set('members');
    this.membersLoading.set(true);

    try {
      const membersList = await this.learningService.getCohortMembers(cohort.id);
      this.members.set(membersList);
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    } finally {
      this.membersLoading.set(false);
    }
  }

  async addMember(): Promise<void> {
    const cohort = this.selectedCohort();
    if (!cohort || !this.addMemberUserId) {
      this.errorMessage.set('Please select a learner to add.');
      return;
    }

    this.saving.set(true);
    this.errorMessage.set('');

    try {
      const added = await this.learningService.addCohortMember(
        cohort.id,
        Number(this.addMemberUserId),
        this.addMemberStatus
      );

      this.members.update(list => {
        const idx = list.findIndex(m => m.user_id === added.user_id);
        if (idx >= 0) {
          const copy = [...list];
          copy[idx] = added;
          return copy;
        }
        return [added, ...list];
      });

      this.successMessage.set('Learner added to cohort successfully.');
      this.addMemberUserId = null;
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    } finally {
      this.saving.set(false);
    }
  }

  async removeMember(userId: number): Promise<void> {
    const cohort = this.selectedCohort();
    if (!cohort || !confirm('Remove this learner from the cohort?')) return;

    try {
      await this.learningService.removeCohortMember(cohort.id, userId);
      this.members.update(list => list.filter(m => m.user_id !== userId));
      this.successMessage.set('Learner removed from cohort.');
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    }
  }

  closeModal(): void {
    this.activeModal.set(null);
    this.selectedCohort.set(null);
    this.errorMessage.set('');
    this.successMessage.set('');
  }
}
