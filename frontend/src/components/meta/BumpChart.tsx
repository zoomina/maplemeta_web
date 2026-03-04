import ReactECharts from 'echarts-for-react';
import { useEffect, useRef, useState } from 'react';
import { BumpPoint } from '../../types';

interface Props {
  data: BumpPoint[];
  versionChanges: { date: string; version: string }[];
  xaxisRange?: [string, string] | null;
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

export function BumpChart({ data, versionChanges, xaxisRange }: Props) {
  const circularImgsRef = useRef<Record<string, string>>({});
  const [, setImgsReady] = useState(false);

  useEffect(() => {
    if (!data.length) return;
    const jobMap = new Map<string, { img: string; color: string }>();
    for (const pt of data) {
      if (!jobMap.has(pt.job_name)) jobMap.set(pt.job_name, { img: pt.img, color: pt.color });
    }
    const jobs = Array.from(jobMap.entries()).filter(([, s]) => s.img);
    if (!jobs.length) { setImgsReady(true); return; }

    Promise.all(
      jobs.map(([jobName, style]) =>
        makeCircularImageDataUrl(style.img, style.color).then((url) => ({ jobName, url }))
      )
    ).then((results) => {
      const map: Record<string, string> = {};
      for (const { jobName, url } of results) {
        if (url) map[jobName] = url;
      }
      circularImgsRef.current = map;
      setImgsReady(true);
    });
  }, [data]);

  if (!data.length) return <p className="text-[#64748B] text-sm py-4 text-center">데이터 없음</p>;

  const jobMap = new Map<string, { img: string; color: string }>();
  for (const pt of data) {
    if (!jobMap.has(pt.job_name)) jobMap.set(pt.job_name, { img: pt.img, color: pt.color });
  }

  const maxRank = Math.max(...data.map((d) => d.rank));
  const circularImgs = circularImgsRef.current;

  const series = Array.from(jobMap.entries()).map(([jobName, style]) => {
    const pts = data
      .filter((d) => d.job_name === jobName)
      .sort((a, b) => a.date.localeCompare(b.date));

    const lineColor = style.color || '#6366f1';
    const circularSrc = circularImgs[jobName];

    const seriesData = pts.map((p, idx) => {
      const isEdge = idx === 0 || idx === pts.length - 1;
      if (isEdge) {
        // 원형 이미지 준비되면 사용, 없으면 색상 circle로 fallback
        const sym = circularSrc ? `image://${circularSrc}` : 'circle';
        return {
          value: [p.date, p.rank],
          symbol: sym,
          symbolSize: circularSrc ? 36 : 14,
          itemStyle: circularSrc
            ? { borderColor: 'transparent', borderWidth: 0 }
            : { color: lineColor, borderColor: '#0F1117', borderWidth: 2 },
        };
      }
      return {
        value: [p.date, p.rank],
        symbol: 'circle',
        symbolSize: 10,
        itemStyle: {
          color: '#0F1117',
          borderColor: lineColor,
          borderWidth: 2,
        },
      };
    });

    return {
      name: jobName,
      type: 'line',
      smooth: false,
      data: seriesData,
      lineStyle: { color: lineColor, width: 2.5 },
      itemStyle: { color: lineColor },
      symbol: 'circle',
      emphasis: { scale: 1.3 },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      tooltip: {
        formatter: (params: any) => {
          const raw = Array.isArray(params.data) ? params.data : params.data?.value;
          const date = Array.isArray(raw) ? raw[0] : undefined;
          const pt = data.find((d) => d.job_name === jobName && d.date === date);
          if (!pt) return jobName;
          const imgHtml = pt.img
            ? `<img src="${pt.img}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;margin-right:6px;border:2px solid ${pt.color};" />`
            : '';
          return `<div style="display:flex;align-items:center;margin-bottom:4px">${imgHtml}<strong style="color:${pt.color}">${pt.job_name}</strong></div>
          ${pt.date}<br/>
          순위 <strong>${pt.rank}위</strong><br/>
          달성률 ${((pt.rate || 0) * 100).toFixed(1)}% (${pt.rate_delta_str})<br/>
          <span style="color:#64748B">${pt.achieved.toLocaleString()}명 / ${pt.total.toLocaleString()}명</span>`;
        },
      },
    };
  });

  const markLineData = versionChanges.map((vc) => ({
    xAxis: vc.date,
    label: { show: true, formatter: vc.version, color: '#94A3B8', fontSize: 10, position: 'insideStartTop' },
    lineStyle: { type: 'dashed' as const, color: '#383B52', width: 1 },
  }));

  const option = {
    backgroundColor: 'transparent',
    grid: { top: 20, bottom: 50, left: 55, right: 20 },
    xAxis: {
      type: 'time',
      axisLabel: { color: '#94A3B8', fontSize: 11 },
      axisLine: { lineStyle: { color: '#2A2D3E' } },
      splitLine: { show: false },
      ...(xaxisRange ? { min: xaxisRange[0], max: xaxisRange[1] } : {}),
    },
    yAxis: {
      type: 'value',
      inverse: true,
      name: '순위',
      nameTextStyle: { color: '#94A3B8', fontSize: 12 },
      min: 1,
      max: Math.min(maxRank, 15),
      interval: 1,
      splitLine: { lineStyle: { color: '#2A2D3E', type: 'dashed' as const } },
      axisLine: { show: false },
      axisLabel: { color: '#94A3B8', fontSize: 12, formatter: '{value}위' },
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1A1D2E',
      borderColor: '#2A2D3E',
      textStyle: { color: '#F1F5F9', fontSize: 13 },
    },
    series: [
      ...series,
      ...(markLineData.length > 0
        ? [{ type: 'line', data: [], markLine: { silent: true, symbol: 'none', data: markLineData } }]
        : []),
    ],
  };

  return <ReactECharts option={option} style={{ height: 420 }} notMerge />;
}
