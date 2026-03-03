import ReactECharts from 'echarts-for-react';
import { TERJobData } from '../../types';

interface Props { data: TERJobData[]; }

function buildBins(data: TERJobData[], nBins = 20) {
  const valid = data.filter((d) => d.ter_p50 != null && d.ter_p50 > 0);
  if (!valid.length) return { labels: [], high: [], low: [] };

  const vals = valid.map((d) => d.ter_p50);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const step = (max - min) / nBins || 1;

  const labels = Array.from({ length: nBins }, (_, i) => (min + i * step + step / 2).toFixed(2));
  const high = new Array<number>(nBins).fill(0);
  const low = new Array<number>(nBins).fill(0);

  for (const item of valid) {
    const idx = Math.min(Math.floor((item.ter_p50 - min) / step), nBins - 1);
    if (item.floor50_rate >= 0.5) high[idx]++;
    else low[idx]++;
  }
  return { labels, high, low };
}

export function TERChart({ data }: Props) {
  if (!data.length) return <p className="text-[#64748B] text-sm py-4 text-center">데이터 없음</p>;

  const { labels, high, low } = buildBins(data);

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 20, bottom: 50, left: 50, right: 20 },
    legend: {
      data: ['50층 이상', '50층 미만'],
      textStyle: { color: '#94A3B8', fontSize: 11 },
      top: 'auto',
      bottom: 0,
    },
    xAxis: {
      type: 'category',
      data: labels,
      name: 'TER (분당 클리어 층수)',
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
      type: 'value',
      name: '직업 수',
      nameTextStyle: { color: '#94A3B8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#2A2D3E', type: 'dashed' as const } },
      axisLine: { show: false },
      axisLabel: { color: '#94A3B8', fontSize: 11 },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1A1D2E',
      borderColor: '#2A2D3E',
      textStyle: { color: '#F1F5F9', fontSize: 12 },
      axisPointer: { type: 'shadow' },
    },
    series: [
      {
        name: '50층 이상',
        type: 'bar',
        data: high,
        barMaxWidth: 20,
        itemStyle: { color: 'rgba(16,185,129,0.7)' },
        stack: 'total',
      },
      {
        name: '50층 미만',
        type: 'bar',
        data: low,
        barMaxWidth: 20,
        itemStyle: { color: 'rgba(239,68,68,0.7)' },
        stack: 'total',
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 320 }} notMerge />;
}
