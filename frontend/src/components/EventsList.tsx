import React, { useEffect, useState } from 'react';
import { eventsApi, Event } from '../services/api';
import { ChevronLeft, ChevronRight, Calendar, MapPin, Clock } from 'lucide-react';

interface EventsListProps {
  onEventClick: (event: Event) => void;
}

const EventsList: React.FC<EventsListProps> = ({ onEventClick }) => {
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [items, setItems] = useState<Event[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [showAll, setShowAll] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchPage = async (p: number) => {
    setLoading(true);
    try {
      const res = await eventsApi.getAll(p, limit);
      setItems(Array.isArray(res.data?.items) ? res.data.items : []);
      setTotalPages(Number(res.data?.total_pages) || 1);
      setTotalItems(Number(res.data?.total_items) || 0);
    } catch (error) {
      console.error('Ошибка загрузки мероприятий:', error);
      setItems([]);
      setTotalPages(1);
      setTotalItems(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPage(page); }, [page]);

  const list = Array.isArray(items) ? items : [];
  const firstThree = list.slice(0, 3);
  const itemsToShow = showAll ? list : firstThree;

  const formatDateTime = (datetime: string) => {
    const date = new Date(datetime);
    return {
      date: date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }),
      time: date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
    };
  };

  return (
    <section className="py-16 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Все мероприятия</h2>
          <p className="text-xl text-gray-600">Откройте для себя удивительные события</p>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Загрузка мероприятий...</p>
          </div>
        ) : (
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Мероприятие</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Дата и время</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Место</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Действие</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {itemsToShow.map((ev) => {
                    const { date, time } = formatDateTime(ev.datetime);
                    const hasPrice = typeof ev.price === 'number' && !Number.isNaN(ev.price);
                    const hasRating = typeof ev.rating === 'number' && !Number.isNaN(ev.rating);
                    const hasDiscount = typeof ev.discount === 'number' && !Number.isNaN(ev.discount);
                    const priceLabel = hasPrice
                      ? ev.price === 0
                        ? 'Бесплатно'
                        : `${new Intl.NumberFormat('ru-RU').format(ev.price ?? 0)} ₽`
                      : null;
                    const ratingLabel = hasRating ? ev.rating!.toFixed(1) : null;
                    const discountLabel = hasDiscount ? `−${Math.round(ev.discount ?? 0)}%` : null;
                    return (
                      <tr key={ev.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            {ev.image_url && (
                              <img src={ev.image_url} alt={ev.title} className="h-12 w-12 rounded-lg object-cover mr-4 border" />
                            )}
                            <div className="min-w-0">
                              <div className="text-sm font-medium text-gray-900">{ev.title}</div>
                              {ev.description && (
                                <div className="text-sm text-gray-500 truncate max-w-xs">{ev.description}</div>
                              )}
                              {(priceLabel || ratingLabel || discountLabel) && (
                                <div className="flex items-center gap-2 mt-2 text-xs">
                                  {priceLabel && (
                                    <span className="font-semibold text-gray-900">{priceLabel}</span>
                                  )}
                                  {ratingLabel && (
                                    <span className="px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-semibold">
                                      {ratingLabel}
                                    </span>
                                  )}
                                  {discountLabel && (
                                    <span className="px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 font-medium">
                                      {discountLabel}
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{date} • {time}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{ev.location}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                          <button className="btn-primary" onClick={() => onEventClick(ev)}>Подробнее</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {!showAll && list.length > 3 && (
              <div className="text-center pt-6">
                <button className="btn-secondary text-lg px-8 py-3" onClick={() => setShowAll(true)}>
                  Показать все ({totalItems} мероприятий)
                </button>
              </div>
            )}

            {showAll && totalPages > 1 && (
              <div className="flex justify-between items-center pt-8 border-t border-gray-200">
                <button
                  className="btn-secondary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft className="h-4 w-4" />
                  <span>Назад</span>
                </button>
                <div className="text-sm text-gray-600">
                  Страница {page} из {totalPages} • Всего {totalItems} мероприятий
                </div>
                <button
                  className="btn-secondary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  <span>Вперёд</span>
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}

            {showAll && totalPages <= 1 && (
              <div className="text-center pt-6 text-gray-500">Показаны все {totalItems} мероприятий</div>
            )}
          </div>
        )}
      </div>
    </section>
  );
};

export default EventsList;


