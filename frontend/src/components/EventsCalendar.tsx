import React, { useState } from 'react';
import Calendar from 'react-calendar';
import { Event } from '../services/api';
import { Calendar as CalendarIcon, Clock, MapPin } from 'lucide-react';
import 'react-calendar/dist/Calendar.css';

interface EventsCalendarProps {
  events: Event[];
  onEventClick: (event: Event) => void;
  loading: boolean;
}

const EventsCalendar: React.FC<EventsCalendarProps> = ({ events, onEventClick, loading }) => {
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());

  // Группируем события по датам
  const eventsByDate = events.reduce((acc, event) => {
    const date = new Date(event.datetime).toDateString();
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(event);
    return acc;
  }, {} as Record<string, Event[]>);

  // Функция для определения, есть ли события в определенный день
  const hasEvents = (date: Date) => {
    const dateString = date.toDateString();
    return eventsByDate[dateString] && eventsByDate[dateString].length > 0;
  };

  // Функция для получения количества событий в день
  const getEventCount = (date: Date) => {
    const dateString = date.toDateString();
    return eventsByDate[dateString]?.length || 0;
  };

  // Получаем события для выбранной даты
  const selectedDateEvents = eventsByDate[selectedDate.toDateString()] || [];

  const formatEventTime = (datetime: string) => {
    return new Date(datetime).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatEventDate = (datetime: string) => {
    return new Date(datetime).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  if (loading) {
    return (
      <section id="events" className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Загрузка мероприятий...</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section id="events" className="py-20 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Календарь мероприятий
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Выберите дату и откройте для себя удивительные события
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Календарь */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center space-x-2 mb-6">
              <CalendarIcon className="h-6 w-6 text-primary-600" />
              <h3 className="text-xl font-semibold text-gray-900">Выберите дату</h3>
            </div>
            
            <Calendar
              onChange={setSelectedDate}
              value={selectedDate}
              locale="ru-RU"
              className="w-full"
              tileContent={({ date }) => {
                const count = getEventCount(date);
                if (count > 0) {
                  return (
                    <div className="absolute top-1 right-1">
                      <div className="bg-primary-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                        {count}
                      </div>
                    </div>
                  );
                }
                return null;
              }}
              tileClassName={({ date }) => {
                return hasEvents(date) 
                  ? 'bg-primary-50 border-primary-200' 
                  : '';
              }}
            />
          </div>

          {/* События на выбранную дату */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h3 className="text-xl font-semibold text-gray-900 mb-6">
              Мероприятия на {selectedDate.toLocaleDateString('ru-RU', {
                day: 'numeric',
                month: 'long',
                year: 'numeric'
              })}
            </h3>
            
            {selectedDateEvents.length === 0 ? (
              <div className="text-center py-8">
                <CalendarIcon className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">На эту дату мероприятий не запланировано</p>
              </div>
            ) : (
              <div className="space-y-4">
                {selectedDateEvents.map((event) => (
                  <div
                    key={event.id}
                    onClick={() => onEventClick(event)}
                    className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                  >
                    <div className="flex items-start space-x-4">
                      {event.image_url && (
                        <img
                          src={event.image_url}
                          alt={event.title}
                          className="w-16 h-16 object-cover rounded-lg"
                        />
                      )}
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900 mb-2">{event.title}</h4>
                        <div className="flex items-center space-x-4 text-sm text-gray-600">
                          <div className="flex items-center space-x-1">
                            <Clock className="h-4 w-4" />
                            <span>{formatEventTime(event.datetime)}</span>
                          </div>
                          <div className="flex items-center space-x-1">
                            <MapPin className="h-4 w-4" />
                            <span>{event.location}</span>
                          </div>
                        </div>
                        {event.description && (
                          <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                            {event.description}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};

export default EventsCalendar;
