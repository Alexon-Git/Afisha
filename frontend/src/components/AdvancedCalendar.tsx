import React, { useMemo, useState } from 'react';
import { Calendar as RBCalendar, dateFnsLocalizer, Views } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { ru } from 'date-fns/locale';
import type { Locale as DateFnsLocale } from 'date-fns';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { Event as ApiEvent } from '../services/api';

type CalendarEvent = {
  id: number;
  title: string;
  start: Date;
  end: Date;
  location?: string;
  original: ApiEvent;
};

const locales: Record<string, DateFnsLocale> = {
  ru,
};

const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek: () => startOfWeek(new Date(), { weekStartsOn: 1 }),
  getDay,
  locales,
});

interface AdvancedCalendarProps {
  events: ApiEvent[];
  onEventClick: (event: ApiEvent) => void;
}

const AdvancedCalendar: React.FC<AdvancedCalendarProps> = ({ events, onEventClick }) => {
  const [currentDate, setCurrentDate] = useState<Date>(new Date());

  const mappedEvents: CalendarEvent[] = useMemo(() => {
    return events.map((e) => {
      const start = new Date(e.datetime);
      const end = new Date(start.getTime() + 60 * 60 * 1000); // 1 час по умолчанию
      return {
        id: e.id,
        title: e.title,
        start,
        end,
        location: e.location,
        original: e,
      };
    });
  }, [events]);

  const components = useMemo(() => ({
    event: ({ event }: any) => (
      <div title={`${event.title} — ${format(event.start, 'HH:mm')} • ${event.location || ''}`}>
        <div className="truncate text-[13px] font-medium">{event.title}</div>
        <div className="text-[11px] text-gray-600">{format(event.start, 'HH:mm')}</div>
      </div>
    ),
    toolbar: (props: any) => {
      const goToBack = () => props.onNavigate('PREV');
      const goToNext = () => props.onNavigate('NEXT');
      const goToToday = () => props.onNavigate('TODAY');
      return (
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <button onClick={goToBack} className="btn-secondary px-3 py-1">←</button>
            <button onClick={goToToday} className="btn-secondary px-3 py-1">Сегодня</button>
            <button onClick={goToNext} className="btn-secondary px-3 py-1">→</button>
          </div>
          <div className="text-lg font-semibold">{format(props.date, 'LLLL yyyy', { locale: ru })}</div>
          <div className="w-20" />
        </div>
      );
    },
  }), []);

  return (
    <div className="card p-4">
      <RBCalendar
        views={[Views.MONTH]}
        view={Views.MONTH}
        date={currentDate}
        onNavigate={(date: Date) => setCurrentDate(date)}
        localizer={localizer}
        events={mappedEvents}
        startAccessor="start"
        endAccessor="end"
        popup
        culture="ru"
        onSelectEvent={(e: CalendarEvent) => onEventClick(e.original)}
        components={components}
        messages={{
          next: 'Следующий',
          previous: 'Предыдущий',
          today: 'Сегодня',
          month: 'Месяц',
        }}
        formats={{
          weekdayFormat: (date: Date) => format(date, 'EE', { locale: ru }),
          dayFormat: (date: Date) => format(date, 'd'),
        }}
        className="rbc-tailwind"
      />

      <style>{`
        .rbc-tailwind .rbc-month-view { border-color: rgb(229 231 235); }
        .rbc-tailwind .rbc-month-row { border-color: rgb(229 231 235); }
        .rbc-tailwind .rbc-header { padding: 8px 0; font-weight: 600; color: rgb(55 65 81); border-color: rgb(229 231 235); }
        .rbc-tailwind .rbc-date-cell { padding: 4px 8px; color: rgb(75 85 99); }
        .rbc-tailwind .rbc-off-range-bg { background: rgb(249 250 251); }
        .rbc-tailwind .rbc-event { background: rgb(219 234 254); border: 1px solid rgb(191 219 254); color: rgb(30 64 175); padding: 2px 6px; border-radius: 6px; }
        .rbc-tailwind .rbc-event.rbc-selected { background: rgb(147 197 253); }
        .rbc-tailwind .rbc-today { background: rgb(239 246 255); }
      `}</style>
    </div>
  );
};

export default AdvancedCalendar;


