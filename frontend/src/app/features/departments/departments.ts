import {
  Component,
  OnInit,
  ChangeDetectorRef,
  inject
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
  FormsModule
} from '@angular/forms';

import {
  DeletionRequest,
  LearningService,
  Department,
  StudentDepartmentRequest
} from '../../core/services/learning.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-departments',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule],
  templateUrl: './departments.html',
  styleUrl: './departments.scss'
})
export class Departments implements OnInit {
  private readonly learningService = inject(LearningService);
  readonly authService = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly cdr = inject(ChangeDetectorRef);

  departments: Department[] = [];
  loading = false;
  saving = false;
  deletingId: number | null = null;
  errorMessage = '';
  successMessage = '';
  searchQuery = '';

  // SuperAdmin Course/Dept deletion consensus state
  isSuperAdmin = false;
  currentUserId = 0;
  deletionRequests: DeletionRequest[] = [];
  processingDeletionId: number | null = null;

  // Tab State: 'departments' | 'requests'
  activeTab: 'departments' | 'requests' = 'departments';

  // Requests state
  requests: StudentDepartmentRequest[] = [];
  loadingRequests = false;
  processingRequestId: number | null = null;
  requestStatusFilter: 'all' | 'pending' | 'approved' | 'rejected' = 'pending';
  reassignDeptMap: Record<number, number> = {};

  // Modal / Form state
  showModal = false;
  isEditing = false;
  editingId: number | null = null;

  form = this.fb.nonNullable.group({
    name: [
      '',
      [
        Validators.required,
        Validators.minLength(2),
        Validators.maxLength(150)
      ]
    ],
    description: ['']
  });

  ngOnInit(): void {
    this.isSuperAdmin = this.authService.hasRole('superadmin');
    this.currentUserId = this.authService.getCurrentUserSnapshot()?.id ?? 0;
    void this.loadDepartments();
    void this.loadRequests();
    if (this.isSuperAdmin) {
      void this.loadDeletionRequests();
    }
  }

  async loadDeletionRequests(): Promise<void> {
    if (!this.isSuperAdmin) return;
    try {
      this.deletionRequests = await this.learningService.getDeletionRequests('pending');
      this.cdr.detectChanges();
    } catch {
      // keep silent if unauthorized
    }
  }

  async loadDepartments(): Promise<void> {
    this.loading = true;
    this.errorMessage = '';
    this.cdr.detectChanges();

    try {
      this.departments = await this.learningService.getDepartments();
    } catch (err: any) {
      console.error('Failed to load departments:', err);
      this.errorMessage = err.error?.detail || 'Unable to retrieve departments.';
    } finally {
      this.loading = false;
      this.cdr.detectChanges();
    }
  }

  async loadRequests(): Promise<void> {
    this.loadingRequests = true;
    this.cdr.detectChanges();

    try {
      this.requests = await this.learningService.getDepartmentRequests();
      // Initialize reassign defaults
      for (const r of this.requests) {
        if (!this.reassignDeptMap[r.id]) {
          this.reassignDeptMap[r.id] = r.department_id;
        }
      }
    } catch (err) {
      console.warn('Could not load department requests:', err);
    } finally {
      this.loadingRequests = false;
      this.cdr.detectChanges();
    }
  }

  get pendingRequestsCount(): number {
    return this.requests.filter(r => r.status === 'pending').length;
  }

  get filteredRequests(): StudentDepartmentRequest[] {
    if (this.requestStatusFilter === 'all') {
      return this.requests;
    }
    return this.requests.filter(r => r.status === this.requestStatusFilter);
  }

  async approveRequest(req: StudentDepartmentRequest, targetDeptId?: number): Promise<void> {
    this.processingRequestId = req.id;
    this.errorMessage = '';
    this.successMessage = '';
    this.cdr.detectChanges();

    try {
      const deptIdToUse = targetDeptId || this.reassignDeptMap[req.id] || req.department_id;
      const updated = await this.learningService.reviewDepartmentRequest(req.id, {
        status: 'approved',
        department_id: deptIdToUse
      });
      const idx = this.requests.findIndex(r => r.id === req.id);
      if (idx !== -1) {
        this.requests[idx] = updated;
      }
      this.successMessage = `Approved joinee "${updated.user_name || 'Student'}" for ${updated.department_name || 'Department'}. Courses unlocked.`;
    } catch (err: any) {
      this.errorMessage = err.error?.detail || 'Failed to approve department request.';
    } finally {
      this.processingRequestId = null;
      this.cdr.detectChanges();
    }
  }

  async rejectRequest(req: StudentDepartmentRequest): Promise<void> {
    this.processingRequestId = req.id;
    this.errorMessage = '';
    this.successMessage = '';
    this.cdr.detectChanges();

    try {
      const updated = await this.learningService.reviewDepartmentRequest(req.id, {
        status: 'rejected'
      });
      const idx = this.requests.findIndex(r => r.id === req.id);
      if (idx !== -1) {
        this.requests[idx] = updated;
      }
      this.successMessage = `Rejected allocation request for "${updated.user_name || 'Student'}".`;
    } catch (err: any) {
      this.errorMessage = err.error?.detail || 'Failed to reject department request.';
    } finally {
      this.processingRequestId = null;
      this.cdr.detectChanges();
    }
  }

  get filteredDepartments(): Department[] {
    const q = this.searchQuery.trim().toLowerCase();
    if (!q) {
      return this.departments;
    }
    return this.departments.filter(d =>
      d.name.toLowerCase().includes(q) ||
      (d.description && d.description.toLowerCase().includes(q))
    );
  }

  get activeCount(): number {
    return this.departments.filter(d => d.is_active).length;
  }

  get inactiveCount(): number {
    return this.departments.filter(d => !d.is_active).length;
  }

  openCreateModal(): void {
    this.isEditing = false;
    this.editingId = null;
    this.errorMessage = '';
    this.successMessage = '';
    this.form.reset({
      name: '',
      description: ''
    });
    this.showModal = true;
    this.cdr.detectChanges();
  }

  openEditModal(dept: Department): void {
    this.isEditing = true;
    this.editingId = dept.id;
    this.errorMessage = '';
    this.successMessage = '';
    this.form.setValue({
      name: dept.name,
      description: dept.description ?? ''
    });
    this.showModal = true;
    this.cdr.detectChanges();
  }

  closeModal(): void {
    this.showModal = false;
    this.isEditing = false;
    this.editingId = null;
    this.cdr.detectChanges();
  }

  async saveDepartment(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.cdr.detectChanges();
      return;
    }

    const { name, description } = this.form.getRawValue();
    this.saving = true;
    this.errorMessage = '';
    this.successMessage = '';
    this.cdr.detectChanges();

    try {
      if (this.isEditing && this.editingId) {
        const updated = await this.learningService.updateDepartment(this.editingId, {
          name: name.trim(),
          description: description.trim() || null
        });
        const idx = this.departments.findIndex(d => d.id === this.editingId);
        if (idx !== -1) {
          this.departments[idx] = updated;
        }
        this.successMessage = `Department "${updated.name}" updated successfully.`;
      } else {
        const created = await this.learningService.createDepartment({
          name: name.trim(),
          description: description.trim() || null
        });
        this.departments.push(created);
        this.successMessage = `Department "${created.name}" created successfully.`;
      }
      this.closeModal();
    } catch (err: any) {
      console.error('Department save error:', err);
      this.errorMessage = err.error?.detail || 'Failed to save department. Ensure name is unique.';
    } finally {
      this.saving = false;
      this.cdr.detectChanges();
    }
  }

  async toggleStatus(dept: Department): Promise<void> {
    this.errorMessage = '';
    this.successMessage = '';
    this.cdr.detectChanges();

    try {
      const updated = await this.learningService.updateDepartment(dept.id, {
        is_active: !dept.is_active
      });
      dept.is_active = updated.is_active;
      this.successMessage = `Department "${dept.name}" ${dept.is_active ? 'activated' : 'deactivated'}.`;
    } catch (err: any) {
      console.error('Toggle status error:', err);
      this.errorMessage = err.error?.detail || 'Failed to update department status.';
    } finally {
      this.cdr.detectChanges();
    }
  }

  async deleteDepartment(dept: Department): Promise<void> {
    if (!this.isSuperAdmin) {
      return;
    }
    if (!confirm(`Deleting "${dept.name}" will delete BOTH this Department and its paired Course Vault (requires approval from all active SuperAdmins). Continue?`)) {
      return;
    }

    this.deletingId = dept.id;
    this.errorMessage = '';
    this.successMessage = '';
    this.cdr.detectChanges();

    try {
      const res = await this.learningService.deleteDepartment(dept.id);
      if (res.status === 'deleted') {
        this.departments = this.departments.filter(d => d.id !== dept.id);
        this.deletionRequests = this.deletionRequests.filter(r => r.department_id !== dept.id);
        this.successMessage = res.message || `Department "${dept.name}" and its paired Course deleted.`;
      } else {
        if (res.request) {
          this.deletionRequests = [
            res.request,
            ...this.deletionRequests.filter(r => r.id !== res.request!.id)
          ];
        }
        this.successMessage = res.message;
      }
    } catch (err: any) {
      console.error('Delete department error:', err);
      this.errorMessage = err.error?.detail || 'Cannot initiate department deletion.';
    } finally {
      this.deletingId = null;
      this.cdr.detectChanges();
    }
  }

  hasCurrentUserApprovedDeletion(req: DeletionRequest): boolean {
    if (!this.currentUserId) return false;
    return req.approved_by_user_ids.includes(this.currentUserId);
  }

  async approveDeletion(req: DeletionRequest): Promise<void> {
    if (!this.isSuperAdmin) return;
    this.processingDeletionId = req.id;
    this.errorMessage = '';
    this.successMessage = '';
    this.cdr.detectChanges();

    try {
      const res = await this.learningService.approveDeletionRequest(req.id);
      this.successMessage = res.message;
      await Promise.all([this.loadDepartments(), this.loadDeletionRequests()]);
    } catch (err: any) {
      this.errorMessage = err.error?.detail || 'Failed to approve deletion request.';
    } finally {
      this.processingDeletionId = null;
      this.cdr.detectChanges();
    }
  }

  async rejectDeletion(req: DeletionRequest): Promise<void> {
    if (!this.isSuperAdmin) return;
    this.processingDeletionId = req.id;
    this.errorMessage = '';
    this.successMessage = '';
    this.cdr.detectChanges();

    try {
      await this.learningService.rejectDeletionRequest(req.id);
      this.deletionRequests = this.deletionRequests.filter(r => r.id !== req.id);
      this.successMessage = `Deletion request for "${req.department_name}" was cancelled.`;
    } catch (err: any) {
      this.errorMessage = err.error?.detail || 'Failed to reject deletion request.';
    } finally {
      this.processingDeletionId = null;
      this.cdr.detectChanges();
    }
  }

  getDeptIcon(name: string): string {
    const lower = name.toLowerCase();
    if (lower.includes('php')) return '🐘';
    if (lower.includes('.net') || lower.includes('c#')) return '⚙';
    if (lower.includes('python')) return '🐍';
    if (lower.includes('java')) return '☕';
    if (lower.includes('data') || lower.includes('sql') || lower.includes('db')) return '🗄';
    if (lower.includes('all') || lower.includes('common')) return '🌐';
    if (lower.includes('qa') || lower.includes('test')) return '✓';
    return '🏢';
  }

  getDeptBadgeClass(name: string): string {
    const lower = name.toLowerCase();
    if (lower.includes('php')) return 'badge-php';
    if (lower.includes('.net')) return 'badge-dotnet';
    if (lower.includes('python')) return 'badge-python';
    if (lower.includes('java')) return 'badge-java';
    if (lower.includes('data') || lower.includes('db')) return 'badge-db';
    if (lower.includes('all') || lower.includes('common')) return 'badge-common';
    return 'badge-default';
  }
}
