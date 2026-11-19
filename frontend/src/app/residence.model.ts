export interface ResidenceInput {
  nombre_querido: string;
  direccion: string;
  ocupacion: number;
  capacidad: number;
}

export interface Residence extends ResidenceInput {
  id: number;
  created_at: string;
}
