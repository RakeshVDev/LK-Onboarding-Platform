
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService, UserRole } from '../services/auth.service';

export const roleGuard = (allowedRoles: UserRole[]): CanActivateFn => {
  return async () => {
    const authService = inject(AuthService);
    const router = inject(Router);

    if (!authService.getToken()) {
      return router.createUrlTree(['/login']);
    }

    try {
      const user = await authService.getCurrentUser();

      if (!user.is_active) {
        authService.logout();
        return router.createUrlTree(['/login']);
      }

      if (!allowedRoles.includes(user.role)) {
        return router.createUrlTree(['/dashboard']);
      }

      return true;
    } catch {
      authService.logout();
      return router.createUrlTree(['/login']);
    }
  };
};
