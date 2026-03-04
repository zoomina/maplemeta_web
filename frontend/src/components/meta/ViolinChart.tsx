import ReactECharts from 'echarts-for-react';
import { ViolinJobData } from '../../types';

interface Props { data: ViolinJobData[]; }

function hexToRgba(hex: string, alpha: number): string {
  const c = (hex || '').replace('#', '');
  if (c.length !== 6) return `rgba(99,110,250,${alpha})`;
  const r = parseInt(c.slice(0, 2), 16);
  const g = parseInt(c.slice(2, 4), 16);
  const b = parseInt(c.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function makeViolinRenderItem(violinData: ViolinJobData[]) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return function (params: any, api: any) {
    const job = violinData[params.dataIndex];
    if (!job || job.density.length < 2) return null;

    const catX = params.dataIndex;
    // 모든 바이올린 동일 최대 폭 — KDE 형태가 분포를 표현 (좁은 분포 → 뾰족, 넓은 분포 → 퍼짐)
    const maxN = Math.max(...violinData.map((d) => d.n || 1));
    const nRatio = (job.n || 1) / maxN;
    const maxHalfWidth = (api.size([0.4, 0]) as [number, number])[0] * 0.5 * nRatio;
    const centerX = (api.coord([catX, 0]) as [number, number])[0];

    // 바이올린 폴리곤
    const leftPts: [number, number][] = [];
    const rightPts: [number, number][] = [];
    for (const [y, d] of job.density) {
      const [px, py] = api.coord([catX, y]) as [number, number];
      const hw = d * maxHalfWidth;
      leftPts.push([px - hw, py]);
      rightPts.push([px + hw, py]);
    }
    const allPts = [...leftPts, ...rightPts.reverse()];

    const color = job.color || '#6366f1';
    const fill = hexToRgba(color, 0.28);

    // 박스플롯 좌표
    const q1 = job.floor_q1 ?? job.floor_median;
    const q3 = job.floor_q3 ?? job.floor_median;
    const [, q1Y] = api.coord([catX, q1]) as [number, number];
    const [, q3Y] = api.coord([catX, q3]) as [number, number];
    const [, medY] = api.coord([catX, job.floor_median]) as [number, number];
    const [, minY] = api.coord([catX, job.floor_min]) as [number, number];
    const [, maxY] = api.coord([catX, job.floor_max]) as [number, number];

    const boxHW = maxHalfWidth * 0.22;
    const capHW = maxHalfWidth * 0.14;

    // q1Y > q3Y (픽셀 기준: 높은 층 = 위 = 작은 픽셀 Y)
    const boxTop = Math.min(q1Y, q3Y);
    const boxHeight = Math.abs(q1Y - q3Y);

    return {
      type: 'group',
      children: [
        // 바이올린 몸체
        {
          type: 'polygon',
          shape: { points: allPts },
          style: { fill, stroke: color, lineWidth: 1.5 },
          z2: 10,
        },
        // 하단 수염: min → Q1
        {
          type: 'line',
          shape: { x1: centerX, y1: minY, x2: centerX, y2: q1Y },
          style: { stroke: color, lineWidth: 1.2, opacity: 0.8 },
          z2: 11,
        },
        // 상단 수염: Q3 → max
        {
          type: 'line',
          shape: { x1: centerX, y1: q3Y, x2: centerX, y2: maxY },
          style: { stroke: color, lineWidth: 1.2, opacity: 0.8 },
          z2: 11,
        },
        // min 캡
        {
          type: 'line',
          shape: { x1: centerX - capHW, y1: minY, x2: centerX + capHW, y2: minY },
          style: { stroke: color, lineWidth: 1.5 },
          z2: 11,
        },
        // max 캡
        {
          type: 'line',
          shape: { x1: centerX - capHW, y1: maxY, x2: centerX + capHW, y2: maxY },
          style: { stroke: color, lineWidth: 1.5 },
          z2: 11,
        },
        // IQR 박스 (Q1~Q3)
        {
          type: 'rect',
          shape: {
            x: centerX - boxHW,
            y: boxTop,
            width: boxHW * 2,
            height: boxHeight,
          },
          style: { fill: hexToRgba(color, 0.6), stroke: color, lineWidth: 1.5 },
          z2: 12,
        },
        // 중앙값 선
        {
          type: 'line',
          shape: { x1: centerX - boxHW, y1: medY, x2: centerX + boxHW, y2: medY },
          style: { stroke: '#ffffff', lineWidth: 2.5 },
          z2: 13,
        },
      ],
    };
  };
}

export function ViolinChart({ data }: Props) {
  if (!data.length) return <p className="text-[#64748B] text-sm py-4 text-center">데이터 없음</p>;

  const jobNames = data.map((d) => d.job_name);

  const richLabels: Record<string, unknown> = {};
  data.forEach((job, idx) => {
    if (job.img) {
      richLabels[`img${idx}`] = {
        backgroundColor: { image: job.img },
        width: 36,
        height: 36,
        borderRadius: 18,
      };
    }
  });

  const allMins = data.map((d) => d.floor_min ?? 1);
  const allMaxs = data.map((d) => d.floor_max ?? 100);
  const yMin = Math.max(1, Math.floor(Math.min(...allMins)) - 2);
  const yMax = Math.min(100, Math.ceil(Math.max(...allMaxs)) + 2);

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 20, bottom: 110, left: 55, right: 20 },
    xAxis: {
      type: 'category',
      data: jobNames,
      axisLabel: {
        interval: 0,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        formatter: (name: string, idx: number) => {
          const job = data[idx];
          const jobName = (name || job?.job_name || '').trim();
          if (job?.img) {
            return `{img${idx}|}\n{name${idx}|${jobName}}`;
          }
          return jobName.length > 4 ? jobName.slice(0, 4) : jobName;
        },
        rich: {
          ...richLabels,
          ...Object.fromEntries(
            data.map((_job, idx) => [
              `name${idx}`,
              { color: '#94A3B8', fontSize: 11, align: 'center' },
            ])
          ),
        },
        color: '#94A3B8',
        fontSize: 12,
      },
      axisLine: { lineStyle: { color: '#2A2D3E' } },
      axisTick: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '층수',
      min: yMin,
      max: yMax,
      nameTextStyle: { color: '#94A3B8', fontSize: 12 },
      splitLine: { lineStyle: { color: '#2A2D3E', type: 'dashed' as const } },
      axisLine: { show: false },
      axisLabel: { color: '#94A3B8', fontSize: 12 },
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1A1D2E',
      borderColor: '#2A2D3E',
      textStyle: { color: '#F1F5F9', fontSize: 13 },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formatter: (params: any) => {
        const job = data[params.dataIndex];
        if (!job) return '';
        const imgHtml = job.img
          ? `<img src="${job.img}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;margin-right:8px;border:2px solid ${job.color || '#6366f1'};" />`
          : '';
        const q1 = job.floor_q1 != null ? job.floor_q1.toFixed(0) : '-';
        const q3 = job.floor_q3 != null ? job.floor_q3.toFixed(0) : '-';
        return `<div style="display:flex;align-items:center;gap:4px;margin-bottom:6px">
          ${imgHtml}<strong style="color:${job.color || '#6366f1'}">${job.job_name}</strong>
        </div>
        최고 ${job.floor_max}층 · 최소 ${job.floor_min}층<br/>
        Q3 ${q3}층 · Q1 ${q1}층<br/>
        평균 ${job.floor_avg?.toFixed(1)}층 · 중앙값 ${job.floor_median?.toFixed(0)}층<br/>
        <span style="color:#64748B">(${job.n?.toLocaleString()}명)</span>`;
      },
    },
    series: [
      {
        type: 'custom',
        data: data.map((_, i) => i),
        renderItem: makeViolinRenderItem(data),
        encode: { x: 0, y: 0 },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 420 }} notMerge />;
}
