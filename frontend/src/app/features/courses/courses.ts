import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { AuthService, CurrentUser } from '../../core/services/auth.service';
import {
  LearningService,
  Course,
  Department,
  SyllabusItem,
  LearningMaterial
} from '../../core/services/learning.service';

@Component({
  selector: 'app-courses',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './courses.html',
  styleUrl: './courses.scss'
})
export class Courses implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly learningService = inject(LearningService);

  readonly user = signal<CurrentUser | null>(null);
  readonly canManage = signal(false);

  readonly courses = signal<Course[]>([]);
  readonly departments = signal<Department[]>([]);
  readonly selectedCourse = signal<Course | null>(null);

  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');

  // Active sub-view or modal: 'syllabus' | 'materials' | 'create' | null
  readonly activeModal = signal<'syllabus' | 'materials' | 'create' | null>(null);

  // ---------- Syllabus State ----------
  readonly syllabus = signal<SyllabusItem[]>([]);
  readonly syllabusLoading = signal(false);
  syllabusTitle = '';
  syllabusDesc = '';
  syllabusOrder = 1;

  // ---------- Learning Materials State (PDF & Links) ----------
  readonly materials = signal<LearningMaterial[]>([]);
  readonly materialsLoading = signal(false);
  materialTitle = '';
  materialType: 'pdf' | 'link' | 'video' | 'doc' = 'pdf';
  materialUrl = '';
  selectedFile: File | null = null;
  isUploadingFile = signal(false);

  // ---------- Create Course State ----------
  newCourseTitle = '';
  newCourseDeptId = 1;
  newCourseDesc = '';
  newCoursePublished = true;

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
      const [courses, depts] = await Promise.all([
        this.learningService.getCourses(),
        this.learningService.getDepartments().catch(() => [])
      ]);
      this.courses.set(courses);
      this.departments.set(depts);
      if (depts.length > 0) {
        this.newCourseDeptId = depts[0].id;
      }
    } catch (err: any) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    } finally {
      this.loading.set(false);
    }
  }

  getDepartmentName(deptId: number): string {
    const dept = this.departments().find(d => d.id === deptId);
    return dept ? dept.name : `Department #${deptId}`;
  }

  // ----------------------------------
  // Create Course
  // ----------------------------------

  openCreateModal(): void {
    this.newCourseTitle = '';
    this.newCourseDesc = '';
    this.newCoursePublished = true;
    if (this.departments().length > 0) {
      this.newCourseDeptId = this.departments()[0].id;
    }
    this.errorMessage.set('');
    this.successMessage.set('');
    this.activeModal.set('create');
  }

  async createCourse(): Promise<void> {
    if (!this.newCourseTitle.trim()) {
      this.errorMessage.set('Course title is required.');
      return;
    }

    this.saving.set(true);
    this.errorMessage.set('');

    try {
      const created = await this.learningService.createCourse({
        title: this.newCourseTitle.trim(),
        department_id: Number(this.newCourseDeptId),
        description: this.newCourseDesc.trim() || undefined,
        is_published: this.newCoursePublished
      });

      this.courses.update(list => [created, ...list]);
      this.successMessage.set(`Course "${created.title}" created successfully!`);
      this.closeModal();
    } catch (err: any) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    } finally {
      this.saving.set(false);
    }
  }

  // ----------------------------------
  // Course Syllabus Management
  // ----------------------------------

  async openSyllabus(course: Course): Promise<void> {
    this.selectedCourse.set(course);
    this.syllabus.set([]);
    this.syllabusTitle = '';
    this.syllabusDesc = '';
    this.syllabusOrder = 1;
    this.errorMessage.set('');
    this.successMessage.set('');
    this.activeModal.set('syllabus');
    this.syllabusLoading.set(true);

    try {
      const items = await this.learningService.getSyllabus(course.id);
      this.syllabus.set(items);
      this.syllabusOrder = items.length + 1;
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    } finally {
      this.syllabusLoading.set(false);
    }
  }

  async addSyllabusItem(): Promise<void> {
    const course = this.selectedCourse();
    if (!course || !this.syllabusTitle.trim()) {
      this.errorMessage.set('Please provide a lesson title.');
      return;
    }

    this.saving.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    try {
      const item = await this.learningService.createSyllabus(course.id, {
        title: this.syllabusTitle.trim(),
        description: this.syllabusDesc.trim() || null,
        sequence_order: Number(this.syllabusOrder)
      });

      this.syllabus.update(items =>
        [...items, item].sort((a, b) => a.sequence_order - b.sequence_order)
      );

      this.syllabusTitle = '';
      this.syllabusDesc = '';
      this.syllabusOrder = this.syllabus().length + 1;
      this.successMessage.set('Syllabus module added.');
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    } finally {
      this.saving.set(false);
    }
  }

  async deleteSyllabusItem(item: SyllabusItem): Promise<void> {
    const course = this.selectedCourse();
    if (!course || !confirm(`Delete lesson "${item.title}"?`)) return;

    try {
      await this.learningService.deleteSyllabus(course.id, item.id);
      this.syllabus.update(items => items.filter(x => x.id !== item.id));
      this.successMessage.set('Syllabus item removed.');
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    }
  }

  // ----------------------------------
  // Learning Materials (PDF Uploads & Resource Links)
  // ----------------------------------

  async openMaterials(course: Course): Promise<void> {
    this.selectedCourse.set(course);
    this.materials.set([]);
    this.materialTitle = '';
    this.materialType = 'pdf';
    this.materialUrl = '';
    this.selectedFile = null;
    this.errorMessage.set('');
    this.successMessage.set('');
    this.activeModal.set('materials');
    this.materialsLoading.set(true);

    try {
      const list = await this.learningService.getMaterials(course.id);
      this.materials.set(list);
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    } finally {
      this.materialsLoading.set(false);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
      if (!this.materialTitle.trim()) {
        this.materialTitle = this.selectedFile.name.replace(/\.[^/.]+$/, '');
      }
    }
  }

  async uploadPdfResource(): Promise<void> {
    const course = this.selectedCourse();
    if (!course) return;

    if (!this.selectedFile) {
      this.errorMessage.set('Please select a PDF or document file to upload.');
      return;
    }

    this.isUploadingFile.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    try {
      const created = await this.learningService.uploadMaterialFile(
        course.id,
        this.materialTitle.trim() || this.selectedFile.name,
        this.selectedFile
      );

      this.materials.update(list => [created, ...list]);
      this.successMessage.set(`PDF "${created.title}" uploaded successfully!`);
      this.selectedFile = null;
      this.materialTitle = '';
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    } finally {
      this.isUploadingFile.set(false);
    }
  }

  async addLinkResource(): Promise<void> {
    const course = this.selectedCourse();
    if (!course) return;

    if (!this.materialTitle.trim()) {
      this.errorMessage.set('Resource title is required.');
      return;
    }

    if (!this.materialUrl.trim()) {
      this.errorMessage.set('Resource URL link is required.');
      return;
    }

    this.saving.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    try {
      const created = await this.learningService.addMaterialLink(
        course.id,
        this.materialTitle.trim(),
        this.materialType,
        this.materialUrl.trim()
      );

      this.materials.update(list => [created, ...list]);
      this.successMessage.set(`Resource link "${created.title}" added.`);
      this.materialTitle = '';
      this.materialUrl = '';
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    } finally {
      this.saving.set(false);
    }
  }

  async deleteMaterial(material: LearningMaterial): Promise<void> {
    const course = this.selectedCourse();
    if (!course || !confirm(`Delete resource "${material.title}"?`)) return;

    try {
      await this.learningService.deleteMaterial(course.id, material.id);
      this.materials.update(list => list.filter(m => m.id !== material.id));
      this.successMessage.set('Resource deleted successfully.');
    } catch (err) {
      this.errorMessage.set(this.learningService.getErrorMessage(err));
    }
  }

  openResource(material: LearningMaterial): void {
    if (material.material_type === 'pdf' || material.material_type === 'doc') {
      const course = this.selectedCourse();
      if (!course) return;
      const downloadUrl = `/training-api/api/v1/courses/${course.id}/materials/${material.id}/file`;
      window.open(downloadUrl, '_blank');
    } else {
      let target = material.storage_key;
      if (!target.startsWith('http://') && !target.startsWith('https://')) {
        target = 'https://' + target;
      }
      window.open(target, '_blank');
    }
  }

  closeModal(): void {
    this.activeModal.set(null);
    this.selectedCourse.set(null);
    this.errorMessage.set('');
    this.successMessage.set('');
  }
}
