
import { Component, OnInit, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService, CurrentUser, UserRole } from '../../core/services/auth.service';

interface WorkspaceCard {
  title: string;
  description: string;
  icon: string;
  route?: string;
  status: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class Dashboard implements OnInit {
  readonly user = signal<CurrentUser | null>(null);
  readonly cards = signal<WorkspaceCard[]>([]);
  readonly loading = signal(true);
  readonly errorMessage = signal('');

  constructor(
    private readonly authService: AuthService,
    private readonly router: Router
  ) {}

  async ngOnInit(): Promise<void> {
    try {
      const currentUser = await this.authService.getCurrentUser();

      if (!currentUser.is_active) {
        this.authService.logout();
        await this.router.navigateByUrl('/login');
        return;
      }

      this.user.set(currentUser);
      this.cards.set(this.getCardsForRole(currentUser.role));
    } catch {
      this.errorMessage.set('Unable to load your dashboard. Please sign in again.');
      this.authService.logout();
      await this.router.navigateByUrl('/login');
    } finally {
      this.loading.set(false);
    }
  }

  get roleTitle(): string {
    switch (this.user()?.role) {
      case 'superadmin': return 'Super Administrator';
      case 'admin': return 'Admin / Manager';
      case 'teacher': return 'Teacher Workspace';
      case 'learner': return 'User / New Joinee';
      default: return 'Workspace';
    }
  }

  get roleDescription(): string {
    switch (this.user()?.role) {
      case 'superadmin':
        return 'Manage platform access, organization and operations.';
      case 'admin':
        return 'Coordinate onboarding, users and training operations.';
      case 'teacher':
        return 'Manage your teaching activities and learner progress.';
      case 'learner':
        return 'Access your onboarding activities and learning journey.';
      default:
        return 'Your learning and development workspace.';
    }
  }

  private getCardsForRole(role: UserRole): WorkspaceCard[] {
    switch (role) {
      case 'superadmin':
        return [
          {
            title: 'User Management',
            description: 'Manage platform users and access.',
            icon: '♟',
            route: '/users',
            status: 'Available'
          },
          {
            title: 'Departments',
            description: 'Organize departments and teams.',
            icon: '▤',
            route: '/departments',
            status: 'Available'
          },
          {
            title: 'Courses',
            description: 'Manage training courses.',
            icon: '▣',
            route: '/courses',
            status: 'Available'
          },
          {
            title: 'Cohorts',
            description: 'Organize training batches.',
            icon: '◷',
            route: '/cohorts',
            status: 'Available'
          }
        ];

      case 'admin':
        return [
          {
            title: 'User Management',
            description: 'Coordinate users and new joiners.',
            icon: '♟',
            route: '/users',
            status: 'Available'
          },
          {
            title: 'Departments',
            description: 'View and organize departments.',
            icon: '▤',
            route: '/departments',
            status: 'Available'
          },
          {
            title: 'Training Courses',
            description: 'Review and coordinate courses.',
            icon: '▣',
            route: '/courses',
            status: 'Available'
          },
          {
            title: 'Training Cohorts',
            description: 'Coordinate training batches.',
            icon: '◷',
            route: '/cohorts',
            status: 'Available'
          },
          {
            title: 'Attendance',
            description: 'Track attendance and participation.',
            icon: '✓',
            status: 'Coming soon'
          },
          {
            title: 'Reports',
            description: 'Review onboarding and training results.',
            icon: '▥',
            status: 'Coming soon'
          }
        ];

      case 'teacher':
        return [
          {
            title: 'My Courses',
            description: 'Access and manage training courses.',
            icon: '▣',
            route: '/courses',
            status: 'Available'
          },
          {
            title: 'My Cohorts',
            description: 'View training batches and learners.',
            icon: '◷',
            route: '/cohorts',
            status: 'Available'
          },
          {
            title: 'Learning Materials',
            description: 'Share syllabus and learning resources.',
            icon: '▤',
            status: 'Coming soon'
          },
          {
            title: 'Attendance',
            description: 'Record and review learner attendance.',
            icon: '✓',
            status: 'Coming soon'
          },
          {
            title: 'Assessments',
            description: 'Create tests and evaluate learners.',
            icon: '✎',
            status: 'Coming soon'
          },
          {
            title: 'Results',
            description: 'Review learner assessment results.',
            icon: '▥',
            status: 'Coming soon'
          }
        ];

      case 'learner':
        return [
          {
            title: 'My Courses',
            description: 'Explore your available training courses.',
            icon: '▣',
            route: '/courses',
            status: 'Available'
          },
          {
            title: 'My Cohort',
            description: 'View your training batch.',
            icon: '◷',
            route: '/cohorts',
            status: 'Available'
          },
          {
            title: 'Onboarding Tests',
            description: 'Complete assigned onboarding assessments.',
            icon: '✎',
            status: 'Coming soon'
          },
          {
            title: 'Timetable',
            description: 'Check your upcoming training sessions.',
            icon: '▦',
            status: 'Coming soon'
          },
          {
            title: 'My Progress',
            description: 'Track your learning and completion.',
            icon: '↗',
            status: 'Coming soon'
          },
          {
            title: 'My Results',
            description: 'Review your assessment results.',
            icon: '▥',
            status: 'Coming soon'
          }
        ];

      default:
        return [];
    }
  }
}
