
import { Routes } from '@angular/router';

import { AuthLayout } from './layouts/auth-layout/auth-layout';
import { MainLayout } from './layouts/main-layout/main-layout';
import { Dashboard } from './features/dashboard/dashboard';
import { Login } from './features/auth/login/login';

import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  // Public authentication routes
  {
    path: 'login',
    component: AuthLayout,
    children: [
      {
        path: '',
        component: Login
      }
    ]
  },

  // Protected application layout
  {
    path: '',
    component: MainLayout,
    canActivate: [authGuard],
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'dashboard'
      },

      // All authenticated roles can access their own dashboard
      {
        path: 'dashboard',
        component: Dashboard
      },

      // Superadmin and admin only
      {
        path: 'users',
        canActivate: [
          roleGuard(['superadmin', 'admin'])
        ],
        loadComponent: () =>
          import('./features/users/users').then(m => m.Users)
      },

      // Organization management
      {
        path: 'departments',
        canActivate: [
          roleGuard(['superadmin', 'admin'])
        ],
        loadComponent: () =>
          import('./features/departments/departments').then(
            m => m.Departments
          )
      },

      // Courses: all roles can open the page;
      // backend must enforce which courses each user can access
      {
        path: 'courses',
        canActivate: [
          roleGuard(['superadmin', 'admin', 'teacher', 'learner'])
        ],
        loadComponent: () =>
          import('./features/courses/courses').then(m => m.Courses)
      },

      // Cohorts: all roles can open the page;
      // backend must enforce assignment and membership restrictions
      {
        path: 'cohorts',
        canActivate: [
          roleGuard(['superadmin', 'admin', 'teacher', 'learner'])
        ],
        loadComponent: () =>
          import('./features/cohorts/cohorts').then(m => m.Cohorts)
      }
    ]
  },

  // Unknown routes
  {
    path: '**',
    redirectTo: 'dashboard'
  }
];
