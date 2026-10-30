import { TestBed } from '@angular/core/testing';

import { Learning } from './learning';

describe('Learning', () => {
  let service: Learning;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Learning);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
