
import { inject } from '@angular/core';
import {
  CanActivateChildFn,
  Router
} from '@angular/router';

import { AuthService } from '../services/auth.service';
import { AssessmentStatusService } from '../services/assessment-status.service';

export const assessmentCompletionGuard: CanActivateChildFn =
  async (route) => {

    // Allow immediate access to assessment-related pages without any blocking checks
    if (route.data && route.data['allowIncompleteAssessment'] === true) {
      return true;
    }

    const authService = inject(AuthService);
    const assessmentService = inject(AssessmentStatusService);
    const router = inject(Router);

    try {
      const user = await authService.getCurrentUser();

      // Only learners need to complete the mandatory assessment.
      if (user.role !== 'learner') {
        return true;
      }

      const assessment = await assessmentService.getStatus();

      if (assessment.status === 'completed') {
        return true;
      }

      // Incomplete learner must complete or resume assessment.
      return router.createUrlTree(['/my-assessments']);

    } catch {
      return router.createUrlTree(['/login']);
    }
  };
