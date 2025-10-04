import React from 'react';
import { Event } from '../services/api';
import { ChevronRight, Heart } from 'lucide-react';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

interface CategorySectionProps {
  title: string;
  events: Event[];
  onEventClick: (event: Event) => void;
  loading?: boolean;
}

const CategorySection: React.FC<CategorySectionProps> = ({ 
  title, 
  events, 
  onEventClick, 
  loading = false 
}) => {
  if (loading) {
    return (
      <section className="py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-48 mb-4"></div>
            <div className="flex space-x-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="w-64 h-80 bg-gray-200 rounded-lg"></div>
              ))}
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (events.length === 0) {
    return null;
  }

  return (
    <section className="py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Заголовок секции */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-gray-900">
            {title}
          </h3>
          <button className="flex items-center text-blue-600 hover:text-blue-700 font-medium">
            Все события
            <ChevronRight className="w-4 h-4 ml-1" />
          </button>
        </div>

        {/* Горизонтальная прокрутка карточек */}
        <div className="relative">
          <div className="flex space-x-4 overflow-x-auto pb-4 scrollbar-hide">
            {events.map((event) => (
              <div
                key={event.id}
                className="flex-shrink-0 w-64 cursor-pointer group"
                onClick={() => onEventClick(event)}
              >
                <div className="bg-white rounded-lg border border-gray-200 hover:shadow-lg transition-all duration-200 overflow-hidden">
                  {/* Изображение */}
                  <div className="aspect-[4/3] relative overflow-hidden">
                    {event.image_url ? (
                      <img 
                        src={event.image_url} 
                        alt={event.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                      />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center">
                        <div className="text-gray-300 text-4xl">🎭</div>
                      </div>
                    )}
                    
                    {/* Рейтинг */}
                    <div className="absolute top-2 left-2">
                      <div className="bg-green-500 text-white px-2 py-1 rounded-full text-xs font-medium">
                        8.2
                      </div>
                    </div>

                    {/* Кнопка избранного */}
                    <button 
                      className="absolute top-2 right-2 p-1.5 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full transition-all duration-200"
                      onClick={(e) => {
                        e.stopPropagation();
                        // TODO: Добавить в избранное
                      }}
                    >
                      <Heart className="w-4 h-4 text-white" />
                    </button>

                    {/* Категория */}
                    <div className="absolute bottom-2 left-2">
                      <span className="bg-black bg-opacity-50 text-white px-2 py-1 rounded text-xs font-medium">
                        {event.category === 'concert' ? 'Концерт' : 
                         event.category === 'theatre' ? 'Театр' : 
                         event.category === 'exhibition' ? 'Выставка' : 
                         'Мероприятие'} • 18+
                      </span>
                    </div>
                  </div>

                  {/* Контент карточки */}
                  <div className="p-4">
                    <h4 className="font-semibold text-gray-900 mb-2 line-clamp-2">
                      {event.title}
                    </h4>
                    <p className="text-sm text-gray-600 mb-3">
                      {event.location} • {format(new Date(event.datetime), 'd MMMM, HH:mm', { locale: ru })}
                    </p>
                    
                    {/* Цена и скидка */}
                    <div className="flex justify-between items-center">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                          до 15%
                        </span>
                      </div>
                      <div className="text-sm font-medium text-gray-900">
                        от 1700 ₽
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default CategorySection;
