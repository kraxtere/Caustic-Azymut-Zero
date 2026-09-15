export interface Observation {
  id: string;
  timestampUtc: string;
  observerLatitudeDeg: number;
  observerLongitudeDeg: number;
  observerAltitudeM: number;
  target: string;
  measuredAzimuthDeg: number;
  measuredElevationDeg: number;
  azimuthUncertaintyDeg?: number;
  elevationUncertaintyDeg?: number;
  source?: string;
}
