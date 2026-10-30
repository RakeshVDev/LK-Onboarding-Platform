
import { Injectable } from '@angular/core';
import {
  HttpClient,
  HttpHeaders,
  HttpErrorResponse
} from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from './auth.service';

export interface SyllabusItem {
  id: number;
  course_id: number;
  title: string;
  description: string | null;
  sequence_order: number;
}

export interface SyllabusCreate {
  title: string;
  description?: string | null;
  sequence_order: number;
}

export interface Enrollment {
  id: number;
  course_id: number;
  user_id: number;
  status: string;
}

@Injectable({
  providedIn: 'root'
})
export class LearningService {
  private readonly apiUrl = '/training-api/api/v1';

  constructor(
    private readonly http: HttpClient,
    private readonly authService: AuthService
  ) {}

  private getHeaders(): HttpHeaders {
    const token = this.authService.getToken();

    if (!token) {
      throw new Error('Please log in to continue.');
    }

    return new HttpHeaders({
      Authorization: `Bearer ${token}`
    });
  }

  // ---------- COURSE SYLLABUS ----------

  getSyllabus(courseId: number): Promise<SyllabusItem[]> {
    return firstValueFrom(
      this.http.get<SyllabusItem[]>(
        `${this.apiUrl}/courses/${courseId}/syllabus`,
        { headers: this.getHeaders() }
      )
    );
  }

  createSyllabus(
    courseId: number,
    payload: SyllabusCreate
  ): Promise<SyllabusItem> {
    return firstValueFrom(
      this.http.post<SyllabusItem>(
        `${this.apiUrl}/courses/${courseId}/syllabus`,
        payload,
        { headers: this.getHeaders() }
      )
    );
  }

  updateSyllabus(
    courseId: number,
    itemId: number,
    payload: Partial<SyllabusCreate>
  ): Promise<SyllabusItem> {
    return firstValueFrom(
      this.http.patch<SyllabusItem>(
        `${this.apiUrl}/courses/${courseId}/syllabus/${itemId}`,
        payload,
        { headers: this.getHeaders() }
      )
    );
  }

  deleteSyllabus(courseId: number, itemId: number): Promise<void> {
    return firstValueFrom(
      this.http.delete<void>(
        `${this.apiUrl}/courses/${courseId}/syllabus/${itemId}`,
        { headers: this.getHeaders() }
      )
    );
  }

  // ---------- COURSE ENROLMENTS ----------

  getEnrolments(courseId: number): Promise<Enrollment[]> {
    return firstValueFrom(
      this.http.get<Enrollment[]>(
        `${this.apiUrl}/courses/${courseId}/enrolments`,
        { headers: this.getHeaders() }
      )
    );
  }

  enrolUser(courseId: number, userId: number): Promise<Enrollment> {
    return firstValueFrom(
      this.http.post<Enrollment>(
        `${this.apiUrl}/courses/${courseId}/enrolments`,
        { user_id: userId },
        { headers: this.getHeaders() }
      )
    );
  }

  updateEnrolmentStatus(
    courseId: number,
    enrolmentId: number,
    status: 'enrolled' | 'completed' | 'withdrawn'
  ): Promise<Enrollment> {
    return firstValueFrom(
      this.http.patch<Enrollment>(
        `${this.apiUrl}/courses/${courseId}/enrolments/${enrolmentId}`,
        { status },
        { headers: this.getHeaders() }
      )
    );
  }

  getErrorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      if (error.status === 0) {
        return 'Cannot connect to the Training API. Check that it is running on port 8001.';
      }

      if (error.status === 401) {
        return 'Your session has expired. Please log in again.';
      }

      if (error.status === 403) {
        return 'You do not have permission to perform this action.';
      }

      return error.error?.detail || 'The operation failed. Please try again.';
    }

    return error instanceof Error
      ? error.message
      : 'An unexpected error occurred.';
  }
}
