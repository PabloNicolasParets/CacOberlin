import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ContactInput, ContactRecord } from './contact.model';

@Injectable({ providedIn: 'root' })
export class ContactService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/contacts';

  list(): Observable<ContactRecord[]> {
    return this.http.get<ContactRecord[]>(this.apiUrl);
  }

  create(contact: ContactInput): Observable<ContactRecord> {
    return this.http.post<ContactRecord>(this.apiUrl, contact);
  }

  update(id: number, contact: ContactInput): Observable<ContactRecord> {
    return this.http.put<ContactRecord>(`${this.apiUrl}/${id}`, contact);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
