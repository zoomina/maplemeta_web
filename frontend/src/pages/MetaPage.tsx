// MetaPage 변경 사항 (260313_update.md):
// - 항목 2: KPI 카드 게이지 차트 디자인 (KPICard type 속성 추가), shift score 방향성 + 구간 해석 메시지
// - 항목 3: 각 차트마다 설명 텍스트 추가
// - 항목 4: 상단 KPI 카드에 shift 해석 텍스트 추가 (구간별 메시지)
// - 항목 5: 버전 선택 옆 날짜 표시, 패치 정보 카드 추가

import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { MetaData, VersionItem, VersionDetail } from '../types';
import { KPICard } from '../components/meta/KPICard';
import { ViolinChart } from '../components/meta/ViolinChart';
import { TERChart } from '../components/meta/TERChart';
import { BumpChart } from '../components/meta/BumpChart';
import { ShiftRankTable } from '../components/meta/ShiftRankTable';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ColdStartOverlay } from '../components/common/ColdStartOverlay';
import { ErrorCard } from '../components/common/ErrorCard';

const TYPE_OPTIONS = ['전체', '전사', '마법사', '궁수', '도적', '해적'];

// Shift score 구간별 해석 메시지 (260313_update.md)
function shiftCaption(val: number | null | undefined, axis: 'outcome' | 'stat' | 'build'): string {
  if (val == null) return '';
  const v = val;
  if (axis === 'outcome') {
    if (v >= 15) return '패치 이후 메타 성과가 전반적으로 크게 상승했습니다. 동일한 스펙 대비 성과가 눈에 띄게 개선되었습니다.';
    if (v >= 3)  return '패치 이후 일부 직업의 성과가 상승하며 메타 환경에 긍정적인 변화가 나타나고 있습니다.';
    if (v > -3)  return '패치 이후 메타 성과 변화는 크지 않습니다. 기존 메타 구조가 유지되고 있습니다.';
    if (v >= -15) return '패치 이후 일부 직업의 성과가 감소하며 메타 환경이 다소 약화된 모습입니다.';
    return '패치 이후 메타 성과가 전반적으로 감소했습니다. 게임 난이도가 상승한 방향으로 변화했습니다.';
  }
  if (axis === 'stat') {
    if (v >= 15) return '패치 이후 요구 스탯 수준이 크게 상승했습니다. 전반적으로 더 높은 스펙 투자가 필요한 환경입니다.';
    if (v >= 3)  return '요구 스탯 수준이 다소 상승했습니다. 기존보다 약간 높은 세팅이 필요한 경향입니다.';
    if (v > -3)  return '요구 스탯 수준 변화는 크지 않습니다. 기존 세팅 수준이 유지되고 있습니다.';
    if (v >= -15) return '요구 스탯 수준이 일부 완화되었습니다. 이전보다 약간 낮은 스펙에서도 비슷한 성과를 낼 수 있습니다.';
    return '요구 스탯 수준이 크게 완화되었습니다. 전반적인 플레이 요구 스펙이 낮아진 상태입니다.';
  }
  // build
  if (v >= 15) return '패치 이후 장비 세팅 요구가 크게 증가했습니다. 새로운 세팅이 필요한 환경으로 변화했습니다.';
  if (v >= 3)  return '장비 세팅 변화가 일부 나타나고 있습니다. 기존 세팅에서 약간의 조정이 필요한 상황입니다.';
  if (v > -3)  return '장비 세팅 변화는 크지 않습니다. 기존 빌드 구조가 유지되고 있습니다.';
  if (v >= -15) return '장비 세팅 요구가 일부 완화되었습니다. 기존보다 단순한 세팅으로도 플레이 가능합니다.';
  return '장비 세팅 부담이 크게 줄어들었습니다. 세팅 복잡도와 적응 부담이 전반적으로 완화되었습니다.';
}

export function MetaPage() {
  const { data: versionsFull } = useApi<VersionItem[]>('/api/version/list-full');
  const [selectedVersion, setSelectedVersion] = useState('');
  const [selectedType, setSelectedType] = useState('전체');

  useEffect(() => {
    if (versionsFull?.length && !selectedVersion) {
      setSelectedVersion(versionsFull[0].version);
    }
  }, [versionsFull, selectedVersion]);

  const url = selectedVersion
    ? `/api/meta?type=${encodeURIComponent(selectedType)}&version=${encodeURIComponent(selectedVersion)}`
    : null;

  const { data, loading, error, isColdStart, refetch } = useApi<MetaData>(url, [selectedVersion, selectedType]);

  // 선택된 버전의 패치 상세 정보 (항목 5)
  const { data: versionDetail } = useApi<VersionDetail>(
    selectedVersion ? `/api/version/${encodeURIComponent(selectedVersion)}` : null,
    [selectedVersion]
  );

  const selectedVersionItem = versionsFull?.find((v) => v.version === selectedVersion);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      <ColdStartOverlay visible={isColdStart} />

      {/* 필터 */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <select
            value={selectedVersion}
            onChange={(e) => setSelectedVersion(e.target.value)}
            className="bg-[#1A1D2E] border border-[#2A2D3E] text-[#F1F5F9] text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-[#FF8C00]"
          >
            {(versionsFull ?? []).map((v) => (
              <option key={v.version} value={v.version}>
                {v.version}{v.start_date ? ` (${v.start_date})` : ''}
              </option>
            ))}
          </select>
          {selectedVersionItem?.start_date && (
            <span className="text-xs text-[#64748B]">{selectedVersionItem.start_date}</span>
          )}
        </div>
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

      {/* 패치 정보 카드 (항목 5: 패치노트와 동일 형태) */}
      {versionDetail && (
        <div className="card space-y-2">
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-base font-bold text-[#FF8C00]">{versionDetail.version}</span>
            {versionDetail.type_list.map((t) => (
              <span key={t} className="badge badge-accent">{t}</span>
            ))}
          </div>
          {versionDetail.impacted_job_list.length > 0 && (
            <div className="flex flex-wrap items-center gap-1">
              <span className="text-xs text-[#94A3B8] font-semibold mr-1">업데이트 직업</span>
              {versionDetail.impacted_job_list.map((j) => (
                <span key={j} className="badge">{j}</span>
              ))}
            </div>
          )}
          {(versionDetail.start_date || versionDetail.end_date) && (
            <p className="text-xs text-[#64748B]">
              {versionDetail.start_date} ~ {versionDetail.end_date || '진행중'}
            </p>
          )}
        </div>
      )}

      {loading && <LoadingSpinner size="lg" className="py-16" />}
      {error && <ErrorCard message={error} onRetry={refetch} />}

      {data && !loading && (
        <>
          {/* KPI 카드 (항목 2, 4) */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPICard
              type="balance"
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
              type="shift"
              title="참여·성과 변동"
              value={data.shift_kpi?.outcome ?? null}
              caption={shiftCaption(data.shift_kpi?.outcome, 'outcome')}
            />
            <KPICard
              type="shift"
              title="스탯 변동"
              value={data.shift_kpi?.stat ?? null}
              caption={shiftCaption(data.shift_kpi?.stat, 'stat')}
            />
            <KPICard
              type="shift"
              title="빌드 변동"
              value={data.shift_kpi?.build ?? null}
              caption={shiftCaption(data.shift_kpi?.build, 'build')}
            />
          </div>

          {/* 직업별 층수 분포 (항목 3: 설명 추가) */}
          <div className="card">
            <h3 className="text-sm font-bold text-[#F1F5F9] mb-1">직업별 층수 분포 (Top10)</h3>
            <p className="text-xs text-[#64748B] mb-4">
              각 직업이 평균적으로 몇 층까지 올라갔는지, 어느 층대에 유저가 많이 분포하는지 확인할 수 있어요.
              분포가 넓을수록 층수 편차가 큰 직업입니다.
            </p>
            <ViolinChart data={data.violin} />
          </div>

          {/* TER 분포 (항목 3: 설명 추가) */}
          <div className="card">
            <h3 className="text-sm font-bold text-[#F1F5F9] mb-1">TER 분포</h3>
            <p className="text-xs text-[#64748B] mb-3">
              층당 소요 시간(초) = 기록 시간 / 클리어 층수. 40~69층 기준이며, 값이 낮을수록 같은 시간에 더 많은 층을 클리어하는 고효율 직업입니다. 위쪽 막대는 50층 이상, 아래쪽 막대는 50층 미만 인원(직업별 스택)입니다.
            </p>
            <TERChart
              data={data.ter}
              terBands={data.ter_bands ?? undefined}
              terByBin={data.ter_by_bin ?? []}
              jobStyle={data.violin?.map((v) => ({ job_name: v.job_name, color: v.color, img: v.img })) ?? []}
            />
          </div>

          {/* Bump Chart (항목 3: 설명 추가) */}
          <div className="card">
            <h3 className="text-sm font-bold text-[#F1F5F9] mb-1">직업별 50층 달성률 순위 추이</h3>
            <p className="text-xs text-[#64748B] mb-4">
              패치별로 각 직업의 50층 달성률 순위가 어떻게 변했는지 추이를 보여줍니다.
              순위가 오를수록(아래로) 해당 패치에서 50층 달성이 쉬워진 직업입니다.
            </p>
            <BumpChart
              data={data.bump}
              versionChanges={data.version_changes}
              xaxisRange={data.bump_xaxis_range}
            />
          </div>

          {/* Shift Rank 테이블 (항목 3: 설명 추가) */}
          <div className="space-y-2">
            <div>
              <h3 className="text-sm font-bold text-[#F1F5F9] mb-1">직업별 Shift 랭크</h3>
              <p className="text-xs text-[#64748B] mb-3">
                이전 패치 대비 메타 변화 폭이 큰 직업을 순위로 보여줍니다. 점수 절댓값이 클수록 변화가 크며, 양수는 상향, 음수는 하향을 의미합니다.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ShiftRankTable title="50층 세그먼트" data={data.shift_rank_50.slice(0, 5)} />
              <ShiftRankTable title="상위권 세그먼트" data={data.shift_rank_upper.slice(0, 5)} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
