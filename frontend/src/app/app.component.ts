import { DatePipe, DecimalPipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ContactInput, ContactRecord } from './contact.model';
import { ContactService } from './contact.service';
import { ListeningRecord, RecordInput } from './record.model';
import { RecordService } from './record.service';
import { Residence, ResidenceInput } from './residence.model';
import { ResidenceService } from './residence.service';

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
  private readonly contactService = inject(ContactService);
  private readonly residenceService = inject(ResidenceService);

  records: ListeningRecord[] = [];
  contacts: ContactRecord[] = [];
  residences: Residence[] = [];
  contactForm = this.emptyContactForm();
  residenceForm = this.emptyResidenceForm();
  currentPage: 'contact' | 'records' | 'residences' = 'contact';
  maintenanceMenuOpen = false;
  contactView: 'list' | 'form' = 'list';
  contactNameFilter = '';
  contactDateFilter = '';
  activeContactTab = 0;
  editingContactId: number | null = null;
  isLoadingContacts = false;
  isSavingContact = false;
  isDeletingContact = false;
  contactErrorMessage = '';
  contactSuccessMessage = '';
  editingResidenceId: number | null = null;
  isLoadingResidences = false;
  isSavingResidence = false;
  residenceErrorMessage = '';
  residenceSuccessMessage = '';
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
    this.loadContacts();
    this.loadResidences();
  }

  get contactTabs(): string[] {
    return [
      'DATOS PERSONALES',
      'PRIMER CONTACTO',
      'CONDICIONES DEL PRIMER CONTACTO',
      'CONSUMOS',
      'RESPUESTAS',
    ];
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

  get visibleContacts(): ContactRecord[] {
    const name = this.contactNameFilter.trim().toLocaleLowerCase('es');
    return this.contacts.filter((contact) => {
      const matchesName = (contact.full_name ?? '').toLocaleLowerCase('es').includes(name);
      const matchesDate =
        !this.contactDateFilter ||
        contact.contact_datetime?.slice(0, 10) === this.contactDateFilter;
      return matchesName && matchesDate;
    });
  }

  get hasContactFilters(): boolean {
    return Boolean(this.contactNameFilter.trim() || this.contactDateFilter);
  }

  clearContactFilters(): void {
    this.contactNameFilter = '';
    this.contactDateFilter = '';
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

  loadContacts(): void {
    this.isLoadingContacts = true;
    this.contactService.list().subscribe({
      next: (contacts) => {
        this.contacts = contacts;
        this.isLoadingContacts = false;
      },
      error: (error: unknown) => {
        this.contactErrorMessage = this.describeError(
          error,
          'No se pudieron cargar los primeros contactos.',
        );
        this.isLoadingContacts = false;
      },
    });
  }

  loadResidences(): void {
    this.isLoadingResidences = true;
    this.residenceErrorMessage = '';
    this.residenceService.list().subscribe({
      next: (residences) => {
        this.residences = residences;
        this.isLoadingResidences = false;
      },
      error: (error: unknown) => {
        this.residenceErrorMessage = this.describeError(
          error,
          'No se pudieron cargar las residencias.',
        );
        this.isLoadingResidences = false;
      },
    });
  }

  openResidences(): void {
    this.currentPage = 'residences';
    this.maintenanceMenuOpen = false;
    this.residenceSuccessMessage = '';
    this.loadResidences();
  }

  editResidence(residence: Residence): void {
    this.editingResidenceId = residence.id;
    this.residenceForm = {
      nombre_querido: residence.nombre_querido,
      direccion: residence.direccion,
      ocupacion: residence.ocupacion,
      capacidad: residence.capacidad,
    };
    this.residenceErrorMessage = '';
    this.residenceSuccessMessage = '';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  newResidence(): void {
    this.resetResidenceForm();
    this.residenceSuccessMessage = '';
  }

  saveResidence(): void {
    this.isSavingResidence = true;
    this.residenceErrorMessage = '';
    this.residenceSuccessMessage = '';
    const payload: ResidenceInput = {
      ...this.residenceForm,
      nombre_querido: this.residenceForm.nombre_querido.trim(),
      direccion: this.residenceForm.direccion.trim(),
    };
    const request = this.editingResidenceId === null
      ? this.residenceService.create(payload)
      : this.residenceService.update(this.editingResidenceId, payload);

    request.subscribe({
      next: (residence) => {
        this.residences = [
          ...this.residences.filter((item) => item.id !== residence.id),
          residence,
        ].sort((first, second) =>
          first.nombre_querido.localeCompare(second.nombre_querido, 'es'),
        );
        this.residenceSuccessMessage = this.editingResidenceId === null
          ? 'La residencia quedó registrada.'
          : 'Los cambios de la residencia se guardaron.';
        this.resetResidenceForm();
        this.isSavingResidence = false;
      },
      error: (error: unknown) => {
        this.residenceErrorMessage = this.describeError(error, 'No se pudo guardar la residencia.');
        this.isSavingResidence = false;
      },
    });
  }

  resetResidenceForm(): void {
    this.residenceForm = this.emptyResidenceForm();
    this.editingResidenceId = null;
  }

  saveContact(): void {
    if (this.contactForm.full_name.trim().length < 2) {
      this.contactErrorMessage = 'Ingresá el apellido y nombre para guardar el contacto.';
      this.activeContactTab = 0;
      return;
    }

    this.isSavingContact = true;
    this.contactErrorMessage = '';
    this.contactSuccessMessage = '';
    const payload: ContactInput = {
      ...this.contactForm,
      full_name: this.contactForm.full_name.trim(),
    };
    const request = this.editingContactId === null
      ? this.contactService.create(payload)
      : this.contactService.update(this.editingContactId, payload);

    request.subscribe({
      next: () => {
        this.contactSuccessMessage = this.editingContactId === null
          ? 'El primer contacto quedó registrado.'
          : 'Los cambios del contacto se guardaron.';
        this.resetContactForm();
        this.contactView = 'list';
        this.loadContacts();
        this.isSavingContact = false;
      },
      error: (error: unknown) => {
        this.contactErrorMessage = this.describeError(error, 'No se pudo guardar el contacto.');
        this.isSavingContact = false;
      },
    });
  }

  editContact(contact: ContactRecord): void {
    this.editingContactId = contact.id;
    this.contactView = 'form';
    this.contactForm = this.emptyContactForm();
    for (const key of Object.keys(this.contactForm) as (keyof ContactInput)[]) {
      this.contactForm[key] = contact[key] ?? '';
    }
    this.activeContactTab = 0;
    this.contactErrorMessage = '';
    this.contactSuccessMessage = '';
    this.currentPage = 'contact';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  newContact(): void {
    this.resetContactForm();
    this.contactSuccessMessage = '';
    this.contactView = 'form';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  showContactList(): void {
    this.resetContactForm();
    this.contactSuccessMessage = '';
    this.currentPage = 'contact';
    this.contactView = 'list';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  deleteContact(contact: ContactRecord): void {
    if (!window.confirm(`¿Eliminar el primer contacto de ${contact.full_name}?`)) {
      return;
    }

    this.isDeletingContact = true;
    this.contactErrorMessage = '';
    this.contactService.delete(contact.id).subscribe({
      next: () => {
        this.contacts = this.contacts.filter((item) => item.id !== contact.id);
        if (this.editingContactId === contact.id) {
          this.resetContactForm();
        }
        this.contactSuccessMessage = 'El primer contacto se eliminó.';
        this.isDeletingContact = false;
      },
      error: (error: unknown) => {
        this.contactErrorMessage = this.describeError(error, 'No se pudo eliminar el contacto.');
        this.isDeletingContact = false;
      },
    });
  }

  resetContactForm(): void {
    this.contactForm = this.emptyContactForm();
    this.editingContactId = null;
    this.activeContactTab = 0;
    this.contactErrorMessage = '';
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

  private emptyResidenceForm(): ResidenceInput {
    return {
      nombre_querido: '',
      direccion: '',
      ocupacion: 0,
      capacidad: 0,
    };
  }

  private emptyContactForm(): ContactInput {
    return {
      date_and_place: '',
      full_name: '',
      birth_date: '',
      self_perceived_gender: '',
      dni: '',
      housing_situation: '',
      residence_address: '',
      phone: '',
      contact_datetime: '',
      access_mode: '',
      manifest_demand: '',
      latent_demand: '',
      affective_references: '',
      household_structure: '',
      literacy: '',
      education_level: '',
      employment_situation: '',
      disability: '',
      disability_details: '',
      health: '',
      violence_present: '',
      violence_details: '',
      legal_conflict: '',
      rights_accessibility: '',
      substance: '',
      frequency: '',
      medication_treatment: '',
      consumption_observations: '',
      previous_treatments: '',
      first_response: '',
      accompaniment_proposals: '',
      participation_activities: '',
      activity: '',
      activity_day_time: '',
      activity_place: '',
      activity_referent: '',
      second_response: '',
      follow_up_observations: '',
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
