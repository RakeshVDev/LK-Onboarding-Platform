import { Component, OnInit } from '@angular/core';
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
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss'
})
export class MainLayout implements OnInit {
  sidebarOpen = false;
  user: CurrentUser | null = null;

  constructor(
    public readonly authService: AuthService,
    private readonly router: Router
  ) {}

  ngOnInit(): void {
    this.user = this.authService.getCurrentUserSnapshot();
  }

  logout(): void {
    this.authService.logout();
    void this.router.navigateByUrl('/login');
  }
}
