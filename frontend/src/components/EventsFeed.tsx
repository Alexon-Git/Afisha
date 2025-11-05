import React, { useEffect, useState } from 'react';
import { eventsApi, Event } from '../services/api';
import EventCard from './EventCard';
import EventFilters, { FilterState } from './EventFilters';
import { Loader2, Calendar } from 'lucide-react';

const PAGE_SIZE = 12;

const EventsFeed: React.FC<{ onEventClick?: (event: Event) => void; dateFrom?: string; dateTo?: string }> = ({ onEventClick, dateFrom, dateTo }) => {
  const [filters, setFilters] = useState<FilterState>({ sort: 'asc' });
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<Event[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);

  const loadPage = async (p: number, replace = false) => {
    setLoading(true);
    try {
      const { location, ...apiFilters } = filters;
      const response = await eventsApi.getAll(p, PAGE_SIZE, apiFilters);
      const paginated = response.data;
      const newItems = Array.isArray(paginated.items) ? paginated.items : [];
      const nextTotalPages = paginated.total_pages || (newItems.length > 0 ? 1 : 0);

      setTotalPages(nextTotalPages || 1);
      setItems(prev => (replace ? newItems : [...prev, ...newItems]));
      setHasMore(p < nextTotalPages);
    } catch (error) {
      console.error('Ошибка загрузки мероприятий:', error);
    } finally {
      setLoading(false);
    }
  };

  // inject external date range from props
  useEffect(() => {
    setFilters(prev => ({ ...prev, date_from: dateFrom || undefined, date_to: dateTo || undefined, date: undefined }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateFrom, dateTo]);

  // reload on filters change
  useEffect(() => {
    setPage(1);
    setItems([]);
    loadPage(1, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.date, filters.date_from, filters.date_to, filters.category, filters.sort, filters.location]);

  const onLoadMore = () => {
    if (hasMore && !loading) {
      const next = page + 1;
      setPage(next);
      loadPage(next);
    }
  };

  const handleFiltersChange = (newFilters: FilterState) => {
    setFilters(newFilters);
  };

  const handleClearFilters = () => {
    setFilters({ sort: 'asc' });
  };

  return (
    <section className="py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Filters */}
        <EventFilters
          filters={filters}
          onFiltersChange={handleFiltersChange}
          onClearFilters={handleClearFilters}
        />

        {/* Results Count */}
        {items.length > 0 && (
          <div className="mb-6 text-sm text-gray-600">
            Найдено мероприятий: <span className="font-medium">{items.length}</span>
            {totalPages > 1 && (
              <span className="ml-2">
                (страница {page} из {totalPages})
              </span>
            )}
          </div>
        )}

        {/* Loading State */}
        {loading && items.length === 0 && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            <span className="ml-2 text-gray-600">Загрузка мероприятий...</span>
          </div>
        )}

        {/* Empty State */}
        {!loading && items.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <Calendar className="h-16 w-16 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Мероприятия не найдены</h3>
            <p className="text-gray-600 mb-4">
              Попробуйте изменить фильтры или выбрать другой период
            </p>
            <button
              onClick={handleClearFilters}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Сбросить фильтры
            </button>
          </div>
        )}

        {/* Events Grid */}
        {items.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {items.map(event => (
              <EventCard
                key={event.id}
                event={event}
                onEventClick={onEventClick || (() => {})}
                variant="default"
              />
            ))}
          </div>
        )}

        {/* Load More Button */}
        {hasMore && items.length > 0 && (
          <div className="text-center mt-8">
            <button
              disabled={loading}
              onClick={onLoadMore}
              className="px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 mx-auto"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Загрузка...
                </>
              ) : (
                'Показать ещё'
              )}
            </button>
          </div>
        )}
      </div>
    </section>
  );
};

export default EventsFeed;


