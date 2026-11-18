export interface ResidenceInput {
  nombre_querido: string;
  direccion: string;
  ocupacion: string;
  capacidad: number;
}

export interface Residence extends ResidenceInput {
  id: number;
  created_at: string;
}
