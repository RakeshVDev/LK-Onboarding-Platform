
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
  private readonly storageKey = 'ase_managed_users';
  private cachedUsers: ManagedUser[] = [];

  constructor(
    private readonly http: HttpClient,
    private readonly authService: AuthService
  ) {
    this.cachedUsers = this.readCachedUsers();
  }

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

  private sanitizeUser(user: ManagedUser): ManagedUser {
    return {
      id: user.id,
      full_name: user.full_name,
      email: user.email,
      role: user.role,
      is_active: user.is_active,
      created_at: user.created_at
    };
  }

  private readCachedUsers(): ManagedUser[] {
    if (typeof localStorage === 'undefined') {
      return this.cachedUsers;
    }

    try {
      const raw = localStorage.getItem(this.storageKey);
      if (!raw) {
        this.cachedUsers = [];
        return [];
      }

      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        this.cachedUsers = parsed
          .filter((item): item is ManagedUser => Boolean(item && typeof item === 'object'))
          .map(item => this.sanitizeUser(item));
        return this.cachedUsers;
      }
    } catch {
      return this.cachedUsers;
    }

    return [];
  }

  private writeCachedUsers(users: ManagedUser[], forceNotify = false): void {
    const sanitized = users.map(u => this.sanitizeUser(u));
    this.cachedUsers = sanitized;

    const nextJson = JSON.stringify(sanitized);
    let changed = forceNotify;

    if (typeof localStorage !== 'undefined') {
      try {
        const prevJson = localStorage.getItem(this.storageKey);
        if (prevJson !== nextJson) {
          localStorage.setItem(this.storageKey, nextJson);
          changed = true;
        }
      } catch {
        // Ignore storage quota / privacy mode errors
      }
    }

    if (changed && typeof window !== 'undefined' && typeof CustomEvent !== 'undefined') {
      window.dispatchEvent(new CustomEvent('ase_users_changed'));
    }
  }

  private mergeIntoCache(incoming: ManagedUser[], forceNotify = false): void {
    const existing = this.readCachedUsers();
    const byId = new Map<number, ManagedUser>();

    for (const user of existing) {
      byId.set(user.id, user);
    }
    for (const user of incoming) {
      byId.set(user.id, this.sanitizeUser(user));
    }

    this.writeCachedUsers(Array.from(byId.values()), forceNotify);
  }

  async listUsers(search = ''): Promise<ManagedUser[]> {
    const trimmedSearch = search.trim();
    const params = new HttpParams().set('search', trimmedSearch);

    const users = await firstValueFrom(
      this.http.get<ManagedUser[]>(this.apiUrl, {
        ...this.options,
        params
      })
    );

    if (!trimmedSearch) {
      this.writeCachedUsers(users, false);
    } else if (users.length > 0) {
      this.mergeIntoCache(users, false);
    }

    return users;
  }

  async createUser(payload: CreateUserRequest): Promise<ManagedUser> {
    const created = await firstValueFrom(
      this.http.post<ManagedUser>(
        this.apiUrl,
        payload,
        this.options
      )
    );

    this.mergeIntoCache([created], true);
    return created;
  }

  async updateStatus(
    userId: number,
    isActive: boolean
  ): Promise<ManagedUser> {
    const updated = await firstValueFrom(
      this.http.patch<ManagedUser>(
        `${this.apiUrl}/${userId}/status`,
        { is_active: isActive },
        this.options
      )
    );

    this.mergeIntoCache([updated], true);
    return updated;
  }

  getTeachers(): ManagedUser[] {
    return this.readCachedUsers().filter(
      user => user.role === 'teacher' && user.is_active !== false
    );
  }

  getLearners(): ManagedUser[] {
    return this.readCachedUsers().filter(
      user => user.role === 'learner' && user.is_active !== false
    );
  }

  async listTeachers(): Promise<ManagedUser[]> {
    const currentSnapshot = this.authService.getCurrentUserSnapshot();
    const canQueryDirectory =
      Boolean(this.authService.getToken()) &&
      (!currentSnapshot || this.authService.hasRole('superadmin', 'admin'));

    if (!canQueryDirectory) {
      return this.getTeachers();
    }

    try {
      const users = await this.listUsers();
      return users.filter(
        user => user.role === 'teacher' && user.is_active !== false
      );
    } catch {
      return this.getTeachers();
    }
  }

  async listLearners(): Promise<ManagedUser[]> {
    const currentSnapshot = this.authService.getCurrentUserSnapshot();
    const canQueryDirectory =
      Boolean(this.authService.getToken()) &&
      (!currentSnapshot || this.authService.hasRole('superadmin', 'admin'));

    if (!canQueryDirectory) {
      return this.getLearners();
    }

    try {
      const users = await this.listUsers();
      return users.filter(
        user => user.role === 'learner' && user.is_active !== false
      );
    } catch {
      return this.getLearners();
    }
  }
}
