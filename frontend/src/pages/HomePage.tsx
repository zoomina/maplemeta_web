import { useApi } from '../hooks/useApi';
import { NoticeItem, EventItem } from '../types';
import { NoticeList } from '../components/home/NoticeList';
import { EventCarousel } from '../components/home/EventCarousel';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ColdStartOverlay } from '../components/common/ColdStartOverlay';

export function HomePage() {
  const notices = useApi<NoticeItem[]>('/api/home/notices');
  const updates = useApi<NoticeItem[]>('/api/home/updates');
  const events = useApi<EventItem[]>('/api/home/events');
  const cashshop = useApi<EventItem[]>('/api/home/cashshop');

  const isColdStart = notices.isColdStart || updates.isColdStart;
  const loading = notices.loading || updates.loading;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-8">
      <ColdStartOverlay visible={isColdStart} />

      {loading ? (
        <LoadingSpinner size="lg" className="py-16" />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <NoticeList title="공지사항" items={notices.data ?? []} />
            <NoticeList title="업데이트" items={updates.data ?? []} />
          </div>

          <EventCarousel title="진행중인 이벤트" items={events.data ?? []} />
          <EventCarousel title="캐시샵 공지사항" items={cashshop.data ?? []} />
        </>
      )}
    </div>
  );
}
