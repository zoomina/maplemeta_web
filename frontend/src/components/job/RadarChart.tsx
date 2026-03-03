import ReactECharts from 'echarts-for-react';
import { RadarData } from '../../types';

interface Props { data: RadarData | null; }

export function RadarChart({ data }: Props) {
  if (!data) return <div className="h-48 flex items-center justify-center text-[#64748B] text-sm">데이터 없음</div>;

  const option = {
    backgroundColor: 'transparent',
    legend: {
      data: ['50층', '상위권'],
      textStyle: { color: '#94A3B8', fontSize: 11 },
      bottom: 0,
    },
    radar: {
      indicator: data.labels.map((name) => ({ name, max: 100 })),
      radius: '65%',
      center: ['50%', '45%'],
      splitLine: { lineStyle: { color: '#2A2D3E' } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: '#2A2D3E' } },
      axisName: { color: '#94A3B8', fontSize: 10 },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: data.segment50,
            name: '50층',
            lineStyle: { color: '#FF8C00', width: 2 },
            itemStyle: { color: '#FF8C00' },
            areaStyle: { color: 'rgba(255,140,0,0.15)' },
          },
          {
            value: data.segmentUpper,
            name: '상위권',
            lineStyle: { color: '#6366f1', width: 2 },
            itemStyle: { color: '#6366f1' },
            areaStyle: { color: 'rgba(99,102,241,0.15)' },
          },
        ],
      },
    ],
    tooltip: {
      backgroundColor: '#1A1D2E',
      borderColor: '#2A2D3E',
      textStyle: { color: '#F1F5F9', fontSize: 11 },
    },
  };

  return <ReactECharts option={option} style={{ height: 280 }} notMerge />;
}
