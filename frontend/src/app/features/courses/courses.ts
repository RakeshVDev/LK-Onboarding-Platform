
import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders, HttpErrorResponse } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/services/auth.service';
import {
  LearningService,
  SyllabusItem
} from '../../core/services/learning.service';

interface Course {
  id: number;
  department_id: number;
  title: string;
  description: string | null;
  is_published: boolean;
}

@Component({
  selector: 'app-courses',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './courses.html',
  styleUrl: './courses.scss'
})
export class Courses implements OnInit {
  readonly courses = signal<Course[]>([]);
  readonly syllabus = signal<SyllabusItem[]>([]);
  readonly selectedCourse = signal<Course | null>(null);
  readonly loading = signal(false);
  readonly syllabusLoading = signal(false);
  readonly saving = signal(false);
  readonly errorMessage = signal('');
  readonly successMessage = signal('');

  readonly canManage = signal(false);

  title = '';
  description = '';
  sequenceOrder = 1;

  private readonly coursesUrl = '/training-api/api/v1/courses';

  constructor(
    private readonly http: HttpClient,
    private readonly authService: AuthService,
    private readonly learningService: LearningService
  ) {}

  ngOnInit(): void {
    const user = this.authService.getCurrentUserSnapshot();

    this.canManage.set(
      user?.role === 'superadmin' || user?.role === 'admin'
    );

    void this.loadCourses();
  }

  private getHeaders(): HttpHeaders {
    const token = this.authService.getToken();

    if (!token) {
      throw new Error('Please log in to continue.');
    }

    return new HttpHeaders({
      Authorization: `Bearer ${token}`
    });
  }

  async loadCourses(): Promise<void> {
    this.loading.set(true);
    this.errorMessage.set('');

    try {
      const response = await firstValueFrom(
        this.http.get<Course[]>(this.coursesUrl, {
          headers: this.getHeaders()
        })
      );

      this.courses.set(response);
    } catch (error) {
      this.errorMessage.set(this.getErrorMessage(error));
    } finally {
      this.loading.set(false);
    }
  }

  async openSyllabus(course: Course): Promise<void> {
    this.selectedCourse.set(course);
    this.syllabus.set([]);
    this.title = '';
    this.description = '';
    this.sequenceOrder = 1;
    this.errorMessage.set('');
    this.successMessage.set('');
    this.syllabusLoading.set(true);

    try {
      const items = await this.learningService.getSyllabus(course.id);
      this.syllabus.set(items);
    } catch (error) {
      this.errorMessage.set(this.getErrorMessage(error));
    } finally {
      this.syllabusLoading.set(false);
    }
  }

  async addSyllabusItem(): Promise<void> {
    const course = this.selectedCourse();

    if (!course || !this.title.trim()) {
      this.errorMessage.set('Please enter a syllabus title.');
      return;
    }

    this.saving.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    try {
      const item = await this.learningService.createSyllabus(course.id, {
        title: this.title.trim(),
        description: this.description.trim() || null,
        sequence_order: Number(this.sequenceOrder)
      });

      this.syllabus.update(items =>
        [...items, item].sort(
          (a, b) =>
            a.sequence_order - b.sequence_order || a.id - b.id
        )
      );

      this.title = '';
      this.description = '';
      this.sequenceOrder = this.syllabus().length + 1;
      this.successMessage.set('Syllabus item added successfully.');
    } catch (error) {
      this.errorMessage.set(this.getErrorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  async deleteSyllabusItem(item: SyllabusItem): Promise<void> {
    const course = this.selectedCourse();

    if (!course || !confirm(`Delete "${item.title}"?`)) {
      return;
    }

    this.errorMessage.set('');
    this.successMessage.set('');

    try {
      await this.learningService.deleteSyllabus(course.id, item.id);

      this.syllabus.update(items =>
        items.filter(existing => existing.id !== item.id)
      );

      this.successMessage.set('Syllabus item deleted successfully.');
    } catch (error) {
      this.errorMessage.set(this.getErrorMessage(error));
    }
  }

  closeSyllabus(): void {
    this.selectedCourse.set(null);
    this.syllabus.set([]);
    this.errorMessage.set('');
    this.successMessage.set('');
  }

  private getErrorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      if (error.status === 0) {
        return 'Cannot connect to the backend. Check that both APIs are running.';
      }

      if (error.status === 401) {
        return 'Your session has expired. Please log in again.';
      }

      if (error.status === 403) {
        return error.error?.detail ||
          'You do not have permission to perform this action.';
      }

      return error.error?.detail || 'The request failed.';
    }

    return error instanceof Error
      ? error.message
      : 'An unexpected error occurred.';
  }
}
