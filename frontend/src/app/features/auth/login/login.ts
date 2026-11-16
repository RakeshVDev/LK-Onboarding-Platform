import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { AssessmentStatusService } from '../../../core/services/assessment-status.service';
import { OnboardingService } from '../../../core/services/onboarding.service';
import { BrandLogo } from '../../../shared/components/brand-logo/brand-logo';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, BrandLogo],
  templateUrl: './login.html',
  styleUrl: './login.scss'
})
export class Login {
  email = '';
  password = '';

  readonly loading = signal(false);
  readonly showPassword = signal(false);
  readonly errorMessage = signal('');

  constructor(
    private readonly authService: AuthService,
    private readonly assessmentStatusService: AssessmentStatusService,
    private readonly onboardingService: OnboardingService,
    private readonly router: Router
  ) {}

  togglePasswordVisibility(): void {
    this.showPassword.set(!this.showPassword());
  }

  async submitLogin(): Promise<void> {
    if (this.loading()) return;

    this.errorMessage.set('');

    if (!this.email.trim() || !this.password) {
      this.errorMessage.set('Enter your email address and password.');
      return;
    }

    this.loading.set(true);

    try {
      await this.authService.login(this.email.trim(), this.password);
      this.password = '';
      this.assessmentStatusService.clearCache();
      this.onboardingService.clearCache();
      const user = await this.authService.getCurrentUser();
      if (user.role === 'learner') {
        try {
          const perms = await this.onboardingService.getPermissions(true);
          await this.router.navigateByUrl(perms.redirect_to || '/my-assessments');
          return;
        } catch {
          await this.router.navigateByUrl('/my-assessments');
          return;
        }
      }
      await this.router.navigateByUrl('/dashboard');
    } catch (error: unknown) {
      this.errorMessage.set(this.authService.getErrorMessage(error));
    } finally {
      this.loading.set(false);
    }
  }
}
