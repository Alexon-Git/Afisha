import React, { useEffect, useMemo, useState } from 'react';
import { eventsApi, Event } from '../services/api';
import { Calendar, MapPin, Filter, ChevronDown } from 'lucide-react';

interface FeedFilters {
  date?: string; // today | tomorrow | weekend | YYYY-MM-DD
  category?: string;
  sort?: 'asc' | 'desc';
}

const datePresets = [
  { key: 'today', label: 'Сегодня' },
  { key: 'tomorrow', label: 'Завтра' },
  { key: 'weekend', label: 'Выходные' },
];

const categories = [
  { key: '', label: 'Все категории' },
  { key: 'concert', label: 'Концерты' },
  { key: 'theatre', label: 'Театр' },
  { key: 'exhibition', label: 'Выставки' },
];

const PAGE_SIZE = 12;

const formatDateTime = (datetime: string) => {
  const date = new Date(datetime);
  return date.toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'
  });
};

const EventsFeed: React.FC<{ onEventClick?: (event: Event) => void }> = ({ onEventClick }) => {
  const [filters, setFilters] = useState<FeedFilters>({ sort: 'asc' });
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<Event[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);

  const loadPage = async (p: number, replace = false) => {
    setLoading(true);
    try {
      const res = await eventsApi.getAll(p, PAGE_SIZE, filters);
      const paginated = res.data as any;
      const newItems: Event[] = Array.isArray(paginated.items) ? paginated.items : [];
      setTotalPages(Number(paginated.total_pages) || 1);
      setItems(replace ? newItems : [...items, ...newItems]);
    } finally {
      setLoading(false);
    }
  };

  // reload on filters change
  useEffect(() => {
    setPage(1);
    loadPage(1, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.date, filters.category, filters.sort]);

  const onLoadMore = () => {
    if (page < totalPages) {
      const next = page + 1;
      setPage(next);
      loadPage(next);
    }
  };

  return (
    <section className="py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Filters */}
        <div className="mb-6 bg-white/80 backdrop-blur rounded-xl p-4 border border-gray-200">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              {datePresets.map(preset => (
                <button
                  key={preset.key}
                  onClick={() => setFilters(prev => ({ ...prev, date: preset.key }))}
                  className={`px-3 py-2 rounded-lg text-sm border ${filters.date === preset.key ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300'}`}
                >
                  {preset.label}
                </button>
              ))}
              <input
                type="date"
                onChange={(e) => setFilters(prev => ({ ...prev, date: e.target.value || undefined }))}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700"
              />
            </div>
            <div className="flex items-center gap-2 ml-auto">
              <select
                value={filters.category || ''}
                onChange={(e) => setFilters(prev => ({ ...prev, category: e.target.value || undefined }))}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700"
              >
                {categories.map(c => (
                  <option key={c.key} value={c.key}>{c.label}</option>
                ))}
              </select>
              <select
                value={filters.sort || 'asc'}
                onChange={(e) => setFilters(prev => ({ ...prev, sort: (e.target.value as 'asc'|'desc') }))}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700"
              >
                <option value="asc">Сначала ближайшие</option>
                <option value="desc">Сначала дальние</option>
              </select>
            </div>
          </div>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {items.map(ev => (
            <div
              key={ev.id}
              className="group rounded-xl overflow-hidden border border-gray-200 bg-white hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => onEventClick?.(ev)}
            >
              <div className="aspect-[4/3] bg-gray-100 overflow-hidden">
                {ev.image_url ? (
                  <img src={ev.image_url} alt={ev.title} className="w-full h-full object-cover object-center group-hover:scale-[1.02] transition-transform" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-400">Нет изображения</div>
                )}
              </div>
              <div className="p-4">
                <div className="text-sm text-gray-500 mb-1">{ev.category || 'Другие'}</div>
                <div className="font-semibold text-gray-900 mb-2 line-clamp-2">{ev.title}</div>
                <div className="text-sm text-gray-700 flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-primary-600" />
                  <span>{formatDateTime(ev.datetime)}</span>
                </div>
                <div className="text-sm text-gray-700 flex items-center gap-2 mt-1">
                  <MapPin className="h-4 w-4 text-primary-600" />
                  <span className="truncate" title={ev.location}>{ev.location}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Load More */}
        {page < totalPages && (
          <div className="text-center mt-8">
            <button disabled={loading} onClick={onLoadMore} className="btn-secondary px-6 py-3 text-base disabled:opacity-60">
              {loading ? 'Загрузка...' : 'Показать ещё'}
            </button>
          </div>
        )}
      </div>
    </section>
  );
};

export default EventsFeed;


