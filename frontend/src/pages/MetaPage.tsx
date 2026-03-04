import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { MetaData } from '../types';
import { KPICard } from '../components/meta/KPICard';
import { ViolinChart } from '../components/meta/ViolinChart';
import { TERChart } from '../components/meta/TERChart';
import { BumpChart } from '../components/meta/BumpChart';
import { ShiftRankTable } from '../components/meta/ShiftRankTable';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ColdStartOverlay } from '../components/common/ColdStartOverlay';
import { ErrorCard } from '../components/common/ErrorCard';
import { useApi as useVersionListApi } from '../hooks/useApi';

const TYPE_OPTIONS = ['전체', '전사', '마법사', '궁수', '도적', '해적'];

export function MetaPage() {
  const { data: versions } = useVersionListApi<string[]>('/api/version/list');
  const [selectedVersion, setSelectedVersion] = useState('');
  const [selectedType, setSelectedType] = useState('전체');

  useEffect(() => {
    if (versions?.length && !selectedVersion) {
      setSelectedVersion(versions[0]);
    }
  }, [versions, selectedVersion]);

  const url = selectedVersion
    ? `/api/meta?type=${encodeURIComponent(selectedType)}&version=${encodeURIComponent(selectedVersion)}`
    : null;

  const { data, loading, error, isColdStart, refetch } = useApi<MetaData>(url, [selectedVersion, selectedType]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      <ColdStartOverlay visible={isColdStart} />

      {/* 필터 */}
      <div className="flex flex-wrap items-center gap-4">
        <select
          value={selectedVersion}
          onChange={(e) => setSelectedVersion(e.target.value)}
          className="bg-[#1A1D2E] border border-[#2A2D3E] text-[#F1F5F9] text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-[#FF8C00]"
        >
          {(versions ?? []).map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        <div className="flex gap-1 flex-wrap">
          {TYPE_OPTIONS.map((t) => (
            <button
              key={t}
              onClick={() => setSelectedType(t)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                selectedType === t
                  ? 'bg-[#FF8C00] text-[#0F1117]'
                  : 'bg-[#1A1D2E] text-[#94A3B8] border border-[#2A2D3E] hover:text-[#F1F5F9]'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {loading && <LoadingSpinner size="lg" className="py-16" />}
      {error && <ErrorCard message={error} onRetry={refetch} />}

      {data && !loading && (
        <>
          {/* KPI 카드 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPICard
              title="밸런스 점수"
              value={data.balance_score}
              caption={data.balance_message ?? undefined}
              subtitle={
                data.balance_top_job
                  ? `1위: ${data.balance_top_job} (${((data.balance_top_share ?? 0) * 100).toFixed(1)}%), CR3: ${((data.balance_cr3 ?? 0) * 100).toFixed(1)}%`
                  : undefined
              }
            />
            <KPICard
              title="참여·성과 변동"
              value={data.shift_kpi?.outcome ?? null}
              caption="참여율, 50층 달성률, 최고 층수 등"
            />
            <KPICard
              title="스탯 변동"
              value={data.shift_kpi?.stat ?? null}
              caption="헥사코어, 어빌리티, 하이퍼스탯"
            />
            <KPICard
              title="빌드 변동"
              value={data.shift_kpi?.build ?? null}
              caption="스타포스, 세트효과, 무기 등"
            />
          </div>

          {/* 직업별 층수 분포 */}
          <div className="card">
            <h3 className="text-sm font-bold text-[#F1F5F9] mb-4">직업별 층수 분포 (Top10)</h3>
            <ViolinChart data={data.violin} />
          </div>

          {/* TER 분포 */}
          <div className="card">
            <h3 className="text-sm font-bold text-[#F1F5F9] mb-1">TER 분포</h3>
            <p className="text-xs text-[#64748B] mb-3">시간 효율 비율 분포 (분당 클리어 층수) — 40~69층 기준</p>
            <TERChart data={data.ter} />
          </div>

          {/* Bump Chart */}
          <div className="card">
            <h3 className="text-sm font-bold text-[#F1F5F9] mb-4">직업별 50층 달성률 순위 추이</h3>
            <BumpChart
              data={data.bump}
              versionChanges={data.version_changes}
              xaxisRange={data.bump_xaxis_range}
            />
          </div>

          {/* Shift Rank 테이블 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ShiftRankTable title="직업별 shift 랭크 (50층 세그먼트)" data={data.shift_rank_50.slice(0, 5)} />
            <ShiftRankTable title="직업별 shift 랭크 (상위권 세그먼트)" data={data.shift_rank_upper.slice(0, 5)} />
          </div>
        </>
      )}
    </div>
  );
}
