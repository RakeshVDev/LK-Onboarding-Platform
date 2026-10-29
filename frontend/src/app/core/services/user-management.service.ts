
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from './auth.service';

export type ManagedRole = 'admin' | 'teacher' | 'learner';

export interface ManagedUser {
  id: number;
  full_name: string;
  email: string;
  role: 'superadmin' | ManagedRole;
  is_active: boolean;
  created_at: string;
}

export interface CreateUserRequest {
  full_name: string;
  email: string;
  password: string;
  role: ManagedRole;
}

@Injectable({ providedIn: 'root' })
export class UserManagementService {
  private readonly apiUrl = '/api/v1/users';

  constructor(
    private readonly http: HttpClient,
    private readonly authService: AuthService
  ) {}

  private get options() {
    const token = this.authService.getToken();

    if (!token) {
      throw new Error('Your session has expired. Please sign in again.');
    }

    return {
      headers: new HttpHeaders({
        Authorization: `Bearer ${token}`
      })
    };
  }

  async listUsers(search = ''): Promise<ManagedUser[]> {
    const params = new HttpParams().set('search', search.trim());

    return firstValueFrom(
      this.http.get<ManagedUser[]>(this.apiUrl, {
        ...this.options,
        params
      })
    );
  }

  async createUser(payload: CreateUserRequest): Promise<ManagedUser> {
    return firstValueFrom(
      this.http.post<ManagedUser>(
        this.apiUrl,
        payload,
        this.options
      )
    );
  }

  async updateStatus(
    userId: number,
    isActive: boolean
  ): Promise<ManagedUser> {
    return firstValueFrom(
      this.http.patch<ManagedUser>(
        `${this.apiUrl}/${userId}/status`,
        { is_active: isActive },
        this.options
      )
    );
  }
}
