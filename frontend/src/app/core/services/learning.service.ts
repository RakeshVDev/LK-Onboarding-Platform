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

export interface DepartmentMemberItem {
  id: number;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface DepartmentMembersResponse {
  department_id: number;
  department_name: string;
  teachers: DepartmentMemberItem[];
  students: DepartmentMemberItem[];
}

export interface Course {
  id: number;
  department_id: number;
  department_name?: string | null;
  title: string;
  description: string | null;
  is_published: boolean;
}

export interface StudentDepartmentRequest {
  id: number;
  user_id: number;
  user_name?: string | null;
  user_email?: string | null;
  department_id: number;
  department_name?: string | null;
  status: 'pending' | 'approved' | 'rejected' | 'superseded';
  notes?: string | null;
  reviewed_by_user_id?: number | null;
  reviewed_by_name?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
  current_approved_department_id?: number | null;
  current_approved_department_name?: string | null;
  is_change_request?: boolean;
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
  material_type: 'pdf' | 'link' | 'doc' | 'video' | 'notes';
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

export interface DeletionRequest {
  id: number;
  department_id: number;
  department_name: string;
  course_id?: number | null;
  target_type: string;
  initiated_by_user_id: number;
  initiated_by_name?: string | null;
  approved_by_user_ids: number[];
  approved_by_names: string[];
  required_superadmin_ids: number[];
  pending_superadmin_names: string[];
  approved_count: number;
  required_count: number;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface CourseDeletionActionResponse {
  status: 'deleted' | 'pending_approval';
  department_id: number;
  course_id?: number | null;
  message: string;
  request?: DeletionRequest | null;
}

export interface SendMaterialToBatchesResponse {
  material_id: number;
  course_id: number;
  delivered_cohort_ids: number[];
  delivered_batch_names: string[];
  total_deliveries: number;
}

export interface CohortTeacherInfo {
  id: number;
  full_name: string;
  email: string;
}

export interface BackendCohort {
  id: number;
  department_id: number;
  department_name?: string | null;
  course_id?: number | null;
  name: string;
  start_date?: string | null;
  end_date?: string | null;
  status: string;
  teacher_ids: number[];
  teachers: CohortTeacherInfo[];
  member_ids: number[];
  learner_count: number;
  material_count: number;
}

export interface CohortCandidateUser {
  id: number;
  full_name: string;
  email: string;
  assigned_department_ids: number[];
}

export interface CohortDepartmentCandidates {
  department_id: number;
  learners: CohortCandidateUser[];
  teachers: CohortCandidateUser[];
}

export interface CohortDeliveredMaterial {
  id: number;
  cohort_id: number;
  course_id: number;
  material_id: number;
  title: string;
  material_type: string;
  storage_key: string;
  source_department_name?: string | null;
  sent_by_user_id: number;
  sent_by_name?: string | null;
  sent_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class LearningService {
  private readonly apiUrl = '/training-api/api/v1';

  constructor(
    private readonly http: HttpClient,
    private readonly authService: AuthService
  ) { }

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

  getDepartmentMembers(departmentId: number): Promise<DepartmentMembersResponse> {
    return firstValueFrom(
      this.http.get<DepartmentMembersResponse>(
        `${this.apiUrl}/departments/${departmentId}/members`,
        { headers: this.getHeaders() }
      )
    );
  }

  createDepartment(payload: { name: string; description?: string | null }): Promise<Department> {
    return firstValueFrom(
      this.http.post<Department>(
        `${this.apiUrl}/departments`,
        payload,
        { headers: this.getHeaders() }
      )
    );
  }

  updateDepartment(
    departmentId: number,
    payload: { name?: string | null; description?: string | null; is_active?: boolean }
  ): Promise<Department> {
    return firstValueFrom(
      this.http.patch<Department>(
        `${this.apiUrl}/departments/${departmentId}`,
        payload,
        { headers: this.getHeaders() }
      )
    );
  }

  deleteDepartment(departmentId: number): Promise<CourseDeletionActionResponse> {
    return firstValueFrom(
      this.http.delete<CourseDeletionActionResponse>(
        `${this.apiUrl}/departments/${departmentId}`,
        { headers: this.getHeaders() }
      )
    );
  }

  getDeletionRequests(status = 'pending'): Promise<DeletionRequest[]> {
    let params = new HttpParams();
    if (status) {
      params = params.set('status', status);
    }
    return firstValueFrom(
      this.http.get<DeletionRequest[]>(
        `${this.apiUrl}/departments/deletion-requests`,
        { headers: this.getHeaders(), params }
      )
    );
  }

  approveDeletionRequest(requestId: number): Promise<CourseDeletionActionResponse> {
    return firstValueFrom(
      this.http.post<CourseDeletionActionResponse>(
        `${this.apiUrl}/departments/deletion-requests/${requestId}/approve`,
        {},
        { headers: this.getHeaders() }
      )
    );
  }

  rejectDeletionRequest(requestId: number): Promise<DeletionRequest> {
    return firstValueFrom(
      this.http.post<DeletionRequest>(
        `${this.apiUrl}/departments/deletion-requests/${requestId}/reject`,
        {},
        { headers: this.getHeaders() }
      )
    );
  }

  // ---------- STUDENT DEPARTMENT ALLOCATION REQUESTS ----------

  getMyDepartmentRequest(): Promise<StudentDepartmentRequest | null> {
    return firstValueFrom(
      this.http.get<StudentDepartmentRequest | null>(
        `${this.apiUrl}/departments/my-request`,
        { headers: this.getHeaders() }
      )
    );
  }

  submitDepartmentRequest(departmentId: number, notes?: string): Promise<StudentDepartmentRequest> {
    return firstValueFrom(
      this.http.post<StudentDepartmentRequest>(
        `${this.apiUrl}/departments/my-request`,
        { department_id: departmentId, notes: notes || null },
        { headers: this.getHeaders() }
      )
    );
  }

  getDepartmentRequests(statusFilter?: string): Promise<StudentDepartmentRequest[]> {
    let params = new HttpParams();
    if (statusFilter) {
      params = params.set('status', statusFilter);
    }
    return firstValueFrom(
      this.http.get<StudentDepartmentRequest[]>(
        `${this.apiUrl}/departments/requests`,
        { headers: this.getHeaders(), params }
      )
    );
  }

  reviewDepartmentRequest(
    requestId: number,
    payload: { status: 'approved' | 'rejected'; department_id?: number; notes?: string }
  ): Promise<StudentDepartmentRequest> {
    return firstValueFrom(
      this.http.post<StudentDepartmentRequest>(
        `${this.apiUrl}/departments/requests/${requestId}/review`,
        payload,
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

  deleteCourse(courseId: number): Promise<CourseDeletionActionResponse> {
    return firstValueFrom(
      this.http.delete<CourseDeletionActionResponse>(
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
    materialType: 'link' | 'video' | 'doc' | 'pdf' | 'notes',
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

  getDeliveredMaterials(courseId: number): Promise<LearningMaterial[]> {
    return firstValueFrom(
      this.http.get<LearningMaterial[]>(
        `${this.apiUrl}/courses/${courseId}/delivered-materials`,
        { headers: this.getHeaders() }
      )
    );
  }

  sendMaterialToBatches(
    courseId: number,
    materialId: number,
    cohortIds: number[]
  ): Promise<SendMaterialToBatchesResponse> {
    return firstValueFrom(
      this.http.post<SendMaterialToBatchesResponse>(
        `${this.apiUrl}/courses/${courseId}/materials/${materialId}/send-to-batches`,
        { cohort_ids: cohortIds },
        { headers: this.getHeaders() }
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

  fetchMaterialFileBlob(courseId: number, materialId: number, inline = false): Promise<Blob> {
    const query = inline ? '?inline=true' : '';
    return firstValueFrom(
      this.http.get(
        `${this.apiUrl}/courses/${courseId}/materials/${materialId}/file${query}`,
        { headers: this.getHeaders(), responseType: 'blob' }
      )
    );
  }

  // ---------- COHORTS ----------

  getCohorts(departmentId?: number): Promise<BackendCohort[]> {
    let params = new HttpParams();
    if (departmentId) {
      params = params.set('department_id', departmentId.toString());
    }

    return firstValueFrom(
      this.http.get<BackendCohort[]>(
        `${this.apiUrl}/cohorts`,
        { headers: this.getHeaders(), params }
      )
    );
  }

  getCohortCandidates(departmentId: number): Promise<CohortDepartmentCandidates> {
    return firstValueFrom(
      this.http.get<CohortDepartmentCandidates>(
        `${this.apiUrl}/cohorts/department-candidates`,
        {
          headers: this.getHeaders(),
          params: new HttpParams().set('department_id', departmentId.toString())
        }
      )
    );
  }

  createCohort(payload: {
    department_id: number;
    name: string;
    start_date?: string | null;
    end_date?: string | null;
    status?: string;
    teacher_ids: number[];
    excluded_learner_ids?: number[];
  }): Promise<BackendCohort> {
    return firstValueFrom(
      this.http.post<BackendCohort>(
        `${this.apiUrl}/cohorts`,
        payload,
        { headers: this.getHeaders() }
      )
    );
  }

  updateCohort(cohortId: number, payload: Partial<Cohort>): Promise<BackendCohort> {
    return firstValueFrom(
      this.http.patch<BackendCohort>(
        `${this.apiUrl}/cohorts/${cohortId}`,
        payload,
        { headers: this.getHeaders() }
      )
    );
  }

  updateCohortTeachers(cohortId: number, teacherIds: number[]): Promise<BackendCohort> {
    return firstValueFrom(
      this.http.put<BackendCohort>(
        `${this.apiUrl}/cohorts/${cohortId}/teachers`,
        { teacher_ids: teacherIds },
        { headers: this.getHeaders() }
      )
    );
  }

  endCohort(cohortId: number): Promise<{ status: string; cohort_id: number; name: string; message: string }> {
    return firstValueFrom(
      this.http.post<{ status: string; cohort_id: number; name: string; message: string }>(
        `${this.apiUrl}/cohorts/${cohortId}/end`,
        {},
        { headers: this.getHeaders() }
      )
    );
  }

  getCohortMaterials(cohortId: number): Promise<CohortDeliveredMaterial[]> {
    return firstValueFrom(
      this.http.get<CohortDeliveredMaterial[]>(
        `${this.apiUrl}/cohorts/${cohortId}/materials`,
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
        return 'Cannot connect to the Training API. Check that it is running on port 8002.';
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
