import React, { useMemo, useState } from 'react';
import { Event } from '../services/api';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface CalendarGridProps {
  events: Event[];
  onEventClick: (event: Event) => void;
}

const startOfMonth = (d: Date) => new Date(d.getFullYear(), d.getMonth(), 1);
const endOfMonth = (d: Date) => new Date(d.getFullYear(), d.getMonth() + 1, 0);
const startOfWeek = (d: Date) => {
  const date = new Date(d);
  const day = (date.getDay() + 6) % 7; // Monday first
  date.setDate(date.getDate() - day);
  date.setHours(0, 0, 0, 0);
  return date;
};
const addDays = (d: Date, days: number) => {
  const date = new Date(d);
  date.setDate(date.getDate() + days);
  return date;
};

const dayKey = (d: Date) => d.toISOString().slice(0, 10);

const CalendarGrid: React.FC<CalendarGridProps> = ({ events, onEventClick }) => {
  const [current, setCurrent] = useState<Date>(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  const monthStart = startOfMonth(current);
  const monthEnd = endOfMonth(current);
  const gridStart = startOfWeek(monthStart);
  const daysCount = Math.ceil(((monthEnd.getTime() - gridStart.getTime()) / 86400000 + 1) / 7) * 7;

  const days = useMemo(() => Array.from({ length: daysCount }, (_, i) => addDays(gridStart, i)), [gridStart, daysCount]);

  const eventsByDay = useMemo(() => {
    const map: Record<string, Event[]> = {};
    for (const e of events) {
      const k = dayKey(new Date(e.datetime));
      (map[k] ||= []).push(e);
    }
    return map;
  }, [events]);

  const isSameMonth = (a: Date, b: Date) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth();
  const isToday = (d: Date) => dayKey(d) === dayKey(new Date());

  const monthName = current.toLocaleString('ru-RU', { month: 'long', year: 'numeric' });

  return (
    <section id="events" className="py-16 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-6 flex-col sm:flex-row gap-4">
          <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 w-full sm:w-auto text-center sm:text-left">Календарь мероприятий</h2>
          <div className="flex items-center space-x-2 sm:space-x-4 w-full sm:w-auto justify-center sm:justify-end">
            <button 
              className="btn-secondary flex items-center space-x-2 px-3 py-2 text-sm" 
              onClick={() => setCurrent(new Date(current.getFullYear(), current.getMonth() - 1, 1))}
            >
              <ChevronLeft className="h-4 w-4" />
              <span>Предыдущий</span>
            </button>
            <button 
              className="btn-secondary px-3 py-2 text-sm" 
              onClick={() => setCurrent(new Date())}
            >
              Сегодня
            </button>
            <button 
              className="btn-secondary flex items-center space-x-2 px-3 py-2 text-sm" 
              onClick={() => setCurrent(new Date(current.getFullYear(), current.getMonth() + 1, 1))}
            >
              <span>Следующий</span>
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="text-center mb-6">
          <h3 className="text-xl sm:text-2xl font-semibold text-gray-800 capitalize">{monthName}</h3>
        </div>

        {/* Сетка 7 колонок: на десктопе показываем детали, на мобильных — точки */}
        <div className="grid grid-cols-7 gap-px bg-gray-200 rounded-lg overflow-hidden shadow-lg text-[11px] sm:text-sm">
          {["Пн","Вт","Ср","Чт","Пт","Сб","Вс"].map((d) => (
            <div key={d} className="bg-gray-100 py-3 text-center text-sm font-semibold text-gray-700 border-b border-gray-200">
              {d}
            </div>
          ))}
          {days.map((d) => {
            const key = dayKey(d);
            const list = eventsByDay[key] || [];
            return (
              <button
                key={key}
                className={
                  `bg-white min-h-[64px] xs:min-h-[88px] sm:min-h-[120px] md:min-h-[160px] p-1 sm:p-2 relative border-r border-b border-gray-100 hover:bg-gray-50 transition-colors text-left ` +
                  (isSameMonth(d, monthStart) ? '' : 'opacity-50 bg-gray-50 ') +
                  (isToday(d) ? 'ring-2 ring-primary-500 bg-primary-50' : '') +
                  (selectedDate && dayKey(d) === dayKey(selectedDate) ? ' outline outline-2 outline-primary-400' : '')
                }
                onClick={() => setSelectedDate(d)}
              >
                <div className={`text-[11px] sm:text-sm font-medium mb-1 sm:mb-2 ${isToday(d) ? 'text-primary-700' : 'text-gray-700'}`}>
                  {d.getDate()}
                </div>
                {/* Desktop: подробный список (первые 3) */}
                <div className="hidden sm:block">
                  <div className="space-y-1 max-h-[calc(100%-32px)] overflow-hidden">
                    {list.slice(0, 3).map(ev => (
                      <button
                        key={ev.id}
                        onClick={(e) => { e.stopPropagation(); onEventClick(ev); }}
                        title={`${ev.title} • ${new Date(ev.datetime).toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'})} • ${ev.location}`}
                        className="w-full flex items-center space-x-2 text-left group hover:bg-primary-50 p-1 rounded transition-colors"
                      >
                        {ev.image_url && (
                          <img src={ev.image_url} alt={ev.title} className="w-6 h-6 rounded object-cover border border-gray-200 flex-shrink-0" />
                        )}
                        <span className="text-[12px] text-gray-800 truncate group-hover:text-primary-700 group-hover:underline">{ev.title}</span>
                      </button>
                    ))}
                    {list.length > 3 && (
                      <div className="text-[11px] text-primary-600 font-medium bg-primary-100 px-2 py-1 rounded">
                        +{list.length - 3} ещё
                      </div>
                    )}
                  </div>
                </div>
                {/* Mobile: точки-индикаторы */}
                <div className="flex sm:hidden items-center gap-0.5 mt-1">
                  {Array.from({ length: Math.min(list.length, 5) }).map((_, i) => (
                    <span key={i} className="inline-block w-1.5 h-1.5 rounded-full bg-primary-500"></span>
                  ))}
                </div>
              </button>
            );
          })}
        </div>

        {/* Список под календарём — только для мобильных */}
        <div className="mt-6 space-y-3 sm:hidden">
          <div className="flex items-center justify-between">
            <h4 className="text-lg font-semibold text-gray-900">
              {selectedDate ? `Мероприятия на ${selectedDate.toLocaleDateString('ru-RU')}` : 'Все мероприятия месяца'}
            </h4>
            {selectedDate && (
              <button className="btn-secondary px-3 py-1 text-sm" onClick={() => setSelectedDate(null)}>Показать все</button>
            )}
          </div>
          <div className="grid gap-3">
            {(() => {
              const filterFn = (e: Event) => {
                const d = new Date(e.datetime);
                if (!isSameMonth(d, monthStart)) return false;
                if (!selectedDate) return true;
                return dayKey(d) === dayKey(selectedDate);
              };
              const visible = events.filter(filterFn).sort((a, b) => +new Date(a.datetime) - +new Date(b.datetime));
              if (visible.length === 0) {
                return <div className="text-sm text-gray-500">На выбранный период нет мероприятий</div>;
              }
              return visible.map(ev => (
                <button
                  key={ev.id}
                  onClick={() => onEventClick(ev)}
                  className="card p-3 flex items-center text-left hover:shadow-md transition-shadow"
                  title={`${ev.title} • ${new Date(ev.datetime).toLocaleString('ru-RU')} • ${ev.location}`}
                >
                  {ev.image_url && <img src={ev.image_url} alt={ev.title} className="w-12 h-12 rounded object-cover border mr-3" />}
                  <div className="min-w-0">
                    <div className="font-medium text-gray-900 truncate">{ev.title}</div>
                    <div className="text-xs text-gray-600 truncate">{new Date(ev.datetime).toLocaleString('ru-RU')} • {ev.location}</div>
                  </div>
                </button>
              ));
            })()}
          </div>
        </div>
      </div>
    </section>
  );
};

export default CalendarGrid;


