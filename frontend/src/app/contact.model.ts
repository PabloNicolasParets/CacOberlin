export interface ContactInput {
  date_and_place: string;
  full_name: string;
  birth_date: string;
  self_perceived_gender: string;
  dni: string;
  housing_situation: string;
  residence_address: string;
  phone: string;
  contact_datetime: string;
  access_mode: string;
  manifest_demand: string;
  latent_demand: string;
  affective_references: string;
  household_structure: string;
  literacy: string;
  education_level: string;
  employment_situation: string;
  disability: string;
  disability_details: string;
  health: string;
  violence_present: string;
  violence_details: string;
  legal_conflict: string;
  rights_accessibility: string;
  substance: string;
  frequency: string;
  medication_treatment: string;
  consumption_observations: string;
  previous_treatments: string;
  first_response: string;
  accompaniment_proposals: string;
  participation_activities: string;
  activity: string;
  activity_day_time: string;
  activity_place: string;
  activity_referent: string;
  second_response: string;
  follow_up_observations: string;
}

export type ContactRecord = {
  [Key in keyof ContactInput]: string | null;
} & {
  id: number;
  created_at: string;
};
