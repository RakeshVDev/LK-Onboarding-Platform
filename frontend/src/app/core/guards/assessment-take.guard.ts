import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AssessmentService } from '../../features/assessments/services/assessment';

/**
 * Route guard for '/assessments/take/:sessionId'.
 * Ensures that submitted or completed assessments cannot be reopened or re-entered
 * via direct URL entry, browser back/forward history, or restored tabs.
 */
export const assessmentTakeGuard: CanActivateFn = async (route) => {
  const router = inject(Router);
  const assessmentService = inject(AssessmentService);

  const sessionId = Number(route.paramMap.get('sessionId'));
  if (!sessionId || !Number.isFinite(sessionId)) {
    return router.createUrlTree(['/my-assessments']);
  }

  // 1. Fast in-memory check for sessions submitted in the current browser session
  if (assessmentService.isSessionLocallySubmitted(sessionId)) {
    return router.createUrlTree(['/assessments/report', sessionId]);
  }

  // 2. Validate authoritative session status with the backend
  try {
    const check = await firstValueFrom(assessmentService.checkSession(sessionId));
    if (check.is_submitted || check.status === 'completed' || check.status === 'submitted') {
      const dest = check.redirect_url || (check.has_report ? `/assessments/report/${sessionId}` : `/assessments/results/${sessionId}`);
      return router.parseUrl(dest);
    }
    if (check.is_expired) {
      return router.createUrlTree(['/my-assessments']);
    }
    return true;
  } catch (error: any) {
    const detail = String(error?.error?.detail || error?.message || '').toLowerCase();
    if (
      detail.includes('already been submitted') ||
      detail.includes('already submitted') ||
      detail.includes('no longer in progress')
    ) {
      return router.createUrlTree(['/assessments/report', sessionId]);
    }
    if (error?.status === 409 || detail.includes('expired')) {
      return router.createUrlTree(['/my-assessments']);
    }
    if (error?.status === 404) {
      return router.createUrlTree(['/my-assessments']);
    }
    // Allow component to render its internal error state on unexpected network issues
    return true;
  }
};
