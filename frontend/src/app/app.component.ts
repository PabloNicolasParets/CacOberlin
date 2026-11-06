import { DatePipe, DecimalPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ListeningRecord, RecordInput } from './record.model';
import { RecordService } from './record.service';

interface RecordForm {
  record_date: string;
  consult_type: 'directa' | 'indirecta';
  full_name: string;
  address: string;
  dni: string;
  kinship: string;
  consultation: string;
  referral: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [DatePipe, DecimalPipe, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent implements OnInit {
  private readonly recordService = inject(RecordService);

  records: ListeningRecord[] = [];
  form = this.emptyForm();
  search = '';
  selectedType: 'todas' | 'directa' | 'indirecta' = 'todas';
  editingId: number | null = null;
  isLoading = false;
  isSaving = false;
  isDeleting = false;
  errorMessage = '';
  successMessage = '';

  ngOnInit(): void {
    this.loadRecords();
  }

  get visibleRecords(): ListeningRecord[] {
    const term = this.search.trim().toLocaleLowerCase('es');
    return this.records.filter((record) => {
      const matchesType =
        this.selectedType === 'todas' || record.consult_type === this.selectedType;
      const searchableText = [
        record.full_name,
        record.dni ?? '',
        record.consultation,
        record.referral ?? '',
      ]
        .join(' ')
        .toLocaleLowerCase('es');
      return matchesType && (!term || searchableText.includes(term));
    });
  }

  get directCount(): number {
    return this.records.filter((record) => record.consult_type === 'directa').length;
  }

  get indirectCount(): number {
    return this.records.filter((record) => record.consult_type === 'indirecta').length;
  }

  loadRecords(): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.recordService.list().subscribe({
      next: (records) => {
        this.records = records;
        this.isLoading = false;
      },
      error: (error: unknown) => {
        this.errorMessage = this.describeError(error, 'No se pudieron cargar las consultas.');
        this.isLoading = false;
      },
    });
  }

  saveRecord(): void {
    this.isSaving = true;
    this.errorMessage = '';
    this.successMessage = '';
    const payload: RecordInput = {
      ...this.form,
      full_name: this.form.full_name.trim(),
      address: this.optionalValue(this.form.address),
      dni: this.optionalValue(this.form.dni),
      kinship: this.optionalValue(this.form.kinship),
      consultation: this.form.consultation.trim(),
      referral: this.optionalValue(this.form.referral),
    };
    const request = this.editingId === null
      ? this.recordService.create(payload)
      : this.recordService.update(this.editingId, payload);

    request.subscribe({
      next: () => {
        this.successMessage =
          this.editingId === null ? 'La escucha quedó registrada.' : 'Los cambios se guardaron.';
        this.resetForm();
        this.loadRecords();
        this.isSaving = false;
      },
      error: (error: unknown) => {
        this.errorMessage = this.describeError(error, 'No se pudo guardar el registro.');
        this.isSaving = false;
      },
    });
  }

  editRecord(record: ListeningRecord): void {
    this.editingId = record.id;
    this.successMessage = '';
    this.errorMessage = '';
    this.form = {
      record_date: record.record_date,
      consult_type: record.consult_type,
      full_name: record.full_name,
      address: record.address ?? '',
      dni: record.dni ?? '',
      kinship: record.kinship ?? '',
      consultation: record.consultation,
      referral: record.referral ?? '',
    };
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  deleteRecord(record: ListeningRecord): void {
    const confirmed = window.confirm(`¿Eliminar la consulta de ${record.full_name}?`);
    if (!confirmed) {
      return;
    }

    this.isDeleting = true;
    this.errorMessage = '';
    this.recordService.delete(record.id).subscribe({
      next: () => {
        this.records = this.records.filter((item) => item.id !== record.id);
        if (this.editingId === record.id) {
          this.resetForm();
        }
        this.successMessage = 'El registro se eliminó.';
        this.isDeleting = false;
      },
      error: (error: unknown) => {
        this.errorMessage = this.describeError(error, 'No se pudo eliminar el registro.');
        this.isDeleting = false;
      },
    });
  }

  resetForm(): void {
    this.form = this.emptyForm();
    this.editingId = null;
  }

  private emptyForm(): RecordForm {
    return {
      record_date: this.localDate(),
      consult_type: 'directa',
      full_name: '',
      address: '',
      dni: '',
      kinship: '',
      consultation: '',
      referral: '',
    };
  }

  private localDate(): string {
    const today = new Date();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return `${today.getFullYear()}-${month}-${day}`;
  }

  private optionalValue(value: string): string | null {
    return value.trim() || null;
  }

  private describeError(error: unknown, fallback: string): string {
    if (error instanceof HttpErrorResponse && error.status === 0) {
      return 'No hay conexión con el servidor. Verificá que la API esté iniciada.';
    }
    if (
      error instanceof HttpErrorResponse &&
      typeof error.error?.detail === 'string'
    ) {
      return error.error.detail;
    }
    return fallback;
  }
}
