import { describe, it, expect, beforeEach, vi } from 'vitest';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AssessmentStatusService } from '../../../core/services/assessment-status.service';
import { AssessmentService } from './assessment';

describe('AssessmentService', () => {
  let service: AssessmentService;
  let httpMock: HttpTestingController;
  let statusStub: { clearCache: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    statusStub = {
      clearCache: vi.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        AssessmentService,
        { provide: AssessmentStatusService, useValue: statusStub },
      ],
    });

    service = TestBed.inject(AssessmentService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('requests assessment templates and invalidates status cache on sync notification', () => {
    let loaded = 0;
    service.getTemplates().subscribe((templates) => {
      loaded = templates.length;
    });

    const req = httpMock.expectOne('/training-api/api/v1/assessments/templates');
    expect(req.request.method).toBe('GET');
    req.flush([{ id: 1, name: 'Logical Reasoning' }]);
    expect(loaded).toBe(1);

    const beforeSync = service.syncVersion();
    service.notifyStatusChanged();
    expect(statusStub.clearCache).toHaveBeenCalledTimes(1);
    expect(service.syncVersion()).toBe(beforeSync + 1);
    httpMock.verify();
  });
});
