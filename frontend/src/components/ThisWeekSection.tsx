import React, { useState, useEffect } from 'react';
import { Event } from '../services/api';
import { ChevronLeft, ChevronRight, Heart } from 'lucide-react';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

interface ThisWeekSectionProps {
  events: Event[];
  onEventClick: (event: Event) => void;
  loading?: boolean;
}

const ThisWeekSection: React.FC<ThisWeekSectionProps> = ({ 
  events, 
  onEventClick, 
  loading = false 
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);

  const goToPrevious = () => {
    setCurrentIndex(currentIndex === 0 ? events.length - 1 : currentIndex - 1);
  };

  const goToNext = () => {
    setCurrentIndex(currentIndex === events.length - 1 ? 0 : currentIndex + 1);
  };

  const goToSlide = (index: number) => {
    setCurrentIndex(index);
  };

  if (loading) {
    return (
      <section className="py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Загрузка мероприятий...</p>
          </div>
        </div>
      </section>
    );
  }

  if (events.length === 0) {
    return (
      <section className="py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center py-12">
            <p className="text-gray-500">Нет мероприятий на эту неделю</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Заголовок секции */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            На этой неделе
          </h2>
          <button className="flex items-center text-blue-600 hover:text-blue-700 font-medium">
            Все события
            <ChevronRight className="w-4 h-4 ml-1" />
          </button>
        </div>

        {/* Карусель мероприятий */}
        <div className="relative">
          <div className="overflow-hidden rounded-2xl">
            <div 
              className="flex transition-transform duration-500 ease-in-out"
              style={{ transform: `translateX(-${currentIndex * 100}%)` }}
            >
              {events.map((event, index) => (
                <div key={event.id} className="w-full flex-shrink-0">
                  <div 
                    className="relative h-96 bg-cover bg-center rounded-2xl cursor-pointer group"
                    style={{
                      backgroundImage: event.image_url 
                        ? `url(${event.image_url})`
                        : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                    }}
                    onClick={() => onEventClick(event)}
                  >
                    {/* Overlay для лучшей читаемости текста */}
                    <div className="absolute inset-0 bg-black bg-opacity-30 rounded-2xl"></div>
                    
                    {/* Кнопка избранного */}
                    <button 
                      className="absolute top-4 right-4 p-2 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full transition-all duration-200"
                      onClick={(e) => {
                        e.stopPropagation();
                        // TODO: Добавить в избранное
                      }}
                    >
                      <Heart className="w-5 h-5 text-white" />
                    </button>

                    {/* Контент баннера */}
                    <div className="relative h-full flex flex-col justify-between p-8 text-white">
                      {/* Верхняя часть - категория и рейтинг */}
                      <div className="flex justify-between items-start">
                        <div className="flex items-center space-x-3">
                          <div className="bg-green-500 text-white px-3 py-1 rounded-full text-sm font-medium">
                            8.2
                          </div>
                          <span className="text-sm font-medium bg-black bg-opacity-50 px-3 py-1 rounded-full">
                            {event.category === 'concert' ? 'Концерт' : 
                             event.category === 'theatre' ? 'Театр' : 
                             event.category === 'exhibition' ? 'Выставка' : 
                             'Мероприятие'} • 18+
                          </span>
                        </div>
                      </div>

                      {/* Нижняя часть - название и детали */}
                      <div className="space-y-4">
                        <h3 className="text-3xl font-bold line-clamp-2">
                          {event.title}
                        </h3>
                        <p className="text-lg opacity-90">
                          {event.location} • {format(new Date(event.datetime), 'd MMMM, HH:mm', { locale: ru })}
                        </p>
                        <div className="flex justify-between items-center">
                          <div className="flex items-center space-x-3">
                            <span className="text-sm bg-purple-500 px-3 py-1 rounded-full">
                              до 15%
                            </span>
                          </div>
                          <div className="bg-yellow-400 text-gray-900 px-4 py-2 rounded-full text-lg font-medium">
                            от 1700 ₽
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Кнопки навигации */}
            {events.length > 1 && (
              <>
                <button
                  onClick={goToPrevious}
                  className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-3 rounded-full transition-all duration-200"
                >
                  <ChevronLeft className="w-6 h-6" />
                </button>
                <button
                  onClick={goToNext}
                  className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-black bg-opacity-50 hover:bg-opacity-70 text-white p-3 rounded-full transition-all duration-200"
                >
                  <ChevronRight className="w-6 h-6" />
                </button>
              </>
            )}
          </div>

          {/* Индикаторы слайдов */}
          {events.length > 1 && (
            <div className="flex justify-center space-x-2 mt-6">
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
        </div>
      </div>
    </section>
  );
};

export default ThisWeekSection;
