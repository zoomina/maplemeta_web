import ReactECharts from 'echarts-for-react';
import { BumpPoint } from '../../types';

interface Props {
  data: BumpPoint[];
  versionChanges: { date: string; version: string }[];
  xaxisRange?: [string, string] | null;
}

export function BumpChart({ data, versionChanges, xaxisRange }: Props) {
  if (!data.length) return <p className="text-[#64748B] text-sm py-4 text-center">데이터 없음</p>;

  const jobMap = new Map<string, { img: string; color: string }>();
  for (const pt of data) {
    if (!jobMap.has(pt.job_name)) jobMap.set(pt.job_name, { img: pt.img, color: pt.color });
  }

  const maxRank = Math.max(...data.map((d) => d.rank));

  const series = Array.from(jobMap.entries()).map(([jobName, style]) => {
    const pts = data
      .filter((d) => d.job_name === jobName)
      .sort((a, b) => a.date.localeCompare(b.date));

    return {
      name: jobName,
      type: 'line',
      smooth: false,
      data: pts.map((p) => [p.date, p.rank]),
      lineStyle: { color: style.color || '#6366f1', width: 2.5 },
      itemStyle: { color: style.color || '#6366f1' },
      symbol: style.img ? `image://${style.img}` : 'circle',
      symbolSize: 26,
      emphasis: { scale: 1.3 },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      tooltip: { formatter: (params: any) => {
        const pt = data.find(
          (d) => d.job_name === jobName && d.date === params.data[0]
        );
        if (!pt) return jobName;
        const imgHtml = pt.img
          ? `<img src="${pt.img}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;margin-right:6px;border:2px solid ${pt.color};" />`
          : '';
        return `<div style="display:flex;align-items:center;margin-bottom:4px">${imgHtml}<strong style="color:${pt.color}">${pt.job_name}</strong></div>
          ${pt.date}<br/>
          순위 <strong>${pt.rank}위</strong><br/>
          달성률 ${((pt.rate || 0) * 100).toFixed(1)}% (${pt.rate_delta_str})<br/>
          <span style="color:#64748B">${pt.achieved.toLocaleString()}명 / ${pt.total.toLocaleString()}명</span>`;
      }},
    };
  });

  const markLineData = versionChanges.map((vc) => ({
    xAxis: vc.date,
    label: { show: true, formatter: vc.version, color: '#94A3B8', fontSize: 10, position: 'insideStartTop' },
    lineStyle: { type: 'dashed' as const, color: '#383B52', width: 1 },
  }));

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 20, bottom: 50, left: 50, right: 20 },
    xAxis: {
      type: 'time',
      axisLabel: { color: '#94A3B8', fontSize: 10 },
      axisLine: { lineStyle: { color: '#2A2D3E' } },
      splitLine: { show: false },
      ...(xaxisRange ? { min: xaxisRange[0], max: xaxisRange[1] } : {}),
    },
    yAxis: {
      type: 'value',
      inverse: true,
      name: '순위',
      nameTextStyle: { color: '#94A3B8', fontSize: 11 },
      min: 1,
      max: Math.min(maxRank, 15),
      interval: 1,
      splitLine: { lineStyle: { color: '#2A2D3E', type: 'dashed' as const } },
      axisLine: { show: false },
      axisLabel: { color: '#94A3B8', fontSize: 11, formatter: '{value}위' },
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1A1D2E',
      borderColor: '#2A2D3E',
      textStyle: { color: '#F1F5F9', fontSize: 12 },
    },
    series: [
      ...series,
      ...(markLineData.length > 0 ? [{
        type: 'line',
        data: [],
        markLine: {
          silent: true,
          symbol: 'none',
          data: markLineData,
        },
      }] : []),
    ],
  };

  return <ReactECharts option={option} style={{ height: 400 }} notMerge />;
}
