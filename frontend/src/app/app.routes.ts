
import { Routes } from '@angular/router';

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
        data: { allowIncompleteAssessment: true },
        component: Dashboard
      },

      // Profile
      {
        path: 'profile',
        data: {
          allowIncompleteAssessment: true
        },
        loadComponent: () =>
          import('./features/profile/profile')
            .then(m => m.Profile)
      },

      // User Management
      {
        path: 'users',
        canActivate: [roleGuard(['superadmin', 'admin'])],
        loadComponent: () =>
          import('./features/users/users')
            .then(m => m.Users)
      },

      // Departments
      {
        path: 'departments',
        canActivate: [roleGuard(['superadmin', 'admin'])],
        loadComponent: () =>
          import('./features/departments/departments')
            .then(m => m.Departments)
      },

      // Courses
      {
        path: 'courses',
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
        canActivate: [
          roleGuard(['superadmin', 'admin', 'teacher', 'learner'])
        ],
        loadComponent: () =>
          import('./features/cohorts/cohorts')
            .then(m => m.Cohorts)
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
          allowIncompleteAssessment: true
        },
        canActivate: [
          roleGuard(['learner'])
        ],
        loadComponent: () =>
          import('./features/assessments/learner-assessments/learner-assessments')
            .then(m => m.LearnerAssessments)
      },

      // Learner Assessment Results & Report Cards
      {
        path: 'my-results',
        data: {
          allowIncompleteAssessment: true
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

      // Admin & Teacher: Learner Results Panel
      {
        path: 'assessment-results',
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
          allowIncompleteAssessment: true
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
          allowIncompleteAssessment: true
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
          allowIncompleteAssessment: true
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
