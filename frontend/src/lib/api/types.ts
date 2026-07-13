import { api } from './client';

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  email: string;
  name: string | null;
  preferred_units: string;
  weight_kg: number | null;
  ftp_watts: number | null;
  max_hr: number | null;
  resting_hr: number | null;
  is_admin: boolean;
}

export interface DistanceSplit {
  split_km: number;
  cumulative_time_s: number;
  cumulative_speed_kmh: number;
  segment_time_s: number;
  segment_speed_kmh: number;
}

export interface ActivityStats {
  distance_m: number | null;
  duration_s: number | null;
  moving_time_s: number | null;
  elevation_gain: number | null;
  elevation_loss: number | null;
  avg_speed: number | null;
  max_speed: number | null;
  avg_hr: number | null;
  max_hr: number | null;
  avg_power: number | null;
  max_power: number | null;
  avg_cadence: number | null;
  calories: number | null;
  polyline: string | null;
  simplified_time_series: string | null;
  elevation_profile: string | null;
  min_lat: number | null;
  max_lat: number | null;
  min_lng: number | null;
  max_lng: number | null;
  distance_splits?: DistanceSplit[];
}

export interface Lap {
  id: number;
  lap_index: number;
  distance_m: number | null;
  duration_s: number | null;
  avg_speed: number | null;
  max_speed: number | null;
  avg_hr: number | null;
  max_hr: number | null;
  avg_power: number | null;
  max_power: number | null;
  avg_cadence: number | null;
  calories: number | null;
}

export interface Activity {
  id: number;
  user_id: number;
  name: string;
  sport_type: string;
  start_time: string;
  timezone: string | null;
  source: string;
  gear_id: number | null;
  notes: string | null;
  rpe: number | null;
  created_at: string;
  updated_at: string;
  stats: ActivityStats | null;
  laps: Lap[];
}

export interface ActivitySummary {
  id: number;
  name: string;
  sport_type: string;
  start_time: string;
  distance_m: number | null;
  duration_s: number | null;
  elevation_gain: number | null;
  avg_speed: number | null;
  avg_hr: number | null;
  max_hr: number | null;
  calories: number | null;
}

export interface ActivityListResponse {
  items: ActivitySummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface Gear {
  id: number;
  user_id: number;
  name: string;
  gear_type: string;
  brand: string | null;
  model: string | null;
  notes: string | null;
  retired: boolean;
  retired_at: string | null;
  maintenance_interval_km: number | null;
  last_service_date: string | null;
  last_service_distance_m: number | null;
  created_at: string;
}

export interface GearStats {
  gear_id: number | null;
  gear_name: string;
  gear_type: string;
  retired: boolean;
  maintenance_interval_km: number | null;
  last_service_date: string | null;
  last_service_distance_m: number | null;
  workout_count: number;
  total_distance_m: number;
  avg_distance_m: number;
  total_elevation_m: number;
  total_moving_time_s: number;
  avg_speed: number;
  total_calories: number;
}

export interface PeriodStats {
  distance_m: number;
  duration_s: number;
  elevation_gain: number;
  activity_count: number;
}

export interface MonthlyVolume {
  month: string;
  count: number;
  distance_m: number;
  duration_s: number;
  elevation_m: number;
  calories: number;
}

export interface SportVolume {
  sport_type: string;
  count: number;
  distance_m: number;
  duration_s: number;
}

export interface VolumeResponse {
  monthly: MonthlyVolume[];
  by_sport: SportVolume[];
}

export interface PersonalRecord {
  activity_id: number;
  name: string;
  sport_type: string;
  start_time: string;
  value: number;
}

export interface PersonalRecordsResponse {
  longest_distance: PersonalRecord | null;
  longest_duration: PersonalRecord | null;
  highest_elevation: PersonalRecord | null;
  fastest_speed: PersonalRecord | null;
  highest_hr: PersonalRecord | null;
  max_speed: PersonalRecord | null;
}

export interface SportBreakdown {
  sport_type: string;
  distance_m: number;
  duration_s: number;
  activity_count: number;
}

export interface DashboardResponse {
  week: PeriodStats;
  prev_week: PeriodStats;
  month: PeriodStats;
  prev_month: PeriodStats;
  year: PeriodStats;
  prev_year: PeriodStats;
  all_time: PeriodStats;
  by_sport: SportBreakdown[];
  recent: ActivitySummary[];
}

export interface EddingtonResponse {
  eddington_number: number;
  next_milestone: number;
  activities_qualified_for_next: number;
  activities_needed_for_next: number;
  unit_label: string;
  distribution: { threshold: number; count: number }[];
  qualifying_activities: {
    id: number;
    name: string;
    sport_type: string;
    start_time: string;
    distance_m: number;
    distance_converted: number;
  }[];
}

export interface HeatmapDay {
  date: string;
  distance_m: number;
  moving_time_s: number;
  calories: number;
}

export interface RouteItem {
  id: number;
  name: string;
  sport_type: string;
  start_time: string;
  polyline: string;
  distance_m: number;
}

export interface UserZone {
  id: number;
  user_id: number;
  zone_type: string;
  zone_1_min: number | null;
  zone_1_max: number | null;
  zone_2_min: number | null;
  zone_2_max: number | null;
  zone_3_min: number | null;
  zone_3_max: number | null;
  zone_4_min: number | null;
  zone_4_max: number | null;
  zone_5_min: number | null;
  zone_5_max: number | null;
}

export const authApi = {
  register: (email: string, password: string, name?: string) =>
    api.post<TokenResponse>('/auth/register', { email, password, name }),

  login: (email: string, password: string) =>
    api.post<TokenResponse>('/auth/login', { email, password }),

  logout: () => api.post<{ ok: boolean }>('/auth/logout'),
};

export interface ActivityFilters {
  sport_type?: string;
  source?: string;
  gear_id?: number;
  date_from?: string;
  date_to?: string;
  distance_min?: number;
  distance_max?: number;
  elevation_min?: number;
  elevation_max?: number;
}

export const activitiesApi = {
  list: (page = 1, pageSize = 20, filters?: ActivityFilters) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.set(key, String(value));
        }
      });
    }
    return api.get<ActivityListResponse>(`/activities?${params}`);
  },

  get: (id: number) => api.get<Activity>(`/activities/${id}`),

  upload: (file: File, gearId?: number) => api.upload<Activity>('/activities/upload', file, gearId ? { gear_id: gearId } : undefined),

  update: (id: number, data: Partial<{ name: string; sport_type: string; notes: string; rpe: number; gear_id: number | null }>) =>
    api.put<Activity>(`/activities/${id}`, data),

  delete: (id: number) => api.del(`/activities/${id}`),
};

export const statsApi = {
  dashboard: () => api.get<DashboardResponse>('/stats/dashboard'),

  eddington: () => api.get<EddingtonResponse>('/stats/eddington'),

  heatmap: () => api.get<HeatmapDay[]>('/stats/heatmap'),

  routes: (sportType?: string, year?: number) => {
    const params = new URLSearchParams();
    if (sportType) params.set('sport_type', sportType);
    if (year) params.set('year', String(year));
    return api.get<RouteItem[]>(`/stats/activity-routes?${params}`);
  },

  volume: (year?: number) => {
    const params = year ? `?year=${year}` : '';
    return api.get<VolumeResponse>(`/stats/volume${params}`);
  },

  personalRecords: (sportType?: string, year?: number) => {
    const params = new URLSearchParams();
    if (sportType) params.set('sport_type', sportType);
    if (year) params.set('year', String(year));
    return api.get<PersonalRecordsResponse>(`/stats/personal-records?${params}`);
  },

  availableYears: () => api.get<number[]>('/stats/available-years'),
};

export const userApi = {
  me: () => api.get<User>('/me'),

  update: (data: Partial<{ name: string; preferred_units: string; weight_kg: number; ftp_watts: number; max_hr: number; resting_hr: number }>) =>
    api.put<User>('/me', data),

  list: () => api.get<User[]>('/users'),

  setAdmin: (id: number, is_admin: boolean) => {
    const form = new FormData();
    form.append('is_admin', String(is_admin));
    return api.put<User>(`/users/${id}/admin`, form);
  },
};

export const zonesApi = {
  list: () => api.get<UserZone[]>('/zones'),

  create: (data: { zone_type: string; zone_1_min?: number; zone_1_max?: number; zone_2_min?: number; zone_2_max?: number; zone_3_min?: number; zone_3_max?: number; zone_4_min?: number; zone_4_max?: number; zone_5_min?: number; zone_5_max?: number }) =>
    api.post<UserZone>('/zones', data),

  update: (id: number, data: Partial<{ zone_1_min: number; zone_1_max: number; zone_2_min: number; zone_2_max: number; zone_3_min: number; zone_3_max: number; zone_4_min: number; zone_4_max: number; zone_5_min: number; zone_5_max: number }>) =>
    api.put<UserZone>(`/zones/${id}`, data),

  delete: (id: number) => api.del(`/zones/${id}`),
};

export const gearApi = {
  list: () => api.get<Gear[]>('/gear'),

  stats: () => api.get<GearStats[]>('/gear/stats'),

  create: (data: { name: string; gear_type: string; brand?: string; model?: string; notes?: string; maintenance_interval_km?: number }) =>
    api.post<Gear>('/gear', data),

  update: (id: number, data: Partial<{ name: string; gear_type: string; brand: string; model: string; notes: string; retired: boolean; maintenance_interval_km: number; last_service_date: string; last_service_distance_m: number }>) =>
    api.put<Gear>(`/gear/${id}`, data),

  markServiced: (id: number) => api.post<Gear>(`/gear/${id}/service`),

  delete: (id: number) => api.del(`/gear/${id}`),
};

export interface SessionTarget {
  type: string;
  value: number | null;
  unit: string | null;
}

export interface TrainingSession {
  id: number;
  plan_id: number;
  scheduled_date: string;
  sport_type: string | null;
  name: string | null;
  description: string | null;
  targets: SessionTarget[];
  intervals: string | null;
  notes: string | null;
  rest_day: boolean;
  activity_id: number | null;
  block_id: number | null;
  status: string;
  created_at: string;
}

export interface TrainingBlock {
  id: number;
  plan_id: number;
  name: string;
  description: string | null;
  focus: string | null;
  block_type: string;
  sort_order: number;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
  sessions: TrainingSession[];
}

export interface TrainingPlan {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
  sessions: TrainingSession[];
  blocks: TrainingBlock[];
}

export const trainingApi = {
  listPlans: () => api.get<TrainingPlan[]>('/training/plans'),

  getPlan: (id: number) => api.get<TrainingPlan>(`/training/plans/${id}`),

  createPlan: (data: { name: string; description?: string; start_date?: string; end_date?: string }) =>
    api.post<TrainingPlan>('/training/plans', data),

  updatePlan: (id: number, data: Partial<{ name: string; description: string; start_date: string; end_date: string }>) =>
    api.put<TrainingPlan>(`/training/plans/${id}`, data),

  deletePlan: (id: number) => api.del(`/training/plans/${id}`),

  createSession: (planId: number, data: { scheduled_date: string; sport_type?: string; name?: string; description?: string; targets?: SessionTarget[]; intervals?: string; notes?: string; rest_day?: boolean; block_id?: number }) =>
    api.post<TrainingSession>(`/training/plans/${planId}/sessions`, data),

  updateSession: (id: number, data: Partial<{ scheduled_date: string; sport_type: string; name: string; description: string; targets: SessionTarget[]; intervals: string; notes: string; rest_day: boolean; block_id: number | null; status: string }>) =>
    api.put<TrainingSession>(`/training/sessions/${id}`, data),

  deleteSession: (id: number) => api.del(`/training/sessions/${id}`),

  createBlock: (planId: number, data: { name: string; description?: string; focus?: string; block_type?: string; sort_order?: number; start_date?: string; end_date?: string }) =>
    api.post<TrainingBlock>(`/training/plans/${planId}/blocks`, data),

  listBlocks: (planId: number) => api.get<TrainingBlock[]>(`/training/plans/${planId}/blocks`),

  getBlock: (blockId: number) => api.get<TrainingBlock>(`/training/blocks/${blockId}`),

  updateBlock: (blockId: number, data: Partial<{ name: string; description: string; focus: string; block_type: string; sort_order: number; start_date: string; end_date: string }>) =>
    api.put<TrainingBlock>(`/training/blocks/${blockId}`, data),

  deleteBlock: (blockId: number) => api.del(`/training/blocks/${blockId}`),

  insights: () => api.get<TrainingInsights>('/training/insights'),

  ctl: (days: number = 90) => api.get<CtlResponse>(`/training/ctl?days=${days}`),

  weeklyVolume: (planId: number, weeks: number = 24) => api.get<WeeklyVolumeResponse>(`/training/weekly-volume?plan_id=${planId}&weeks=${weeks}`),
};

export interface WeeklyVolume {
  week_start: string;
  distance_m: number;
  duration_s: number;
  moving_time_s: number;
  count: number;
}

export interface PaceTrendPoint {
  week_start: string;
  avg_speed: number | null;
}

export interface TrainingInsights {
  weekly_volume: WeeklyVolume[];
  pace_trends: Record<string, PaceTrendPoint[]>;
  consistency_streak: number;
  total_weeks: number;
}

export interface CtlDataPoint {
  date: string;
  training_load: number;
  ctl: number;
  atl: number;
  tsb: number;
}

export interface AcwrInfo {
  value: number;
  acute_load: number;
  chronic_load: number | null;
  status: string;
  color: string;
  guidance: string;
}

export interface CtlResponse {
  days: number;
  data: CtlDataPoint[];
  acwr: AcwrInfo | null;
  sport_load: SportLoad[];
  weekly_loads: WeeklyLoad[];
}

export interface SportLoad {
  sport_type: string;
  total_load: number;
  count: number;
}

export interface WeeklyLoad {
  week_start: string;
  load: number;
}

export interface SportVolume {
  distance_m: number;
  duration_s: number;
  count: number;
}

export interface WeeklyVolumeWeek {
  week_start: string;
  planned: Record<string, SportVolume>;
  actual: Record<string, SportVolume>;
  total_planned_distance_m: number;
  total_planned_duration_s: number;
  total_planned_count: number;
  total_actual_distance_m: number;
  total_actual_duration_s: number;
  total_actual_count: number;
}

export interface WeeklyVolumeResponse {
  plan_id: number;
  weeks: WeeklyVolumeWeek[];
}

export interface Waypoint {
  lat: number;
  lng: number;
}

export interface ElevationPoint {
  distance: number;
  elevation: number;
}

export interface Route {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  waypoints: Waypoint[];
  route_polyline: string | null;
  distance_m: number;
  elevation_gain_m: number | null;
  elevation_loss_m: number | null;
  elevation_profile: ElevationPoint[];
  sport_type: string | null;
  created_at: string;
  updated_at: string;
}

export interface RoutePlanResponse {
  polyline: string;
  distance_m: number;
  waypoints: Waypoint[];
}

export interface RouteElevationResponse {
  elevation_profile: ElevationPoint[];
  elevation_gain_m: number;
  elevation_loss_m: number;
}

export interface Segment {
  id: number;
  user_id: number;
  creator_name: string | null;
  name: string;
  description: string | null;
  sport_type: string | null;
  start_lat: number;
  start_lng: number;
  end_lat: number;
  end_lng: number;
  polyline: string | null;
  distance_m: number | null;
  elevation_gain_m: number | null;
  created_at: string;
  best_time: number | null;
  effort_count: number;
}

export interface SegmentListItem {
  id: number;
  name: string;
  sport_type: string | null;
  distance_m: number | null;
  best_time: number | null;
  effort_count: number;
  creator_name: string | null;
  created_at: string;
}

export interface SegmentEffort {
  id: number;
  segment_id: number;
  activity_id: number;
  user_id: number;
  user_name: string | null;
  activity_name: string | null;
  activity_start_time: string | null;
  elapsed_time_s: number;
  avg_speed: number | null;
  avg_hr: number | null;
  avg_power: number | null;
  start_time: string;
  created_at: string;
}

export interface SegmentPR {
  id: number | null;
  elapsed_time_s: number | null;
  avg_speed: number | null;
  avg_hr: number | null;
  avg_power: number | null;
  start_time: string | null;
  activity_id: number | null;
}

export interface SegmentLeaderboardEntry {
  rank: number;
  user_name: string | null;
  elapsed_time_s: number;
  avg_speed: number | null;
  activity_id: number;
  start_time: string;
}

export const segmentApi = {
  list: (sportType?: string, search?: string) => {
    const params = new URLSearchParams();
    if (sportType) params.set('sport_type', sportType);
    if (search) params.set('search', search);
    return api.get<SegmentListItem[]>(`/segments?${params}`);
  },

  get: (id: number) => api.get<Segment>(`/segments/${id}`),

  create: (data: { name: string; description?: string; sport_type?: string; start_lat: number; start_lng: number; end_lat: number; end_lng: number; polyline?: string; distance_m?: number; elevation_gain_m?: number }) =>
    api.post<Segment>('/segments', data),

  update: (id: number, data: Partial<{ name: string; description: string; sport_type: string }>) =>
    api.put<Segment>(`/segments/${id}`, data),

  delete: (id: number) => api.del(`/segments/${id}`),

  efforts: (segmentId: number) => api.get<SegmentEffort[]>(`/segments/${segmentId}/efforts`),

  pr: (segmentId: number) => api.get<SegmentPR>(`/segments/${segmentId}/pr`),

  leaderboard: (segmentId: number, limit: number = 10) =>
    api.get<SegmentLeaderboardEntry[]>(`/segments/${segmentId}/leaderboard?limit=${limit}`),

  deleteEffort: (segmentId: number, effortId: number) =>
    api.del(`/segments/${segmentId}/efforts/${effortId}`),

  matchActivities: (segmentId: number) =>
    api.post<{ matched: number; segment_id: number }>(`/segments/${segmentId}/match`),
};

export const routeApi = {
  list: () => api.get<Route[]>('/routes'),

  get: (id: number) => api.get<Route>(`/routes/${id}`),

  create: (data: { name: string; description?: string; waypoints: Waypoint[]; route_polyline?: string; distance_m?: number; elevation_gain_m?: number; elevation_loss_m?: number; elevation_profile?: ElevationPoint[]; sport_type?: string }) =>
    api.post<Route>('/routes', data),

  update: (id: number, data: Partial<{ name: string; description: string; waypoints: Waypoint[]; route_polyline: string; distance_m: number; elevation_gain_m: number; elevation_loss_m: number; elevation_profile: ElevationPoint[]; sport_type: string }>) =>
    api.put<Route>(`/routes/${id}`, data),

  delete: (id: number) => api.del(`/routes/${id}`),

  plan: (waypoints: Waypoint[]) =>
    api.post<RoutePlanResponse>('/routes/plan', { waypoints }),

  elevation: (points: Waypoint[]) =>
    api.post<RouteElevationResponse>('/routes/elevation', { points }),
};

