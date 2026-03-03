import ReactECharts from 'echarts-for-react';
import { ViolinJobData } from '../../types';

interface Props { data: ViolinJobData[]; }

function hexToRgba(hex: string, alpha: number): string {
  const c = hex.replace('#', '');
  if (c.length !== 6) return `rgba(99,110,250,${alpha})`;
  const r = parseInt(c.slice(0, 2), 16);
  const g = parseInt(c.slice(2, 4), 16);
  const b = parseInt(c.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function makeViolinRenderItem(violinData: ViolinJobData[]) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return function (params: any, api: any) {
    const job = violinData[params.dataIndex];
    if (!job || job.density.length < 4) return null;

    const catX = params.dataIndex;
    const maxHalfWidth = api.size([0.4, 0])[0] * 0.5;

    const leftPts: [number, number][] = [];
    const rightPts: [number, number][] = [];

    for (const [y, d] of job.density) {
      const coord = api.coord([catX, y]);
      const hw = d * maxHalfWidth;
      leftPts.push([coord[0] - hw, coord[1]]);
      rightPts.push([coord[0] + hw, coord[1]]);
    }

    const allPts = [...leftPts, ...rightPts.reverse()];
    const color = job.color || '#6366f1';
    const fill = hexToRgba(color, 0.35);
    const medianCoord = api.coord([catX, job.floor_median]);

    return {
      type: 'group',
      children: [
        {
          type: 'polygon',
          shape: { points: allPts },
          style: { fill, stroke: color, lineWidth: 1.5 },
          z2: 10,
        },
        {
          type: 'line',
          shape: {
            x1: medianCoord[0] - maxHalfWidth * 0.6,
            y1: medianCoord[1],
            x2: medianCoord[0] + maxHalfWidth * 0.6,
            y2: medianCoord[1],
          },
          style: { stroke: '#ffffff', lineWidth: 2, opacity: 0.9 },
          z2: 11,
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
        width: 32,
        height: 32,
        borderRadius: 16,
      };
    }
  });

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 20, bottom: 72, left: 50, right: 20 },
    xAxis: {
      type: 'category',
      data: jobNames,
      axisLabel: {
        interval: 0,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        formatter: (_name: string, idx: number) => {
          const job = data[idx];
          return job?.img ? `{img${idx}|}` : (_name.length > 4 ? _name.slice(0, 4) : _name);
        },
        rich: richLabels,
        color: '#94A3B8',
        fontSize: 11,
      },
      axisLine: { lineStyle: { color: '#2A2D3E' } },
      axisTick: { show: false },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '층수',
      nameTextStyle: { color: '#94A3B8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#2A2D3E', type: 'dashed' as const } },
      axisLine: { show: false },
      axisLabel: { color: '#94A3B8', fontSize: 11 },
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1A1D2E',
      borderColor: '#2A2D3E',
      textStyle: { color: '#F1F5F9', fontSize: 12 },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formatter: (params: any) => {
        const job = data[params.dataIndex];
        if (!job) return '';
        const imgHtml = job.img
          ? `<img src="${job.img}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;margin-right:8px;border:2px solid ${job.color || '#6366f1'};" />`
          : '';
        return `<div style="display:flex;align-items:center;gap:4px;margin-bottom:6px">
          ${imgHtml}<strong style="color:${job.color || '#6366f1'}">${job.job_name}</strong>
        </div>
        최고 ${job.floor_max}층 · 최소 ${job.floor_min}층<br/>
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

  return <ReactECharts option={option} style={{ height: 380 }} notMerge />;
}
