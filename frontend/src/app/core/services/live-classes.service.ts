import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

export type LiveClassStatus = 'scheduled' | 'live' | 'completed' | 'cancelled';

export interface LiveClassSession {
  id: number;
  title: string;
  description?: string | null;
  department_id: number;
  department_name?: string | null;
  instructor_user_id: number;
  instructor_name?: string | null;
  scheduled_start: string;
  duration_minutes: number;
  meeting_url: string;
  platform: string;
  status: LiveClassStatus;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface LiveClassListResponse {
  sessions: LiveClassSession[];
  approved_department_id: number | null;
  restricted_reason: string | null;
}

export interface AssignableHost {
  id: number;
  full_name: string;
  email: string;
  role: string;
}

export interface LiveClassCreatePayload {
  title: string;
  description?: string | null;
  department_id: number;
  instructor_user_id?: number | null;
  scheduled_start: string;
  duration_minutes: number;
  meeting_url: string;
  platform: string;
}

export interface LiveClassUpdatePayload {
  title?: string;
  description?: string | null;
  department_id?: number;
  instructor_user_id?: number | null;
  scheduled_start?: string;
  duration_minutes?: number;
  meeting_url?: string;
  platform?: string;
  status?: LiveClassStatus;
}

export interface LiveClassJoinResponse {
  session_id: number;
  title: string;
  department_id: number;
  department_name?: string | null;
  meeting_url: string;
  platform: string;
  status: string;
}

@Injectable({ providedIn: 'root' })
export class LiveClassesService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/training-api/api/v1/live-classes';

  listSessions(departmentId?: number | null): Observable<LiveClassListResponse> {
    let params = new HttpParams();
    if (departmentId && departmentId > 0) {
      params = params.set('department_id', String(departmentId));
    }
    return this.http.get<LiveClassListResponse>(this.apiUrl, { params });
  }

  createSession(payload: LiveClassCreatePayload): Observable<LiveClassSession> {
    return this.http.post<LiveClassSession>(this.apiUrl, payload);
  }

  updateSession(
    sessionId: number,
    payload: LiveClassUpdatePayload
  ): Observable<LiveClassSession> {
    return this.http.patch<LiveClassSession>(
      `${this.apiUrl}/${sessionId}`,
      payload
    );
  }

  deleteSession(sessionId: number): Observable<{ status: string; session_id: number }> {
    return this.http.delete<{ status: string; session_id: number }>(
      `${this.apiUrl}/${sessionId}`
    );
  }

  joinSession(sessionId: number): Observable<LiveClassJoinResponse> {
    return this.http.post<LiveClassJoinResponse>(
      `${this.apiUrl}/${sessionId}/join`,
      {}
    );
  }

  getAssignableHosts(): Observable<AssignableHost[]> {
    return this.http.get<AssignableHost[]>(`${this.apiUrl}/assignable-hosts`);
  }
}

