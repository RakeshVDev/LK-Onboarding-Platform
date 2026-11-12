
import { Injectable, signal } from '@angular/core';
import {
  HttpClient,
  HttpErrorResponse,
  HttpHeaders
} from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export type UserRole = 'superadmin' | 'admin' | 'teacher' | 'learner';

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at?: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly tokenKey = 'lk_access_token';
  private readonly currentUserKey = 'lk_current_user';
  private readonly apiUrl = '/api/v1/auth';

  private readonly currentUserState = signal<CurrentUser | null>(null);
  readonly currentUser = this.currentUserState.asReadonly();

  constructor(private readonly http: HttpClient) {}

  private setCurrentUser(user: CurrentUser | null): void {
    this.currentUserState.set(user);

    if (typeof sessionStorage !== 'undefined') {
      if (user) {
        sessionStorage.setItem(
          this.currentUserKey,
          JSON.stringify({
            id: user.id,
            full_name: user.full_name,
            email: user.email,
            role: user.role,
            is_active: user.is_active,
            created_at: user.created_at
          })
        );
      } else {
        sessionStorage.removeItem(this.currentUserKey);
      }
    }
  }

  async login(email: string, password: string): Promise<CurrentUser> {
    const response = await firstValueFrom(
      this.http.post<LoginResponse>(`${this.apiUrl}/login`, {
        email: email.trim().toLowerCase(),
        password
      })
    );

    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem(this.tokenKey, response.access_token);
    }

    try {
      const user = await this.getCurrentUser();
      this.setCurrentUser(user);
      return user;
    } catch (error) {
      this.logout();
      throw error;
    }
  }

  async getCurrentUser(): Promise<CurrentUser> {
    const token = this.getToken();

    if (!token) {
      this.setCurrentUser(null);
      throw new Error('Please log in to continue.');
    }

    try {
      const user = await firstValueFrom(
        this.http.get<CurrentUser>(`${this.apiUrl}/me`, {
          headers: new HttpHeaders({
            Authorization: `Bearer ${token}`
          })
        })
      );

      this.setCurrentUser(user);
      return user;
    } catch (error) {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        this.logout();
      }

      throw error;
    }
  }

  hasRole(...roles: UserRole[]): boolean {
    const user = this.currentUserState();
    return user !== null &&
      user.is_active &&
      roles.includes(user.role);
  }

  getCurrentUserSnapshot(): CurrentUser | null {
    return this.currentUserState();
  }

  logout(): void {
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.removeItem(this.tokenKey);
    }
    this.setCurrentUser(null);
  }

  getToken(): string | null {
    return typeof sessionStorage !== 'undefined'
      ? sessionStorage.getItem(this.tokenKey)
      : null;
  }

  async updateProfile(fullName: string): Promise<CurrentUser> {
    const token = this.getToken();
    if (!token) throw new Error('Please log in to continue.');

    const updated = await firstValueFrom(
      this.http.put<CurrentUser>(
        `${this.apiUrl}/profile`,
        { full_name: fullName.trim() },
        {
          headers: new HttpHeaders({
            Authorization: `Bearer ${token}`
          })
        }
      )
    );

    this.setCurrentUser(updated);
    return updated;
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    const token = this.getToken();
    if (!token) throw new Error('Please log in to continue.');

    return firstValueFrom(
      this.http.post<{ message: string }>(
        `${this.apiUrl}/change-password`,
        {
          current_password: currentPassword,
          new_password: newPassword
        },
        {
          headers: new HttpHeaders({
            Authorization: `Bearer ${token}`
          })
        }
      )
    );
  }

  getErrorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      if (error.status === 401) {
        return 'Incorrect email or password. Please try again.';
      }

      if (error.status === 0) {
        return 'Unable to connect to the server. Check that the Identity API is running.';
      }

      if (error.status >= 500) {
        return 'The server encountered an error. Please try again shortly.';
      }

      return error.error?.detail || 'Login failed. Please try again.';
    }

    return 'Something went wrong. Please try again.';
  }
}
