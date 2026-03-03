import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useApi } from '../hooks/useApi';
import { VersionDetail } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

export function PatchNotePage() {
  const { data: versions } = useApi<string[]>('/api/version/list');
  const [selectedVersion, setSelectedVersion] = useState('');

  useEffect(() => {
    if (versions?.length && !selectedVersion) setSelectedVersion(versions[0]);
  }, [versions, selectedVersion]);

  const { data: detail } = useApi<VersionDetail>(
    selectedVersion ? `/api/version/${encodeURIComponent(selectedVersion)}` : null,
    [selectedVersion]
  );
  const { data: patchNote, loading } = useApi<{ content: string }>(
    selectedVersion ? `/api/version/${encodeURIComponent(selectedVersion)}/patch-note` : null,
    [selectedVersion]
  );

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-black text-[#F1F5F9]">패치노트</h1>
        <select
          value={selectedVersion}
          onChange={(e) => setSelectedVersion(e.target.value)}
          className="bg-[#1A1D2E] border border-[#2A2D3E] text-[#F1F5F9] text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-[#FF8C00]"
        >
          {(versions ?? []).map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </div>

      {detail && (
        <div className="card space-y-3">
          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-lg font-bold text-[#FF8C00]">{detail.version}</span>
            {detail.type_list.map((t) => (
              <span key={t} className="badge badge-accent">{t}</span>
            ))}
          </div>
          {detail.impacted_job_list.length > 0 && (
            <div>
              <span className="text-xs text-[#94A3B8] font-semibold mr-2">업데이트 직업</span>
              {detail.impacted_job_list.map((j) => (
                <span key={j} className="badge">{j}</span>
              ))}
            </div>
          )}
          {(detail.start_date || detail.end_date) && (
            <p className="text-xs text-[#64748B]">
              {detail.start_date} ~ {detail.end_date || '진행중'}
            </p>
          )}
        </div>
      )}

      {loading && <LoadingSpinner size="lg" className="py-16" />}

      {patchNote && !loading && (
        <div className="card">
          {patchNote.content ? (
            <div className="prose-dark">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{patchNote.content}</ReactMarkdown>
            </div>
          ) : (
            <p className="text-[#64748B] text-sm py-8 text-center">패치노트 파일을 찾을 수 없습니다.</p>
          )}
        </div>
      )}
    </div>
  );
}
