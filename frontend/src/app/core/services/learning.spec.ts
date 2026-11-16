import { describe, it, expect, beforeEach, vi } from 'vitest';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService } from './auth.service';
import { LearningService } from './learning.service';

describe('LearningService', () => {
  let service: LearningService;
  let httpMock: HttpTestingController;
  let authStub: { getToken: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    authStub = {
      getToken: vi.fn().mockReturnValue('test-jwt-token'),
    };

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        LearningService,
        { provide: AuthService, useValue: authStub },
      ],
    });

    service = TestBed.inject(LearningService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('fetches departments with Bearer authorization header', async () => {
    const promise = service.getDepartments();
    const req = httpMock.expectOne('/training-api/api/v1/departments');
    expect(req.request.method).toBe('GET');
    expect(req.request.headers.get('Authorization')).toBe('Bearer test-jwt-token');
    req.flush([
      { id: 1, name: 'Python', description: 'Python track', is_active: true },
    ]);

    const depts = await promise;
    expect(depts.length).toBe(1);
    expect(depts[0].name).toBe('Python');
    httpMock.verify();
  });

  it('throws clear authentication error when token is missing', async () => {
    authStub.getToken.mockReturnValue(null);
    expect(() => service.getDepartments()).toThrow('Please log in to continue.');
  });
});
