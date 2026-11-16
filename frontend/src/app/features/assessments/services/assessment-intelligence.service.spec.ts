import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import {
  AssessmentIntelligenceResponse,
  AssessmentIntelligenceService,
  OverviewAnalyticsResponse,
} from './assessment-intelligence.service';

describe('AssessmentIntelligenceService', () => {
  let service: AssessmentIntelligenceService;
  let httpMock: HttpTestingController;

  const baseUrl = '/training-api/api/v1/assessment-intelligence';

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(AssessmentIntelligenceService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('POSTs session evaluation request with force flag and optional scoring version tag', () => {
    const mockResp = {
      session_id: 42,
      template_id: 7,
      overall_percentage: 86.5,
    } as AssessmentIntelligenceResponse;

    let actual: AssessmentIntelligenceResponse | undefined;
    service.evaluateSession(42, true, 'v2.0-offline').subscribe((res) => {
      actual = res;
    });

    const req = httpMock.expectOne(`${baseUrl}/sessions/42/evaluate`);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      force: true,
      scoring_version_tag: 'v2.0-offline',
    });
    req.flush(mockResp);
    expect(actual).toEqual(mockResp);
  });

  it('GETs session intelligence and overview analytics from dedicated intelligence routes', () => {
    const mockIntel = { session_id: 15, skill_level: 'Advanced' } as AssessmentIntelligenceResponse;
    let intelResult: AssessmentIntelligenceResponse | undefined;
    service.getSessionIntelligence(15).subscribe((res) => (intelResult = res));

    const intelReq = httpMock.expectOne(`${baseUrl}/sessions/15/intelligence`);
    expect(intelReq.request.method).toBe('GET');
    intelReq.flush(mockIntel);
    expect(intelResult?.skill_level).toBe('Advanced');

    const mockOverview = {
      total_evaluated_sessions: 12,
    } as OverviewAnalyticsResponse;
    let overviewResult: OverviewAnalyticsResponse | undefined;
    service.getOverviewAnalytics().subscribe((res) => (overviewResult = res));

    const overviewReq = httpMock.expectOne(`${baseUrl}/analytics/overview`);
    expect(overviewReq.request.method).toBe('GET');
    overviewReq.flush(mockOverview);
    expect(overviewResult?.total_evaluated_sessions).toBe(12);
  });
});

