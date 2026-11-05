import { Component, OnInit, HostListener, inject, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet
} from '@angular/router';
import { AuthService, CurrentUser } from '../../core/services/auth.service';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss'
})
export class MainLayout implements OnInit {
  sidebarOpen = false;
  profileMenuOpen = false;
  user: CurrentUser | null = null;

  public readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly elementRef = inject(ElementRef);

  async ngOnInit(): Promise<void> {
    this.user = this.authService.getCurrentUserSnapshot();
    if (!this.user) {
      try {
        this.user = await this.authService.getCurrentUser();
      } catch {
        // Auth guard will handle unauthorized redirection if needed
      }
    }
  }

  toggleProfileMenu(event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    this.profileMenuOpen = !this.profileMenuOpen;
  }

  closeProfileMenu(): void {
    this.profileMenuOpen = false;
  }

  get userInitial(): string {
    return this.user?.full_name?.charAt(0)?.toUpperCase() || 'U';
  }

  get roleDisplayName(): string {
    switch (this.user?.role) {
      case 'superadmin': return 'Super Admin';
      case 'admin': return 'Administrator';
      case 'teacher': return 'Academic Faculty';
      case 'learner': return 'New Joinee';
      default: return 'User';
    }
  }

  logout(): void {
    this.profileMenuOpen = false;
    this.sidebarOpen = false;
    this.authService.logout();
    void this.router.navigateByUrl('/login');
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (this.profileMenuOpen) {
      const target = event.target as HTMLElement;
      const topbarProfile = this.elementRef.nativeElement.querySelector('.topbar-profile-container');
      if (topbarProfile && !topbarProfile.contains(target)) {
        this.profileMenuOpen = false;
      }
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.profileMenuOpen = false;
    this.sidebarOpen = false;
  }
}
