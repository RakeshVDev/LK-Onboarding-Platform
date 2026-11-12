
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export type AssessmentStatus =
  | 'not_started'
  | 'in_progress'
  | 'completed';

export interface LearnerAssessmentStatus {
  status: AssessmentStatus;
  session_id: number | null;
}

@Injectable({
  providedIn: 'root'
})
export class AssessmentStatusService {

  private readonly apiUrl =
    '/training-api/api/v1/assessments/my/status';

  private cachedStatus: LearnerAssessmentStatus | null = null;
  private cachedToken: string | null = null;
  private pendingPromise: Promise<LearnerAssessmentStatus> | null = null;

  constructor(private readonly http: HttpClient) {}

  async getStatus(force = false): Promise<LearnerAssessmentStatus> {
    const activeToken =
      typeof sessionStorage !== 'undefined'
        ? sessionStorage.getItem('lk_access_token')
        : null;

    if (this.cachedToken !== activeToken) {
      this.cachedStatus = null;
      this.pendingPromise = null;
      this.cachedToken = activeToken;
    }

    if (!force && this.cachedStatus && this.cachedStatus.status === 'completed') {
      return this.cachedStatus;
    }

    if (!force && this.pendingPromise) {
      return this.pendingPromise;
    }

    this.pendingPromise = (async () => {
      try {
        const res = await firstValueFrom(
          this.http.get<LearnerAssessmentStatus>(this.apiUrl)
        );
        this.cachedToken =
          typeof sessionStorage !== 'undefined'
            ? sessionStorage.getItem('lk_access_token')
            : null;
        this.cachedStatus = res;
        return res;
      } finally {
        this.pendingPromise = null;
      }
    })();

    return this.pendingPromise;
  }

  clearCache(): void {
    this.cachedStatus = null;
    this.cachedToken = null;
    this.pendingPromise = null;
  }
}
