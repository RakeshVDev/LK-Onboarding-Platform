
import { inject } from '@angular/core';
import {
  CanActivateChildFn,
  Router
} from '@angular/router';

import { AuthService } from '../services/auth.service';
import { OnboardingService } from '../services/onboarding.service';

const ALWAYS_ALLOWED_LEARNER_KEYS = new Set(['assessment', 'result', 'report']);

export const assessmentCompletionGuard: CanActivateChildFn =
  async (route) => {
    const authService = inject(AuthService);
    const onboardingService = inject(OnboardingService);
    const router = inject(Router);

    try {
      const user = await authService.getCurrentUser();

      if (user.role !== 'learner') {
        return true;
      }

      const permissions = await onboardingService.getPermissions();
      const navKey = route.data?.['navKey'] as string | undefined;

      if (permissions.is_unlocked) {
        if (navKey === 'department_selection') {
          return router.createUrlTree(['/dashboard']);
        }
        return true;
      }

      if (navKey && ALWAYS_ALLOWED_LEARNER_KEYS.has(navKey)) {
        return true;
      }

      if (navKey === 'department_selection' && permissions.can_select_department) {
        return true;
      }

      return router.createUrlTree([permissions.redirect_to || '/my-assessments']);
    } catch {
      return router.createUrlTree(['/login']);
    }
  };

export const onboardingGuard = assessmentCompletionGuard;
