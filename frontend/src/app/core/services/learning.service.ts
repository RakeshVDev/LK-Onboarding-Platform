import { Injectable } from '@angular/core';
import {
  HttpClient,
  HttpHeaders,
  HttpErrorResponse,
  HttpParams
} from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from './auth.service';

export interface Department {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface Course {
  id: number;
  department_id: number;
  title: string;
  description: string | null;
  is_published: boolean;
}

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

export interface LearningMaterial {
  id: number;
  course_id: number;
  title: string;
  material_type: 'pdf' | 'link' | 'doc' | 'video';
  storage_key: string;
  is_active: boolean;
}

export interface Cohort {
  id: number;
  department_id: number;
  name: string;
  start_date: string | null;
  end_date: string | null;
  status: 'planned' | 'active' | 'completed';
}

export interface CohortMember {
  id: number;
  cohort_id: number;
  user_id: number;
  joined_at: string;
  status: string;
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

  // ---------- DEPARTMENTS ----------

  getDepartments(): Promise<Department[]> {
    return firstValueFrom(
      this.http.get<Department[]>(
        `${this.apiUrl}/departments`,
        { headers: this.getHeaders() }
      )
    );
  }

  // ---------- COURSES ----------

  getCourses(departmentId?: number): Promise<Course[]> {
    let params = new HttpParams();
    if (departmentId) {
      params = params.set('department_id', departmentId.toString());
    }

    return firstValueFrom(
      this.http.get<Course[]>(
        `${this.apiUrl}/courses`,
        { headers: this.getHeaders(), params }
      )
    );
  }

  getCourse(courseId: number): Promise<Course> {
    return firstValueFrom(
      this.http.get<Course>(
        `${this.apiUrl}/courses/${courseId}`,
        { headers: this.getHeaders() }
      )
    );
  }

  createCourse(payload: {
    department_id: number;
    title: string;
    description?: string;
    is_published?: boolean;
  }): Promise<Course> {
    return firstValueFrom(
      this.http.post<Course>(
        `${this.apiUrl}/courses`,
        payload,
        { headers: this.getHeaders() }
      )
    );
  }

  updateCourse(courseId: number, payload: Partial<Course>): Promise<Course> {
    return firstValueFrom(
      this.http.patch<Course>(
        `${this.apiUrl}/courses/${courseId}`,
        payload,
        { headers: this.getHeaders() }
      )
    );
  }

  deleteCourse(courseId: number): Promise<void> {
    return firstValueFrom(
      this.http.delete<void>(
        `${this.apiUrl}/courses/${courseId}`,
        { headers: this.getHeaders() }
      )
    );
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

  // ---------- LEARNING MATERIALS (PDF UPLOADS & LINKS) ----------

  getMaterials(courseId: number): Promise<LearningMaterial[]> {
    return firstValueFrom(
      this.http.get<LearningMaterial[]>(
        `${this.apiUrl}/courses/${courseId}/materials`,
        { headers: this.getHeaders() }
      )
    );
  }

  addMaterialLink(
    courseId: number,
    title: string,
    materialType: 'link' | 'video' | 'doc' | 'pdf',
    storageKey: string
  ): Promise<LearningMaterial> {
    return firstValueFrom(
      this.http.post<LearningMaterial>(
        `${this.apiUrl}/courses/${courseId}/materials`,
        {
          title,
          material_type: materialType,
          storage_key: storageKey
        },
        { headers: this.getHeaders() }
      )
    );
  }

  uploadMaterialFile(
    courseId: number,
    title: string,
    file: File
  ): Promise<LearningMaterial> {
    const formData = new FormData();
    formData.append('title', title);
    formData.append('file', file);

    const token = this.authService.getToken();
    const headers = new HttpHeaders({
      Authorization: `Bearer ${token}`
    });

    return firstValueFrom(
      this.http.post<LearningMaterial>(
        `${this.apiUrl}/courses/${courseId}/materials/upload`,
        formData,
        { headers }
      )
    );
  }

  deleteMaterial(courseId: number, materialId: number): Promise<void> {
    return firstValueFrom(
      this.http.delete<void>(
        `${this.apiUrl}/courses/${courseId}/materials/${materialId}`,
        { headers: this.getHeaders() }
      )
    );
  }

  // ---------- COHORTS ----------

  getCohorts(departmentId?: number): Promise<Cohort[]> {
    let params = new HttpParams();
    if (departmentId) {
      params = params.set('department_id', departmentId.toString());
    }

    return firstValueFrom(
      this.http.get<Cohort[]>(
        `${this.apiUrl}/cohorts`,
        { headers: this.getHeaders(), params }
      )
    );
  }

  createCohort(payload: {
    department_id: number;
    name: string;
    start_date?: string | null;
    end_date?: string | null;
    status?: string;
  }): Promise<Cohort> {
    return firstValueFrom(
      this.http.post<Cohort>(
        `${this.apiUrl}/cohorts`,
        payload,
        { headers: this.getHeaders() }
      )
    );
  }

  updateCohort(cohortId: number, payload: Partial<Cohort>): Promise<Cohort> {
    return firstValueFrom(
      this.http.patch<Cohort>(
        `${this.apiUrl}/cohorts/${cohortId}`,
        payload,
        { headers: this.getHeaders() }
      )
    );
  }

  deleteCohort(cohortId: number): Promise<void> {
    return firstValueFrom(
      this.http.delete<void>(
        `${this.apiUrl}/cohorts/${cohortId}`,
        { headers: this.getHeaders() }
      )
    );
  }

  // ---------- COHORT MEMBERS ----------

  getCohortMembers(cohortId: number): Promise<CohortMember[]> {
    return firstValueFrom(
      this.http.get<CohortMember[]>(
        `${this.apiUrl}/cohorts/${cohortId}/members`,
        { headers: this.getHeaders() }
      )
    );
  }

  addCohortMember(cohortId: number, userId: number, status = 'active'): Promise<CohortMember> {
    return firstValueFrom(
      this.http.post<CohortMember>(
        `${this.apiUrl}/cohorts/${cohortId}/members`,
        { user_id: userId, status },
        { headers: this.getHeaders() }
      )
    );
  }

  removeCohortMember(cohortId: number, userId: number): Promise<void> {
    return firstValueFrom(
      this.http.delete<void>(
        `${this.apiUrl}/cohorts/${cohortId}/members/${userId}`,
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
