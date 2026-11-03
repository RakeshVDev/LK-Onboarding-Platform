import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AssessmentManagement } from './assessment-management';

describe('AssessmentManagement', () => {
  let component: AssessmentManagement;
  let fixture: ComponentFixture<AssessmentManagement>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AssessmentManagement],
    }).compileComponents();

    fixture = TestBed.createComponent(AssessmentManagement);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
