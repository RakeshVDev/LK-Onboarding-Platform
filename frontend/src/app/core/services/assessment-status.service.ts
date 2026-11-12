
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

  constructor(private readonly http: HttpClient) {}

  async getStatus(): Promise<LearnerAssessmentStatus> {
    return await firstValueFrom(
      this.http.get<LearnerAssessmentStatus>(this.apiUrl)
    );
  }
}
