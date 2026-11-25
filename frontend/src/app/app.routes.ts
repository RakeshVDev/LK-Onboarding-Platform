
import { Routes, Router } from '@angular/router';
import { inject } from '@angular/core';

import { AuthLayout } from './layouts/auth-layout/auth-layout';
import { MainLayout } from './layouts/main-layout/main-layout';

import { Dashboard } from './features/dashboard/dashboard';
import { Login } from './features/auth/login/login';

import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';
import { assessmentCompletionGuard } from './core/guards/assessment-completion.guard';

export const routes: Routes = [

  // Public authentication
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

  // Protected application
  {
    path: '',
    component: MainLayout,
    canActivate: [authGuard],
    canActivateChild: [assessmentCompletionGuard],

    children: [

      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'dashboard'
      },

      // Dashboard
      {
        path: 'dashboard',
        data: { navKey: 'dashboard' },
        component: Dashboard
      },

      // Department Selection (Sequential Onboarding Stage 4-5)
      {
        path: 'department-selection',
        data: { navKey: 'department_selection' },
        canActivate: [roleGuard(['learner'])],
        loadComponent: () =>
          import('./features/onboarding/department-selection/department-selection')
            .then(m => m.DepartmentSelection)
      },

      // Profile
      {
        path: 'profile',
        data: { navKey: 'profile' },
        loadComponent: () =>
          import('./features/profile/profile')
            .then(m => m.Profile)
      },

      // User Management
      {
        path: 'users',
        data: { navKey: 'users' },
        canActivate: [roleGuard(['superadmin', 'admin'])],
        loadComponent: () =>
          import('./features/users/users')
            .then(m => m.Users)
      },

      // Departments
      {
        path: 'departments',
        data: { navKey: 'departments' },
        canActivate: [roleGuard(['superadmin', 'admin', 'teacher'])],
        loadComponent: () =>
          import('./features/departments/departments')
            .then(m => m.Departments)
      },

      // Courses
      {
        path: 'courses',
        data: { navKey: 'courses' },
        canActivate: [
          roleGuard(['superadmin', 'admin', 'teacher', 'learner'])
        ],
        loadComponent: () =>
          import('./features/courses/courses')
            .then(m => m.Courses)
      },

      // Cohorts
      {
        path: 'cohorts',
        data: { navKey: 'cohorts' },
        canActivate: [
          roleGuard(['superadmin', 'admin', 'teacher', 'learner'])
        ],
        loadComponent: () =>
          import('./features/cohorts/cohorts')
            .then(m => m.Cohorts)
      },

      // Live Classes consolidated into Cohorts -> Schedule tab
      {
        path: 'live-classes',
        pathMatch: 'full',
        redirectTo: () => inject(Router).createUrlTree(['/cohorts'], { queryParams: { tab: 'schedule' } })
      },

      // Assessment Management - Admin and Teacher only
      {
        path: 'assessments',
        canActivate: [
          roleGuard(['superadmin', 'admin', 'teacher'])
        ],
        loadComponent: () =>
          import('./features/assessments/assessment-management/assessment-management')
            .then(m => m.AssessmentManagement)
      },

      // Create Assessment
      {
        path: 'assessments/create',
        canActivate: [
          roleGuard(['superadmin', 'admin', 'teacher'])
        ],
        loadComponent: () =>
          import('./features/assessments/assessment-form/assessment-form')
            .then(m => m.AssessmentForm)
      },

      // Edit Assessment
      {
        path: 'assessments/edit/:id',
        canActivate: [
          roleGuard(['superadmin', 'admin', 'teacher'])
        ],
        loadComponent: () =>
          import('./features/assessments/assessment-form/assessment-form')
            .then(m => m.AssessmentForm)
      },

      // Learner Assessment Listing
      {
        path: 'my-assessments',
        data: {
          allowIncompleteAssessment: true,
          navKey: 'assessment'
        },
        canActivate: [
          roleGuard(['learner'])
        ],
        loadComponent: () =>
          import('./features/assessments/learner-assessments/learner-assessments')
            .then(m => m.LearnerAssessments)
      },

      // Learner Assessment Results
      {
        path: 'my-results',
        data: {
          allowIncompleteAssessment: true,
          navKey: 'result'
        },
        canActivate: [
          roleGuard(['learner', 'admin', 'teacher', 'superadmin'])
        ],
        loadComponent: () =>
          import('./features/assessments/learner-results/learner-results')
            .then(m => m.LearnerResults)
      },
      {
        path: 'results',
        redirectTo: 'my-results',
        pathMatch: 'full'
      },

      // Learner Diagnostic Reports Hub
      {
        path: 'my-reports',
        data: {
          allowIncompleteAssessment: true,
          navKey: 'report'
        },
        canActivate: [
          roleGuard(['learner', 'admin', 'teacher', 'superadmin'])
        ],
        loadComponent: () =>
          import('./features/assessments/learner-reports/learner-reports')
            .then(m => m.LearnerReports)
      },

      // Admin & Teacher: Learner Results Panel
      {
        path: 'assessment-results',
        data: { navKey: 'assessments' },
        canActivate: [
          roleGuard(['admin', 'teacher', 'superadmin'])
        ],
        loadComponent: () =>
          import('./features/assessments/admin-results/admin-results')
            .then(m => m.AdminResults)
      },

      // Take or resume assessment
      {
        path: 'assessments/take/:sessionId',
        data: {
          allowIncompleteAssessment: true,
          navKey: 'assessment'
        },
        canActivate: [
          roleGuard(['learner'])
        ],
        loadComponent: () =>
          import('./features/assessments/assessment-taking/assessment-taking')
            .then(m => m.AssessmentTaking)
      },

      // Assessment Results
      {
        path: 'assessments/results/:sessionId',
        data: {
          allowIncompleteAssessment: true,
          navKey: 'result'
        },
        canActivate: [
          roleGuard(['learner', 'admin', 'teacher', 'superadmin'])
        ],
        loadComponent: () =>
          import('./features/assessments/assessment-results/assessment-results')
            .then(m => m.AssessmentResults)
      },

      // Assessment Report
      {
        path: 'assessments/report/:sessionId',
        data: {
          allowIncompleteAssessment: true,
          navKey: 'report'
        },
        canActivate: [
          roleGuard(['learner', 'admin', 'teacher', 'superadmin'])
        ],
        loadComponent: () =>
          import('./features/assessments/assessment-report/assessment-report')
            .then(m => m.AssessmentReportPage)
      }

    ]
  },

  // Unknown routes
  {
    path: '**',
    redirectTo: 'dashboard'
  }

];
