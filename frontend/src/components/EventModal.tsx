import React from 'react';
import { X, Calendar, Clock, MapPin, User } from 'lucide-react';
import { Event } from '../services/api';

interface EventModalProps {
  event: Event;
  onClose: () => void;
}

const EventModal: React.FC<EventModalProps> = ({ event, onClose }) => {
  const formatDateTime = (datetime: string) => {
    const date = new Date(datetime);
    return {
      date: date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      }),
      time: date.toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit'
      })
    };
  };

  const { date, time } = formatDateTime(event.datetime);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="relative">
          {/* Изображение события */}
          {event.image_url && (
            <div className="h-64 bg-gray-200 rounded-t-xl overflow-hidden">
              <img
                src={event.image_url}
                alt={event.title}
                className="w-full h-full object-cover"
              />
            </div>
          )}
          
          {/* Кнопка закрытия */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 bg-white bg-opacity-90 hover:bg-opacity-100 rounded-full p-2 transition-all"
          >
            <X className="h-5 w-5 text-gray-600" />
          </button>
        </div>
        
        <div className="p-6">
          {/* Заголовок */}
          <h2 className="text-2xl font-bold text-gray-900 mb-4">{event.title}</h2>
          
          {/* Информация о событии */}
          <div className="space-y-3 mb-6">
            <div className="flex items-center space-x-3 text-gray-600">
              <Calendar className="h-5 w-5 text-primary-600" />
              <span>{date}</span>
            </div>
            
            <div className="flex items-center space-x-3 text-gray-600">
              <Clock className="h-5 w-5 text-primary-600" />
              <span>{time}</span>
            </div>
            
            <div className="flex items-center space-x-3 text-gray-600">
              <MapPin className="h-5 w-5 text-primary-600" />
              <span>{event.location}</span>
            </div>
          </div>
          
          {/* Описание */}
          {event.description && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Описание</h3>
              <p className="text-gray-600 leading-relaxed whitespace-pre-wrap">
                {event.description}
              </p>
            </div>
          )}
          
          {/* Кнопки действий */}
          <div className="flex space-x-4">
            <button
              onClick={onClose}
              className="flex-1 btn-primary"
            >
              Закрыть
            </button>
            <button
              onClick={() => {
                // Здесь можно добавить функциональность "Добавить в календарь"
                console.log('Добавить в календарь');
              }}
              className="flex-1 btn-secondary"
            >
              Добавить в календарь
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EventModal;
