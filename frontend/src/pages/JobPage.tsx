import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { JobItem, JobDetail, JobStats } from '../types';
import { RadarChart } from '../components/job/RadarChart';
import { HistogramCompare } from '../components/job/HistogramCompare';
import { TopTable } from '../components/job/TopTable';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ColdStartOverlay } from '../components/common/ColdStartOverlay';
import { ErrorCard } from '../components/common/ErrorCard';

const TYPE_OPTIONS = ['전체', '전사', '마법사', '궁수', '도적', '해적'];
const SEGMENTS = ['전체', '50층', '상위권'];

export function JobPage() {
  const { data: versions } = useApi<string[]>('/api/version/list');
  const [selectedVersion, setSelectedVersion] = useState('');
  const [selectedType, setSelectedType] = useState('전체');
  const [keyword, setKeyword] = useState('');
  const [view, setView] = useState<'select' | 'detail'>('select');
  const [selectedJob, setSelectedJob] = useState('');
  const [segment, setSegment] = useState('전체');
  const [activeTab, setActiveTab] = useState<'stat' | 'item'>('stat');

  useEffect(() => {
    if (versions?.length && !selectedVersion) setSelectedVersion(versions[0]);
  }, [versions, selectedVersion]);

  const jobListUrl = `/api/job/list?type=${encodeURIComponent(selectedType)}&keyword=${encodeURIComponent(keyword)}`;
  const rankingUrl = selectedVersion ? `/api/job/ranking?type=${encodeURIComponent(selectedType)}&version=${encodeURIComponent(selectedVersion)}` : null;
  const detailUrl = selectedJob ? `/api/job/${encodeURIComponent(selectedJob)}?version=${encodeURIComponent(selectedVersion)}` : null;
  const statsUrl = selectedJob
    ? `/api/job/${encodeURIComponent(selectedJob)}/stats?segment=${encodeURIComponent(segment)}&version=${encodeURIComponent(selectedVersion)}`
    : null;

  const jobList = useApi<JobItem[]>(jobListUrl, [selectedType, keyword]);
  const ranking = useApi<Record<string, unknown>[]>(rankingUrl, [selectedType, selectedVersion]);
  const detail = useApi<JobDetail>(detailUrl, [selectedJob]);
  const stats = useApi<JobStats>(statsUrl, [selectedJob, segment, selectedVersion]);

  const isColdStart = jobList.isColdStart || ranking.isColdStart;

  function openDetail(job: string) {
    setSelectedJob(job);
    setSegment('전체');
    setActiveTab('stat');
    setView('detail');
  }

  if (view === 'detail' && selectedJob) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        <ColdStartOverlay visible={detail.isColdStart || stats.isColdStart} />

        {/* 상단 바 */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setView('select')}
            className="flex items-center gap-2 text-sm text-[#94A3B8] hover:text-[#F1F5F9] transition-colors"
          >
            ← 뒤로
          </button>
          <select
            value={selectedVersion}
            onChange={(e) => setSelectedVersion(e.target.value)}
            className="bg-[#1A1D2E] border border-[#2A2D3E] text-[#F1F5F9] text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-[#FF8C00]"
          >
            {(versions ?? []).map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>

        {detail.loading && <LoadingSpinner size="lg" className="py-16" />}
        {detail.error && <ErrorCard message={detail.error} onRetry={detail.refetch} />}

        {detail.data && (
          <>
            {/* 직업 정보 행 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* 직업 이미지 */}
              <div className="card flex items-center justify-center min-h-48">
                {detail.data.img_full_resolved ? (
                  <img
                    src={detail.data.img_full_resolved}
                    alt={detail.data.job}
                    className="max-h-64 object-contain"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                ) : detail.data.img ? (
                  <img src={detail.data.img} alt={detail.data.job} className="w-32 h-32 object-contain rounded-full" />
                ) : (
                  <div className="w-24 h-24 rounded-full bg-[#2A2D3E] flex items-center justify-center text-[#64748B]">?</div>
                )}
              </div>

              {/* 직업 스탯 */}
              <div className="card space-y-3">
                <h2 className="text-2xl font-black text-[#F1F5F9]">{detail.data.job}</h2>
                <div className="flex flex-wrap gap-1">
                  {[detail.data.category, detail.data.type, detail.data.main_stat].filter(Boolean).map((t) => (
                    <span key={t} className="badge">{t}</span>
                  ))}
                </div>
                {detail.data.description && (
                  <p className="text-xs text-[#64748B] leading-relaxed">{detail.data.description}</p>
                )}
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div>
                    <div className="text-xs text-[#94A3B8]">50층 달성률</div>
                    <div className="text-xl font-bold text-[#FF8C00]">{detail.data.floor50_rate ?? '-'}</div>
                  </div>
                  <div>
                    <div className="text-xs text-[#94A3B8]">shift score</div>
                    <div className="text-xl font-bold text-[#F1F5F9]">{detail.data.shift_score ?? '-'}</div>
                  </div>
                </div>
                {detail.data.link_skill_name && (
                  <div className="flex items-center gap-2 pt-1">
                    {detail.data.link_skill_icon?.startsWith('http') && (
                      <img src={detail.data.link_skill_icon} alt="링크스킬" className="w-8 h-8" />
                    )}
                    <div>
                      <div className="text-xs text-[#94A3B8]">링크 스킬</div>
                      <div className="text-sm text-[#F1F5F9]">{detail.data.link_skill_name}</div>
                    </div>
                  </div>
                )}
              </div>

              {/* 레이다 차트 */}
              <div className="card">
                <h4 className="text-xs font-semibold text-[#94A3B8] mb-2">레이다 차트</h4>
                <RadarChart data={stats.data?.radar ?? null} />
              </div>
            </div>

            {/* 세그먼트 + 탭 */}
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex gap-1">
                {SEGMENTS.map((s) => (
                  <button
                    key={s}
                    onClick={() => setSegment(s)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                      segment === s
                        ? 'bg-[#FF8C00] text-[#0F1117]'
                        : 'bg-[#1A1D2E] text-[#94A3B8] border border-[#2A2D3E] hover:text-[#F1F5F9]'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
              <div className="flex gap-1 ml-auto">
                {(['stat', 'item'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      activeTab === tab
                        ? 'bg-[#FF8C00]/10 text-[#FF8C00] border border-[#FF8C00]/30'
                        : 'text-[#94A3B8] border border-[#2A2D3E] hover:text-[#F1F5F9]'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>
            </div>

            {stats.loading && <LoadingSpinner className="py-8" />}

            {stats.data && !stats.loading && (
              <>
                {activeTab === 'stat' && (
                  <div className="space-y-4">
                    <HistogramCompare
                      data={stats.data.main_stat_compare}
                      title="주스탯 분포 (패치 전후 비교)"
                      currentLabel={stats.data.selected_version}
                      previousLabel={stats.data.previous_version}
                    />
                    <div className="card">
                      <h4 className="text-sm font-semibold text-[#F1F5F9] mb-3">추천 코어 (헥사코어 Top5)</h4>
                      {stats.data.hexacore_top5.length > 0 ? (
                        <TopTable title="" data={stats.data.hexacore_top5} />
                      ) : (
                        <p className="text-[#64748B] text-xs">데이터 없음</p>
                      )}
                    </div>
                    <HistogramCompare
                      data={stats.data.hexacore_compare}
                      title="헥사코어 레벨 합 분포 (패치 전후 비교)"
                      currentLabel={stats.data.selected_version}
                      previousLabel={stats.data.previous_version}
                    />
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <TopTable title="하이퍼스탯 Top 5" data={stats.data.hyper_top5} />
                      <div className="space-y-4">
                        <TopTable title="어빌리티 Top 3 (Boss)" data={stats.data.ability_boss_top3} />
                        <TopTable title="어빌리티 Top 3 (Field)" data={stats.data.ability_field_top3} />
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === 'item' && (
                  <div className="space-y-4">
                    <HistogramCompare
                      data={stats.data.starforce_compare}
                      title="스타포스 분포 (패치 전후 비교)"
                      currentLabel={stats.data.selected_version}
                      previousLabel={stats.data.previous_version}
                    />
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <TopTable title="세트효과 Top 5" data={stats.data.set_effect_top5} />
                      <TopTable title="무기 Top 5" data={stats.data.weapon_top5} />
                      <TopTable title="보조무기 Top 5" data={stats.data.subweapon_top5} />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <TopTable title="추옵 Top 5" data={stats.data.extra_option_top5} />
                      <TopTable title="잠재 Top 5" data={stats.data.potential_top5} />
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    );
  }

  // Select view
  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
      <ColdStartOverlay visible={isColdStart} />

      {/* 상단 필터 */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={selectedVersion}
          onChange={(e) => setSelectedVersion(e.target.value)}
          className="bg-[#1A1D2E] border border-[#2A2D3E] text-[#F1F5F9] text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-[#FF8C00]"
        >
          {(versions ?? []).map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </div>

      <div className="grid grid-cols-5 md:grid-cols-12 gap-4">
        {/* 좌측: 직업 선택 */}
        <div className="col-span-5 space-y-3">
          <h3 className="text-sm font-bold text-[#F1F5F9]">직업 선택</h3>
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="직업명 검색..."
            className="w-full bg-[#1A1D2E] border border-[#2A2D3E] text-[#F1F5F9] text-sm rounded-lg px-3 py-2 placeholder-[#64748B] focus:outline-none focus:border-[#FF8C00]"
          />
          <div className="flex gap-1 flex-wrap">
            {TYPE_OPTIONS.map((t) => (
              <button
                key={t}
                onClick={() => setSelectedType(t)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                  selectedType === t
                    ? 'bg-[#FF8C00] text-[#0F1117]'
                    : 'bg-[#1A1D2E] text-[#94A3B8] border border-[#2A2D3E] hover:text-[#F1F5F9]'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {jobList.loading && <LoadingSpinner className="py-8" />}
          <div className="grid grid-cols-5 gap-2">
            {(jobList.data ?? []).map((job) => (
              <button
                key={job.job}
                onClick={() => openDetail(job.job)}
                className="flex flex-col items-center gap-1.5 p-2 rounded-lg border border-[#2A2D3E] hover:bg-[#1F2440] hover:border-[#FF8C00]/50 transition-colors group"
              >
                {job.img ? (
                  <img
                    src={job.img}
                    alt={job.job}
                    className="w-full aspect-square rounded-md object-cover border border-[#2A2D3E] group-hover:border-[#FF8C00] transition-colors"
                  />
                ) : (
                  <div className="w-full aspect-square rounded-md bg-[#2A2D3E] flex items-center justify-center text-xs text-[#64748B]">
                    {job.job[0]}
                  </div>
                )}
                <span className="text-xs text-[#94A3B8] group-hover:text-[#F1F5F9] text-center leading-tight line-clamp-2 w-full">
                  {job.job}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* 우측: 랭킹 테이블 */}
        <div className="col-span-5 md:col-span-7">
          <h3 className="text-sm font-bold text-[#F1F5F9] mb-3">전체 랭킹</h3>
          {ranking.loading && <LoadingSpinner className="py-8" />}
          {!ranking.loading && ranking.data && ranking.data.length > 0 && (
            <div className="card overflow-hidden p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[#2A2D3E]">
                      {Object.keys(ranking.data[0]).map((k) => (
                        <th key={k} className="px-4 py-2.5 text-left text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">
                          {k}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {ranking.data.map((row, i) => {
                      const jobName = String(row['job'] ?? row['직업'] ?? '');
                      const jobInfo = (jobList.data ?? []).find((j) => j.job === jobName);
                      return (
                        <tr
                          key={i}
                          onClick={() => jobName && openDetail(jobName)}
                          className="border-b border-[#2A2D3E]/50 hover:bg-[#1F2440] cursor-pointer transition-colors"
                        >
                          {Object.keys(ranking.data![0]).map((k) => (
                            <td key={k} className="px-4 py-2.5 text-[#94A3B8]">
                              {k === 'job' || k === '직업' ? (
                                <div className="flex items-center gap-2">
                                  {jobInfo?.img && (
                                    <img src={jobInfo.img} alt={String(row[k])} className="w-6 h-6 rounded object-cover" />
                                  )}
                                  <span className="text-[#F1F5F9]">{String(row[k] ?? '-')}</span>
                                </div>
                              ) : (
                                String(row[k] ?? '-')
                              )}
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {!ranking.loading && (!ranking.data || ranking.data.length === 0) && (
            <p className="text-sm text-[#64748B] py-6 text-center">데이터 없음</p>
          )}
        </div>
      </div>
    </div>
  );
}
