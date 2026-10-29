
import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
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
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly tokenKey = 'lk_access_token';
  private readonly apiUrl = '/api/v1/auth';

  constructor(private readonly http: HttpClient) {}

  async login(email: string, password: string): Promise<CurrentUser> {
    const response = await firstValueFrom(
      this.http.post<LoginResponse>(`${this.apiUrl}/login`, {
        email: email.trim().toLowerCase(),
        password
      })
    );

    sessionStorage.setItem(this.tokenKey, response.access_token);

    try {
      return await this.getCurrentUser();
    } catch (error) {
      this.logout();
      throw error;
    }
  }

  async getCurrentUser(): Promise<CurrentUser> {
    const token = sessionStorage.getItem(this.tokenKey);

    if (!token) {
      throw new Error('Please log in to continue.');
    }

    return firstValueFrom(
      this.http.get<CurrentUser>(`${this.apiUrl}/me`, {
        headers: new HttpHeaders({
          Authorization: `Bearer ${token}`
        })
      })
    );
  }

  logout(): void {
    sessionStorage.removeItem(this.tokenKey);
  }

  getToken(): string | null {
    return sessionStorage.getItem(this.tokenKey);
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
