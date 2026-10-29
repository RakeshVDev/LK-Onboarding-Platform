
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = async () => {
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

    return true;
  } catch {
    authService.logout();
    return router.createUrlTree(['/login']);
  }
};
