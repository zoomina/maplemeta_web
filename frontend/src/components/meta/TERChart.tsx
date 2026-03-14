import ReactECharts from 'echarts-for-react';
import { useEffect, useRef, useState } from 'react';
import { TERJobData, TERBands, TERByBinItem } from '../../types';

export interface JobStyleItem {
  job_name: string;
  color: string;
  img: string;
}

interface Props {
  data: TERJobData[];
  terBands?: TERBands | null;
  terByBin?: TERByBinItem[];
  jobStyle?: JobStyleItem[];
}

function makeCircularImageDataUrl(imgUrl: string, color: string, size = 52): Promise<string> {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    if (!ctx) { resolve(''); return; }
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      try {
        const border = 3;
        const r = size / 2;
        ctx.beginPath();
        ctx.arc(r, r, r, 0, Math.PI * 2);
        ctx.fillStyle = color || '#6366f1';
        ctx.fill();
        ctx.save();
        ctx.beginPath();
        ctx.arc(r, r, r - border, 0, Math.PI * 2);
        ctx.clip();
        ctx.drawImage(img, 0, 0, size, size);
        ctx.restore();
        resolve(canvas.toDataURL());
      } catch {
        resolve('');
      }
    };
    img.onerror = () => resolve('');
    img.src = imgUrl;
  });
}

const JOB_PALETTE = [
  'rgba(16,185,129,0.85)', 'rgba(59,130,246,0.85)', 'rgba(168,85,247,0.85)',
  'rgba(236,72,153,0.85)', 'rgba(249,115,22,0.85)', 'rgba(234,179,8,0.85)',
  'rgba(34,197,94,0.85)', 'rgba(14,165,233,0.85)', 'rgba(139,92,246,0.85)',
  'rgba(244,63,94,0.85)', 'rgba(251,146,60,0.85)', 'rgba(250,204,21,0.85)',
];

function buildBins(
  data: TERJobData[],
  colorByJob?: Record<string, string>
): {
  labels: string[];
  high: number[];
  low: number[];
  jobSeriesAbove: { job_name: string; data: number[]; color: string }[];
  jobSeriesBelow: { job_name: string; data: number[]; color: string }[];
} {
  const valid = data.filter((d) => d.sec_per_floor_p50 != null && d.sec_per_floor_p50 > 0);
  const empty = {
    labels: [],
    high: [],
    low: [],
    jobSeriesAbove: [],
    jobSeriesBelow: [],
  };
  if (!valid.length) return empty;

  const vals = valid.map((d) => d.sec_per_floor_p50);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const minSec = Math.floor(min);
  const maxSec = Math.floor(max);
  const nBins = Math.max(1, maxSec - minSec + 1);
  const labels = Array.from({ length: nBins }, (_, i) => `${minSec + i}초대`);

  const high = new Array<number>(nBins).fill(0);
  const low = new Array<number>(nBins).fill(0);

  const jobsByBinAbove: Record<number, { job_name: string; value: number }[]> = {};
  const jobsByBinBelow: Record<number, { job_name: string; value: number }[]> = {};
  for (let i = 0; i < nBins; i++) {
    jobsByBinAbove[i] = [];
    jobsByBinBelow[i] = [];
  }

  for (const item of valid) {
    const sec = Math.floor(Number(item.sec_per_floor_p50));
    const idx = Math.min(Math.max(sec - minSec, 0), nBins - 1);
    high[idx] += item.n_50plus ?? 0;
    low[idx] += item.n_below50 ?? 0;
    if ((item.n_50plus ?? 0) > 0) jobsByBinAbove[idx].push({ job_name: item.job_name, value: item.n_50plus });
    if ((item.n_below50 ?? 0) > 0) jobsByBinBelow[idx].push({ job_name: item.job_name, value: item.n_below50 });
  }

  const jobNamesAbove = new Set<string>();
  const jobNamesBelow = new Set<string>();
  for (let i = 0; i < nBins; i++) {
    jobsByBinAbove[i].forEach((x) => jobNamesAbove.add(x.job_name));
    jobsByBinBelow[i].forEach((x) => jobNamesBelow.add(x.job_name));
  }
  const allJobs = Array.from(new Set([...jobNamesAbove, ...jobNamesBelow]));
  const getColor = (job_name: string, j: number) =>
    colorByJob?.[job_name] ?? JOB_PALETTE[j % JOB_PALETTE.length];
  const jobSeriesAbove = allJobs.map((job_name, j) => {
    const data = labels.map((_, binIdx) => {
      const arr = jobsByBinAbove[binIdx];
      const found = arr?.find((x) => x.job_name === job_name);
      return found ? found.value : 0;
    });
    return { job_name, data, color: getColor(job_name, j) };
  });
  const jobSeriesBelow = allJobs.map((job_name, j) => {
    const data = labels.map((_, binIdx) => {
      const arr = jobsByBinBelow[binIdx];
      const found = arr?.find((x) => x.job_name === job_name);
      return found ? -found.value : 0;
    });
    return { job_name, data, color: getColor(job_name, j) };
  });

  return { labels, high, low, jobSeriesAbove, jobSeriesBelow };
}

/** 직업별·구간별 분포(ter_by_bin)로 스택 구성. 한 직업이 여러 시간 구간에 분포 가능. */
function buildBinsFromDistribution(
  terByBin: TERByBinItem[],
  colorByJob?: Record<string, string>
): {
  labels: string[];
  high: number[];
  low: number[];
  jobSeriesAbove: { job_name: string; data: number[]; color: string }[];
  jobSeriesBelow: { job_name: string; data: number[]; color: string }[];
} {
  const empty = {
    labels: [],
    high: [],
    low: [],
    jobSeriesAbove: [],
    jobSeriesBelow: [],
  };
  if (!terByBin.length) return empty;

  const secBins = [...new Set(terByBin.map((d) => d.sec_bin))].sort((a, b) => a - b);
  const minSec = secBins[0];
  const maxSec = secBins[secBins.length - 1];
  const nBins = maxSec - minSec + 1;
  const labels = Array.from({ length: nBins }, (_, i) => `${minSec + i}초대`);

  const key = (job: string, sec: number) => `${job}\t${sec}`;
  const map = new Map<string, { n_50plus: number; n_below50: number }>();
  for (const d of terByBin) {
    const k = key(d.job_name, d.sec_bin);
    const cur = map.get(k) ?? { n_50plus: 0, n_below50: 0 };
    cur.n_50plus += d.n_50plus ?? 0;
    cur.n_below50 += d.n_below50 ?? 0;
    map.set(k, cur);
  }

  const high = new Array<number>(nBins).fill(0);
  const low = new Array<number>(nBins).fill(0);
  const allJobs = [...new Set(terByBin.map((d) => d.job_name))];
  const getColor = (job_name: string, j: number) =>
    colorByJob?.[job_name] ?? JOB_PALETTE[j % JOB_PALETTE.length];

  for (let i = 0; i < nBins; i++) {
    const sec = minSec + i;
    for (const job of allJobs) {
      const v = map.get(key(job, sec));
      if (v) {
        high[i] += v.n_50plus;
        low[i] += v.n_below50;
      }
    }
  }

  const jobSeriesAbove = allJobs.map((job_name, j) => ({
    job_name,
    data: labels.map((_, i) => map.get(key(job_name, minSec + i))?.n_50plus ?? 0),
    color: getColor(job_name, j),
  }));
  const jobSeriesBelow = allJobs.map((job_name, j) => ({
    job_name,
    data: labels.map((_, i) => -(map.get(key(job_name, minSec + i))?.n_below50 ?? 0)),
    color: getColor(job_name, j),
  }));

  return { labels, high, low, jobSeriesAbove, jobSeriesBelow };
}

function findLabelRange(labels: string[], lo: number | null, hi: number | null): { start: string; end: string } | null {
  if (lo == null || hi == null || !labels.length) return null;
  const loSec = Math.floor(lo);
  const hiSec = Math.floor(hi);
  const numLabels = labels.map((l) => parseInt(l, 10));
  const startIdx = numLabels.findIndex((s) => s >= loSec);
  let endIdx = -1;
  for (let i = labels.length - 1; i >= 0; i--) {
    if (numLabels[i] <= hiSec) { endIdx = i; break; }
  }
  if (startIdx === -1 || endIdx === -1 || startIdx > endIdx) return null;
  return { start: labels[startIdx], end: labels[endIdx] };
}

const TOOLTIP_PAGE_SIZE = 10;

interface TooltipItem {
  job_name: string;
  value: number;
  color: string;
}

interface CustomTooltipState {
  visible: boolean;
  clientX: number;
  clientY: number;
  axisValue: string;
  aboveList: TooltipItem[];
  belowList: TooltipItem[];
}

export function TERChart({ data, terBands, terByBin, jobStyle }: Props) {
  const top3Ref = useRef<{ job_name: string; img: string; color: string }[]>([]);
  const [top3Ready, setTop3Ready] = useState(false);
  const [hoveredRank, setHoveredRank] = useState<number | null>(null);
  const [tooltip, setTooltip] = useState<CustomTooltipState>({
    visible: false,
    clientX: 0,
    clientY: 0,
    axisValue: '',
    aboveList: [],
    belowList: [],
  });
  const [tooltipPageAbove, setTooltipPageAbove] = useState(0);
  const [tooltipPageBelow, setTooltipPageBelow] = useState(0);
  const chartRef = useRef<ReactECharts>(null);
  const hideTooltipTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  if (!data.length) return <p className="text-[#64748B] text-sm py-4 text-center">데이터 없음</p>;

  const styleMap = new Map<string | undefined, { img: string; color: string }>();
  const colorByJob: Record<string, string> = {};
  (jobStyle ?? []).forEach((s) => {
    styleMap.set(s.job_name, { img: s.img, color: s.color });
    if (s.color) colorByJob[s.job_name] = s.color;
  });

  const { labels, high, low, jobSeriesAbove, jobSeriesBelow } =
    terByBin?.length > 0
      ? buildBinsFromDistribution(terByBin, colorByJob)
      : buildBins(data, colorByJob);

  // 그래프 여유/근접 구간 표시와 고효율(n_in_relaxed) 계산은 동일한 terBands 사용 (백엔드 한 번에 계산)
  const relaxedRange = terBands
    ? findLabelRange(labels, terBands.relaxed_lo ?? undefined, terBands.relaxed_hi ?? undefined)
    : null;
  const nearRange = terBands
    ? findLabelRange(labels, terBands.near_lo ?? undefined, terBands.near_hi ?? undefined)
    : null;

  const maxY = Math.max(...high, 1);
  const minY = -Math.max(...low, 1);

  const top3Jobs = [...data]
    .filter((d) => (d.n_in_relaxed ?? 0) > 0)
    .sort((a, b) => (b.n_in_relaxed ?? 0) - (a.n_in_relaxed ?? 0))
    .slice(0, 3);

  const top3JobKeys = top3Jobs.map((d) => d.job_name).join(',');
  useEffect(() => {
    return () => { if (hideTooltipTimerRef.current) clearTimeout(hideTooltipTimerRef.current); };
  }, []);

  useEffect(() => {
    if (top3Jobs.length === 0) { setTop3Ready(true); return; }
    Promise.all(
      top3Jobs.map((d) => {
        const style = styleMap.get(d.job_name);
        const img = style?.img ?? '';
        const color = style?.color ?? '#6366f1';
        return makeCircularImageDataUrl(img, color, 40).then((dataUrl) => ({
          job_name: d.job_name,
          img: dataUrl || img,
          color,
        }));
      })
    ).then((results) => {
      top3Ref.current = results;
      setTop3Ready(true);
    });
  }, [top3JobKeys, jobStyle?.length ?? 0]);

  const relaxedLabel =
    relaxedRange && terBands?.relaxed_lo != null && terBands?.relaxed_hi != null
      ? `여유 구간 (${terBands.relaxed_lo.toFixed(1)}~${terBands.relaxed_hi.toFixed(1)}초/층)`
      : '여유 구간';
  const markAreaRelaxed =
    relaxedRange &&
    ({
      silent: true,
      itemStyle: { color: 'rgba(16,185,129,0.1)', borderColor: 'rgba(16,185,129,0.35)', borderWidth: 1 },
      data: [[{ xAxis: relaxedRange.start, yAxis: 0 }, { xAxis: relaxedRange.end, yAxis: maxY }]],
      label: {
        show: true,
        position: 'insideTop',
        color: 'rgba(16,185,129,0.8)',
        fontSize: 10,
        formatter: relaxedLabel,
      },
    } as const);

  const nearLabel =
    nearRange && terBands?.near_lo != null && terBands?.near_hi != null
      ? `근접구간 (${terBands.near_lo.toFixed(1)}~${terBands.near_hi.toFixed(1)}초/층)`
      : '근접구간';
  const markAreaNear =
    nearRange &&
    ({
      silent: true,
      itemStyle: { color: 'rgba(59,130,246,0.1)', borderColor: 'rgba(59,130,246,0.35)', borderWidth: 1 },
      data: [[{ xAxis: nearRange.start, yAxis: minY }, { xAxis: nearRange.end, yAxis: 0 }]],
      label: {
        show: true,
        position: 'insideBottom',
        color: 'rgba(59,130,246,0.8)',
        fontSize: 10,
        formatter: nearLabel,
      },
    } as const);

  const seriesAbove = jobSeriesAbove.map((s) => ({
    name: s.job_name,
    type: 'bar' as const,
    stack: 'above',
    data: s.data,
    barMaxWidth: 24,
    itemStyle: { color: s.color },
    ...(markAreaRelaxed && s === jobSeriesAbove[0] ? { markArea: markAreaRelaxed } : {}),
  }));

  const seriesBelow = jobSeriesBelow.map((s) => ({
    name: s.job_name,
    type: 'bar' as const,
    stack: 'below',
    data: s.data,
    barMaxWidth: 24,
    itemStyle: { color: s.color },
    ...(markAreaNear && s === jobSeriesBelow[0] ? { markArea: markAreaNear } : {}),
  }));

  const showCustomTooltip = (binIndex: number, event: { offsetX: number; offsetY: number }) => {
    if (binIndex < 0 || binIndex >= labels.length) return;
    const aboveList: TooltipItem[] = jobSeriesAbove
      .filter((s) => (s.data[binIndex] ?? 0) > 0)
      .map((s) => ({ job_name: s.job_name, value: s.data[binIndex], color: s.color }))
      .sort((a, b) => b.value - a.value);
    const belowList: TooltipItem[] = jobSeriesBelow
      .filter((s) => (s.data[binIndex] ?? 0) < 0)
      .map((s) => ({ job_name: s.job_name, value: -s.data[binIndex], color: s.color }))
      .sort((a, b) => b.value - a.value);
    const ec = chartRef.current?.getEchartsInstance();
    const dom = ec?.getDom();
    const rect = dom?.getBoundingClientRect();
    const clientX = rect ? rect.left + event.offsetX + 12 : event.offsetX;
    const clientY = rect ? rect.top + event.offsetY + 8 : event.offsetY;
    setTooltip({
      visible: aboveList.length > 0 || belowList.length > 0,
      clientX,
      clientY,
      axisValue: labels[binIndex],
      aboveList,
      belowList,
    });
    setTooltipPageAbove(0);
    setTooltipPageBelow(0);
  };

  const hideCustomTooltip = () => {
    if (hideTooltipTimerRef.current) clearTimeout(hideTooltipTimerRef.current);
    hideTooltipTimerRef.current = setTimeout(() => setTooltip((t) => ({ ...t, visible: false })), 80);
  };
  const cancelHideTooltip = () => {
    if (hideTooltipTimerRef.current) {
      clearTimeout(hideTooltipTimerRef.current);
      hideTooltipTimerRef.current = null;
    }
  };

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 56, bottom: 50, left: 55, right: 20 },
    legend: { show: false },
    xAxis: {
      type: 'category' as const,
      data: labels,
      name: '층당 소요 시간(초)',
      nameTextStyle: { color: '#94A3B8', fontSize: 11 },
      axisLabel: {
        color: '#94A3B8',
        fontSize: 10,
        interval: Math.floor(labels.length / 5),
        rotate: 30,
      },
      axisLine: { lineStyle: { color: '#2A2D3E' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value' as const,
      name: '인원 수',
      nameTextStyle: { color: '#94A3B8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#2A2D3E', type: 'dashed' as const } },
      axisLine: { show: false },
      axisLabel: { color: '#94A3B8', fontSize: 11 },
    },
    tooltip: { show: false },
    series: [...seriesAbove, ...seriesBelow],
  };

  const onChartMouseMove = (params: { event?: { offsetX: number; offsetY: number } }) => {
    const ev = params?.event;
    if (!ev) return;
    const ec = chartRef.current?.getEchartsInstance();
    if (!ec) return;
    const coord = ec.convertFromPixel({ gridIndex: 0 }, [ev.offsetX, ev.offsetY]) as [number, number] | undefined;
    if (coord == null) return;
    const raw = Math.round(coord[0]);
    const binIndex = Math.min(labels.length - 1, Math.max(0, raw));
    showCustomTooltip(binIndex, { offsetX: ev.offsetX, offsetY: ev.offsetY });
  };

  const totalPagesAbove = Math.max(1, Math.ceil(tooltip.aboveList.length / TOOLTIP_PAGE_SIZE));
  const totalPagesBelow = Math.max(1, Math.ceil(tooltip.belowList.length / TOOLTIP_PAGE_SIZE));
  const sliceAbove = tooltip.aboveList.slice(
    tooltipPageAbove * TOOLTIP_PAGE_SIZE,
    (tooltipPageAbove + 1) * TOOLTIP_PAGE_SIZE
  );
  const sliceBelow = tooltip.belowList.slice(
    tooltipPageBelow * TOOLTIP_PAGE_SIZE,
    (tooltipPageBelow + 1) * TOOLTIP_PAGE_SIZE
  );

  return (
    <div className="relative">
      {top3Ready && top3Ref.current.length > 0 && (
        <div className="absolute right-0 top-0 flex items-center gap-2 z-10">
          <span className="text-[10px] text-[#94A3B8] mr-1">고효율</span>
          {top3Ref.current.map((t, i) => {
            const job = top3Jobs[i];
            const nRelaxed = job?.n_in_relaxed ?? 0;
            const n50Plus = job?.n_50plus ?? 0;
            const nBelow50 = job?.n_below50 ?? 0;
            const ratePct = n50Plus > 0 ? ((nRelaxed / n50Plus) * 100).toFixed(1) : '0';
            const showTooltip = hoveredRank === i;
            return (
              <div
                key={t.job_name}
                className="relative flex flex-col items-center"
                onMouseEnter={() => setHoveredRank(i)}
                onMouseLeave={() => setHoveredRank(null)}
              >
                <span className="text-[10px] font-semibold text-[#94A3B8] mb-0.5">{i + 1}위</span>
                <div
                  className="w-10 h-10 rounded-full border-2 flex-shrink-0 overflow-hidden bg-[#1A1D2E] cursor-help"
                  style={{ borderColor: t.color }}
                >
                  {t.img.startsWith('data:') ? (
                    <img src={t.img} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-[#64748B] text-xs">?</div>
                  )}
                </div>
                <span className="text-[9px] text-[#94A3B8] mt-0.5 truncate max-w-[52px]">{t.job_name}</span>
                {showTooltip && (
                  <div className="absolute left-0 top-full mt-1 pt-2 px-2.5 pb-2 min-w-[180px] bg-[#1A1D2E] border border-[#2A2D3E] rounded-lg shadow-lg text-left z-20 text-[11px] text-[#F1F5F9]">
                    <div className="font-medium text-[#94A3B8] mb-1.5">{t.job_name}</div>
                    <div className="space-y-0.5">
                      <div>여유구간 수: {nRelaxed}명</div>
                      <div>50~69층 수 (50층 이상): {n50Plus}명</div>
                      <div>40~49층 수 (50층 미만): {nBelow50}명</div>
                      <div>여유구간 점유율: {ratePct}% (여유/50층 이상)</div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ height: 320 }}
        notMerge
        onEvents={{
          mousemove: onChartMouseMove,
          globalout: hideCustomTooltip,
        }}
      />
      {tooltip.visible && (
        <div
          className="fixed z-30 min-w-[200px] max-w-[280px] bg-[#1A1D2E] border border-[#2A2D3E] rounded-lg shadow-lg text-[11px] text-[#F1F5F9] overflow-hidden"
          style={{ left: tooltip.clientX, top: tooltip.clientY }}
          onMouseEnter={cancelHideTooltip}
          onMouseLeave={() => setTooltip((t) => ({ ...t, visible: false }))}
        >
          <div className="px-2.5 py-1.5 border-b border-[#2A2D3E] font-medium text-[#94A3B8]">
            {tooltip.axisValue}
          </div>
          <div className="p-2 space-y-3">
            {tooltip.aboveList.length > 0 && (
              <div>
                <div className="text-[10px] font-medium text-[#10B981] mb-1">50층 이상</div>
                <ul className="space-y-0.5">
                  {sliceAbove.map((p) => (
                    <li key={p.job_name} className="flex items-center gap-1.5">
                      <span
                        className="shrink-0 w-2 h-2 rounded-full"
                        style={{ backgroundColor: p.color }}
                      />
                      <span className="truncate">{p.job_name}</span>
                      <span className="shrink-0 text-[#94A3B8]">{p.value}명</span>
                    </li>
                  ))}
                </ul>
                {tooltip.aboveList.length > TOOLTIP_PAGE_SIZE && (
                  <div className="flex items-center justify-between mt-1 pt-1 border-t border-[#2A2D3E]">
                    <span className="text-[10px] text-[#64748B]">
                      {tooltipPageAbove * TOOLTIP_PAGE_SIZE + 1}~
                      {Math.min((tooltipPageAbove + 1) * TOOLTIP_PAGE_SIZE, tooltip.aboveList.length)} / {tooltip.aboveList.length}건
                    </span>
                    <div className="flex gap-0.5">
                      <button
                        type="button"
                        className="px-1.5 py-0.5 text-[10px] rounded bg-[#2A2D3E] text-[#94A3B8] disabled:opacity-40"
                        disabled={tooltipPageAbove <= 0}
                        onClick={() => setTooltipPageAbove((p) => Math.max(0, p - 1))}
                      >
                        이전
                      </button>
                      <button
                        type="button"
                        className="px-1.5 py-0.5 text-[10px] rounded bg-[#2A2D3E] text-[#94A3B8] disabled:opacity-40"
                        disabled={tooltipPageAbove >= totalPagesAbove - 1}
                        onClick={() => setTooltipPageAbove((p) => Math.min(totalPagesAbove - 1, p + 1))}
                      >
                        다음
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
            {tooltip.belowList.length > 0 && (
              <div>
                <div className="text-[10px] font-medium text-[#3B82F6] mb-1">50층 미만</div>
                <ul className="space-y-0.5">
                  {sliceBelow.map((p) => (
                    <li key={p.job_name} className="flex items-center gap-1.5">
                      <span
                        className="shrink-0 w-2 h-2 rounded-full"
                        style={{ backgroundColor: p.color }}
                      />
                      <span className="truncate">{p.job_name}</span>
                      <span className="shrink-0 text-[#94A3B8]">{p.value}명</span>
                    </li>
                  ))}
                </ul>
                {tooltip.belowList.length > TOOLTIP_PAGE_SIZE && (
                  <div className="flex items-center justify-between mt-1 pt-1 border-t border-[#2A2D3E]">
                    <span className="text-[10px] text-[#64748B]">
                      {tooltipPageBelow * TOOLTIP_PAGE_SIZE + 1}~
                      {Math.min((tooltipPageBelow + 1) * TOOLTIP_PAGE_SIZE, tooltip.belowList.length)} / {tooltip.belowList.length}건
                    </span>
                    <div className="flex gap-0.5">
                      <button
                        type="button"
                        className="px-1.5 py-0.5 text-[10px] rounded bg-[#2A2D3E] text-[#94A3B8] disabled:opacity-40"
                        disabled={tooltipPageBelow <= 0}
                        onClick={() => setTooltipPageBelow((p) => Math.max(0, p - 1))}
                      >
                        이전
                      </button>
                      <button
                        type="button"
                        className="px-1.5 py-0.5 text-[10px] rounded bg-[#2A2D3E] text-[#94A3B8] disabled:opacity-40"
                        disabled={tooltipPageBelow >= totalPagesBelow - 1}
                        onClick={() => setTooltipPageBelow((p) => Math.min(totalPagesBelow - 1, p + 1))}
                      >
                        다음
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
