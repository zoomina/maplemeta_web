export interface NoticeItem {
  title: string;
  url: string;
  date: string;
}

export interface EventItem {
  title: string;
  url: string;
  period: string;
  dday: string;
  thumbnail: string;
}

export interface VersionDetail {
  version: string;
  type_list: string[];
  impacted_job_list: string[];
  start_date: string | null;
  end_date: string | null;
}

export interface ViolinJobData {
  job_name: string;
  color: string;
  img: string;
  n: number;
  floor_max: number;
  floor_min: number;
  floor_avg: number;
  floor_median: number;
  floor_q1: number | null;
  floor_q3: number | null;
  density: [number, number][];
}

export interface TERJobData {
  job_name: string;
  ter_p50: number;
  floor50_rate: number;
}

export interface BumpPoint {
  date: string;
  job_name: string;
  rank: number;
  rate: number;
  rate_delta_str: string;
  achieved: number;
  total: number;
  img: string;
  color: string;
}

export interface MetaData {
  balance_score: number | null;
  balance_message: string | null;
  balance_top_job: string | null;
  balance_top_share: number | null;
  balance_cr3: number | null;
  shift_kpi: { outcome: number | null; stat: number | null; build: number | null } | null;
  violin: ViolinJobData[];
  ter: TERJobData[];
  bump: BumpPoint[];
  version_changes: { date: string; version: string }[];
  bump_xaxis_range: [string, string] | null;
  shift_rank_50: Record<string, unknown>[];
  shift_rank_upper: Record<string, unknown>[];
  selected_version: string;
}

export interface JobItem {
  job: string;
  img: string;
  type?: string;
  category?: string;
  main_stat?: string;
  color?: string;
}

export interface JobDetail {
  job: string;
  category: string;
  type: string;
  main_stat: string;
  description: string;
  img_full_resolved: string | null;
  img: string;
  floor50_rate: string | null;
  shift_score: string | null;
  link_skill_icon: string;
  link_skill_name: string;
}

export interface RadarData {
  labels: string[];
  segment50: number[];
  segmentUpper: number[];
}

export interface CompareItem {
  value: number;
  current: number;
  previous: number;
}

export interface JobStats {
  selected_version: string;
  previous_version: string;
  radar: RadarData | null;
  main_stat_compare: CompareItem[];
  hexacore_compare: CompareItem[];
  hexacore_top5: Record<string, unknown>[];
  hyper_top5: Record<string, unknown>[];
  ability_boss_top3: Record<string, unknown>[];
  ability_field_top3: Record<string, unknown>[];
  starforce_compare: CompareItem[];
  set_effect_top5: Record<string, unknown>[];
  weapon_top5: Record<string, unknown>[];
  subweapon_top5: Record<string, unknown>[];
  extra_option_top5: Record<string, unknown>[];
  potential_top5: Record<string, unknown>[];
}

export interface VersionItem {
  version: string;
  start_date: string | null;
}
