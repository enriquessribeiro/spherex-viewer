// Tipos do contrato de dados (schemas/field.schema.json, schemas/manifest.schema.json).
import type { Wcs } from "./wcs";
import type { Stretch } from "./stretch";

export type Detector = "D1" | "D2" | "D3" | "D4" | "D5" | "D6";
export const DETECTORS: Detector[] = ["D1", "D2", "D3", "D4", "D5", "D6"];

export interface FrameDoc {
  n_exposures: number;
  mjd_mean: number;
  lambda_min_um: number;
  lambda_max_um: number;
  background: number;
  frame: string;
  variance: string;
  mask: string;
  png: string;
}

export interface EpochDoc {
  index: number;
  mjd_start: number;
  mjd_end: number;
  mjd_mid: number;
  date_start: string;
  date_end: string;
  frames: Partial<Record<Detector, FrameDoc>>;
  exposures: { id: string; det: Detector; mjd: number; collection?: string }[];
}

export interface TargetDoc {
  id: string;
  name: string;
  description?: string;
  pm_ra_masyr: number;
  pm_dec_masyr: number;
  ref_mjd: number;
  predicted_positions: { epoch: number; ra: number; dec: number }[];
}

export interface FieldDoc {
  schema_version: 1;
  field_id: string;
  data_version: string;
  status: "ready";
  generated_at: string;
  center: { ra: number; dec: number };
  fov_arcmin: number;
  grid: { n: number; pixel_scale_arcsec: number; row_order?: "north_first"; wcs: Wcs };
  collections: string[];
  latest_exposure_mjd: number;
  base_url: string;
  epochs: EpochDoc[];
  display: Partial<Record<Detector, { stretch: Stretch; vmin: number; vmax: number }>>;
  failed_exposures: string[];
  target?: TargetDoc;
}
