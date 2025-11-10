import React from 'react';
import { Event } from '../services/api';
import { Calendar, MapPin, Clock, Share2 } from 'lucide-react';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

interface EventCardProps {
  event: Event;
  onEventClick: (event: Event) => void;
  variant?: 'default' | 'compact' | 'featured';
}

const EventCard: React.FC<EventCardProps> = ({ 
  event, 
  onEventClick, 
  variant = 'default' 
}) => {
  const formatDateTime = (datetime: string) => {
    const date = new Date(datetime);
    return {
      date: format(date, 'd MMM', { locale: ru }),
      time: format(date, 'HH:mm', { locale: ru }),
      fullDate: format(date, 'd MMMM yyyy', { locale: ru }),
      weekday: format(date, 'EEEE', { locale: ru })
    };
  };

  const { date, time, fullDate, weekday } = formatDateTime(event.datetime);
  const isToday = new Date(event.datetime).toDateString() === new Date().toDateString();
  const isTomorrow = new Date(event.datetime).toDateString() === new Date(Date.now() + 86400000).toDateString();

  const categorySlug = event.category?.slug;
  const categoryName = event.category?.name ?? 'Мероприятие';

  const hasPrice = typeof event.price === 'number' && !Number.isNaN(event.price);
  const hasRating = typeof event.rating === 'number' && !Number.isNaN(event.rating);
  const hasDiscount = typeof event.discount === 'number' && !Number.isNaN(event.discount);

  const priceLabel = hasPrice
    ? event.price === 0
      ? 'Бесплатно'
      : `${new Intl.NumberFormat('ru-RU').format(event.price ?? 0)} ₽`
    : null;
  const ratingLabel = hasRating ? event.rating?.toFixed(1) : null;
  const discountLabel = hasDiscount ? `${Math.round(event.discount ?? 0)}%` : null;

  const getCategoryColor = (slug?: string) => {
    switch (slug) {
      case 'concert': return 'bg-purple-100 text-purple-800';
      case 'theatre': return 'bg-blue-100 text-blue-800';
      case 'exhibition': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (variant === 'compact') {
    return (
      <div 
        className="flex bg-white rounded-lg border border-gray-200 hover:shadow-md transition-all duration-200 cursor-pointer group"
        onClick={() => onEventClick(event)}
      >
        <div className="w-20 h-20 flex-shrink-0">
          {event.image_url ? (
            <img 
              src={event.image_url} 
              alt={event.title}
              className="w-full h-full object-cover rounded-l-lg"
            />
          ) : (
            <div className="w-full h-full bg-gray-100 rounded-l-lg flex items-center justify-center">
              <Calendar className="h-6 w-6 text-gray-400" />
            </div>
          )}
        </div>
        <div className="flex-1 p-3 min-w-0">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h3 className="font-medium text-gray-900 truncate group-hover:text-blue-600 transition-colors">
                {event.title}
              </h3>
              <p className="text-sm text-gray-500 mt-1 truncate">{event.location}</p>
            </div>
            <div className="text-right ml-2">
              <div className="text-sm font-medium text-gray-900">{date}</div>
              <div className="text-xs text-gray-500">{time}</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (variant === 'featured') {
    return (
      <div 
        className="relative bg-white rounded-xl overflow-hidden border border-gray-200 hover:shadow-xl transition-all duration-300 cursor-pointer group"
        onClick={() => onEventClick(event)}
      >
        <div className="aspect-[16/9] relative overflow-hidden">
          {event.image_url ? (
            <img 
              src={event.image_url} 
              alt={event.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center">
              <Calendar className="h-16 w-16 text-gray-300" />
            </div>
          )}
          <div className="absolute top-3 left-3">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(categorySlug)}`}>
              {categoryName}
            </span>
          </div>
          <div className="absolute top-3 right-3 flex gap-2">
            <button
              className="p-2 bg-white/80 backdrop-blur-sm rounded-full hover:bg-white transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                // TODO: Share event
              }}
            >
              <Share2 className="h-4 w-4 text-gray-600" />
            </button>
          </div>
        </div>
        <div className="p-4">
          <h3 className="font-semibold text-lg text-gray-900 mb-2 line-clamp-2 group-hover:text-blue-600 transition-colors">
            {event.title}
          </h3>
          {event.description && (
            <p className="text-gray-600 text-sm mb-3 line-clamp-2">{event.description}</p>
          )}
          <div className="space-y-2">
            <div className="flex items-center text-sm text-gray-600">
              <Calendar className="h-4 w-4 mr-2 text-blue-500" />
              <span className="font-medium">{weekday}, {fullDate}</span>
              <span className="mx-2">•</span>
              <Clock className="h-4 w-4 mr-1" />
              <span>{time}</span>
            </div>
            <div className="flex items-center text-sm text-gray-600">
              <MapPin className="h-4 w-4 mr-2 text-red-500" />
              <span className="truncate">{event.location}</span>
            </div>
            {(ratingLabel || discountLabel || priceLabel) && (
              <div className="flex items-center justify-between pt-2">
                <div className="flex items-center gap-2">
                  {ratingLabel && (
                    <span className="text-xs font-semibold text-green-700 bg-green-100 px-2 py-1 rounded-full">
                      {ratingLabel}
                    </span>
                  )}
                  {discountLabel && (
                    <span className="text-xs font-medium text-purple-700 bg-purple-100 px-2 py-1 rounded-full">
                      −{discountLabel}
                    </span>
                  )}
                </div>
                {priceLabel && <span className="text-sm font-semibold text-gray-900">{priceLabel}</span>}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Default variant (WB style)
  return (
    <div 
      className="bg-white rounded-lg border border-gray-200 hover:shadow-lg transition-all duration-200 cursor-pointer group overflow-hidden"
      onClick={() => onEventClick(event)}
    >
      <div className="aspect-[4/3] relative overflow-hidden">
        {event.image_url ? (
          <img 
            src={event.image_url} 
            alt={event.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
            <Calendar className="h-12 w-12 text-gray-300" />
          </div>
        )}
        <div className="absolute top-2 left-2">
          <span className={`px-2 py-1 rounded text-xs font-medium ${getCategoryColor(categorySlug)}`}>
            {categoryName}
          </span>
        </div>
        {(isToday || isTomorrow) && (
          <div className="absolute top-2 right-2">
            <span className="px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800">
              {isToday ? 'Сегодня' : 'Завтра'}
            </span>
          </div>
        )}
      </div>
      
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2 group-hover:text-blue-600 transition-colors">
          {event.title}
        </h3>
        
        <div className="space-y-2 mb-3">
          <div className="flex items-center text-sm text-gray-600">
            <Calendar className="h-4 w-4 mr-2 text-blue-500 flex-shrink-0" />
            <span className="font-medium">{date}</span>
            <span className="mx-1">•</span>
            <Clock className="h-4 w-4 mr-1 flex-shrink-0" />
            <span>{time}</span>
          </div>
          <div className="flex items-center text-sm text-gray-600">
            <MapPin className="h-4 w-4 mr-2 text-red-500 flex-shrink-0" />
            <span className="truncate" title={event.location}>{event.location}</span>
          </div>
        </div>

        {event.description && (
          <p className="text-gray-600 text-sm line-clamp-2 mb-3">{event.description}</p>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {ratingLabel && (
              <span className="text-xs font-semibold text-green-700 bg-green-100 px-2 py-1 rounded-full">
                {ratingLabel}
              </span>
            )}
            {discountLabel && (
              <span className="text-xs font-medium text-purple-700 bg-purple-100 px-2 py-1 rounded-full">
                −{discountLabel}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {priceLabel && <span className="text-sm font-semibold text-gray-900">{priceLabel}</span>}
            <button
              className="p-1.5 rounded-full hover:bg-gray-100 transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                // TODO: Share event
              }}
            >
              <Share2 className="h-4 w-4 text-gray-400 hover:text-blue-500" />
            </button>
          </div>
          <span className="text-xs text-gray-500">Подробнее →</span>
        </div>
      </div>
    </div>
  );
};

export default EventCard;
