import React, { useState, useEffect } from 'react';
import { Event } from '../services/api';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

interface EventsCarouselProps {
  events: Event[];
  onEventClick: (event: Event) => void;
  autoSlideInterval?: number; // в миллисекундах
}

const EventsCarousel: React.FC<EventsCarouselProps> = ({ 
  events, 
  onEventClick, 
  autoSlideInterval = 8000 
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);

  // Автолистание каждые 8 секунд
  useEffect(() => {
    if (!isAutoPlaying || events.length <= 1) return;

    const interval = setInterval(() => {
      setCurrentIndex((prevIndex) => 
        prevIndex === events.length - 1 ? 0 : prevIndex + 1
      );
    }, autoSlideInterval);

    return () => clearInterval(interval);
  }, [isAutoPlaying, events.length, autoSlideInterval]);

  const goToPrevious = () => {
    setCurrentIndex(currentIndex === 0 ? events.length - 1 : currentIndex - 1);
    setIsAutoPlaying(false); // Останавливаем автолистание при ручном управлении
  };

  const goToNext = () => {
    setCurrentIndex(currentIndex === events.length - 1 ? 0 : currentIndex + 1);
    setIsAutoPlaying(false); // Останавливаем автолистание при ручном управлении
  };

  const goToSlide = (index: number) => {
    setCurrentIndex(index);
    setIsAutoPlaying(false); // Останавливаем автолистание при ручном управлении
  };

  if (events.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Нет мероприятий для отображения</p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Основной контейнер карусели */}
      <div className="relative overflow-hidden rounded-2xl">
        <div 
          className="flex transition-transform duration-500 ease-in-out"
          style={{ transform: `translateX(-${currentIndex * 100}%)` }}
        >
          {events.map((event, index) => {
            const hasRating = typeof event.rating === 'number' && !Number.isNaN(event.rating);
            const ratingValue = hasRating ? event.rating!.toFixed(1) : '—';
            const hasDiscount = typeof event.discount === 'number' && !Number.isNaN(event.discount);
            const discountLabel = hasDiscount ? `до ${Math.round(event.discount ?? 0)}%` : null;
            const hasPrice = typeof event.price === 'number' && !Number.isNaN(event.price);
            const priceLabel = hasPrice
              ? event.price === 0
                ? 'Бесплатно'
                : `от ${new Intl.NumberFormat('ru-RU').format(event.price ?? 0)} ₽`
              : 'Цена по запросу';

            return (
              <div key={event.id} className="w-full flex-shrink-0">
                <div
                  className="relative h-80 bg-cover bg-center rounded-2xl cursor-pointer group"
                  style={{
                    backgroundImage: event.image_url
                      ? `url(${event.image_url})`
                      : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                  }}
                  onClick={() => onEventClick(event)}
                >
                  {/* Fallback изображение если основное не загрузилось */}
                  {event.image_url && (
                    <img
                      src={event.image_url}
                      alt={event.title}
                    className="absolute inset-0 w-full h-full object-cover rounded-2xl opacity-0"
                    onError={(e) => {
                      // Если изображение не загрузилось, показываем градиент
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                )}
                {/* Overlay для лучшей читаемости текста */}
                <div className="absolute inset-0 bg-black bg-opacity-40 rounded-2xl"></div>
                
                  {/* Контент баннера */}
                  <div className="relative h-full flex flex-col justify-between p-6 text-white">
                    {/* Верхняя часть - категория и рейтинг */}
                    <div className="flex justify-between items-start">
                      <div className="flex items-center space-x-2">
                        <div className={`px-2 py-1 rounded-full text-xs font-medium ${hasRating ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-800'}`}>
                          {ratingValue}
                        </div>
                        <span className="text-sm font-medium">
                          {event.category?.name ?? 'Мероприятие'} • 18+
                        </span>
                      </div>
                    </div>

                  {/* Нижняя часть - название и детали */}
                    <div className="space-y-2">
                      <h3 className="text-2xl font-bold line-clamp-2">
                        {event.title}
                      </h3>
                      <p className="text-sm opacity-90">
                        {event.location} • {format(new Date(event.datetime), 'd MMMM', { locale: ru })}
                      </p>
                      <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-2">
                          {discountLabel && (
                            <span className="text-xs bg-purple-500 px-2 py-1 rounded">
                              {discountLabel}
                            </span>
                          )}
                        </div>
                        <div className="bg-yellow-400 text-gray-900 px-3 py-1 rounded-full text-sm font-medium">
                          {priceLabel}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Кнопки навигации */}
        {events.length > 1 && (
          <>
            <button
              onClick={goToPrevious}
              className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-2 rounded-full transition-all duration-200"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              onClick={goToNext}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-2 rounded-full transition-all duration-200"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </>
        )}
      </div>

      {/* Индикаторы слайдов */}
      {events.length > 1 && (
        <div className="flex justify-center space-x-2 mt-4">
          {events.map((_, index) => (
            <button
              key={index}
              onClick={() => goToSlide(index)}
              className={`w-2 h-2 rounded-full transition-all duration-200 ${
                index === currentIndex 
                  ? 'bg-blue-600 w-8' 
                  : 'bg-gray-300 hover:bg-gray-400'
              }`}
            />
          ))}
        </div>
      )}

      {/* Кнопка возобновления автолистания */}
      {events.length > 1 && !isAutoPlaying && (
        <div className="text-center mt-4">
          <button
            onClick={() => setIsAutoPlaying(true)}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Возобновить автолистание
          </button>
        </div>
      )}
    </div>
  );
};

export default EventsCarousel;
