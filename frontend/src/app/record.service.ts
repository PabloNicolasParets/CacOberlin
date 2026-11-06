import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ListeningRecord, RecordInput } from './record.model';

@Injectable({ providedIn: 'root' })
export class RecordService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/records';

  list(search = ''): Observable<ListeningRecord[]> {
    let params = new HttpParams();
    if (search.trim()) {
      params = params.set('search', search.trim());
    }
    return this.http.get<ListeningRecord[]>(this.apiUrl, { params });
  }

  create(record: RecordInput): Observable<ListeningRecord> {
    return this.http.post<ListeningRecord>(this.apiUrl, record);
  }

  update(id: number, record: RecordInput): Observable<ListeningRecord> {
    return this.http.put<ListeningRecord>(`${this.apiUrl}/${id}`, record);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
