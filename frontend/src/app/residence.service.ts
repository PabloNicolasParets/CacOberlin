import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { Residence, ResidenceInput } from './residence.model';

@Injectable({ providedIn: 'root' })
export class ResidenceService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/residences';

  list(): Observable<Residence[]> {
    return this.http.get<Residence[]>(this.apiUrl);
  }

  create(residence: ResidenceInput): Observable<Residence> {
    return this.http.post<Residence>(this.apiUrl, residence);
  }

  update(id: number, residence: ResidenceInput): Observable<Residence> {
    return this.http.put<Residence>(`${this.apiUrl}/${id}`, residence);
  }
}
