import ReactECharts from 'echarts-for-react';
import { CompareItem } from '../../types';

interface Props {
  data: CompareItem[];
  title: string;
  currentLabel: string;
  previousLabel: string;
  continuous?: boolean;
}

export function HistogramCompare({ data, title, currentLabel, previousLabel, continuous }: Props) {
  if (!data.length) return (
    <div className="card">
      <h4 className="text-sm font-semibold text-[#F1F5F9] mb-2">{title}</h4>
      <p className="text-[#64748B] text-xs">데이터 없음</p>
    </div>
  );

  const option = continuous
    ? {
        backgroundColor: 'transparent',
        grid: { top: 30, bottom: 40, left: 40, right: 10 },
        legend: {
          data: [currentLabel || '현재', previousLabel || '이전'],
          textStyle: { color: '#94A3B8', fontSize: 10 },
          top: 0,
          right: 0,
        },
        xAxis: {
          type: 'value',
          min: 'dataMin',
          max: 'dataMax',
          axisLabel: { color: '#94A3B8', fontSize: 10 },
          axisLine: { lineStyle: { color: '#2A2D3E' } },
          axisTick: { show: false },
          splitLine: { show: false },
        },
        yAxis: {
          type: 'value',
          splitLine: { lineStyle: { color: '#2A2D3E', type: 'dashed' as const } },
          axisLine: { show: false },
          axisLabel: { color: '#94A3B8', fontSize: 10 },
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: '#1A1D2E',
          borderColor: '#2A2D3E',
          textStyle: { color: '#F1F5F9', fontSize: 11 },
        },
        series: [
          {
            name: currentLabel || '현재',
            type: 'line',
            data: data.map((d) => [d.value, d.current]),
            smooth: true,
            symbol: 'none',
            lineStyle: { color: 'rgba(255,140,0,0.9)', width: 2 },
            areaStyle: { color: 'rgba(255,140,0,0.25)' },
          },
          {
            name: previousLabel || '이전',
            type: 'line',
            data: data.map((d) => [d.value, d.previous]),
            smooth: true,
            symbol: 'none',
            lineStyle: { color: 'rgba(148,163,184,0.7)', width: 2 },
            areaStyle: { color: 'rgba(148,163,184,0.15)' },
          },
        ],
      }
    : {
        backgroundColor: 'transparent',
        grid: { top: 30, bottom: 40, left: 40, right: 10 },
        legend: {
          data: [currentLabel || '현재', previousLabel || '이전'],
          textStyle: { color: '#94A3B8', fontSize: 10 },
          top: 0,
          right: 0,
        },
        xAxis: {
          type: 'category',
          data: data.map((d) => d.value),
          axisLabel: { color: '#94A3B8', fontSize: 10, interval: Math.floor(data.length / 6) },
          axisLine: { lineStyle: { color: '#2A2D3E' } },
          axisTick: { show: false },
        },
        yAxis: {
          type: 'value',
          splitLine: { lineStyle: { color: '#2A2D3E', type: 'dashed' as const } },
          axisLine: { show: false },
          axisLabel: { color: '#94A3B8', fontSize: 10 },
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: '#1A1D2E',
          borderColor: '#2A2D3E',
          textStyle: { color: '#F1F5F9', fontSize: 11 },
          axisPointer: { type: 'shadow' },
        },
        series: [
          {
            name: currentLabel || '현재',
            type: 'bar',
            data: data.map((d) => d.current),
            barMaxWidth: 20,
            itemStyle: { color: 'rgba(255,140,0,0.75)' },
          },
          {
            name: previousLabel || '이전',
            type: 'bar',
            data: data.map((d) => d.previous),
            barMaxWidth: 20,
            itemStyle: { color: 'rgba(148,163,184,0.5)' },
          },
        ],
      };

  return (
    <div className="card">
      <h4 className="text-sm font-semibold text-[#F1F5F9] mb-3">{title}</h4>
      <ReactECharts option={option} style={{ height: 200 }} notMerge />
    </div>
  );
}
