import React, { useState } from 'react';
import { Search, MapPin } from 'lucide-react';

const Header: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');

  const categories = [
    'Сертификаты',
    'Кино', 
    'Концерты',
    'Театр',
    'Детям',
    'Выставки',
    'Спорт',
    'Стендап',
    'Ещё'
  ];

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      {/* Верхняя панель */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          {/* Логотип */}
          <div className="flex items-center space-x-3">
            <div className="bg-primary-600 p-2 rounded-lg">
              {/* <Calendar className="h-6 w-6 text-white" /> */}
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Афиша мероприятий</h1>
            </div>
          </div>

          {/* Поиск */}
          <div className="flex-1 max-w-2xl mx-8">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="События, артисты и места"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Правая панель */}
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-gray-600">
              <MapPin className="h-4 w-4" />
              <span className="font-medium">Новосибирск</span>
            </div>
            {/* <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
              <Plus className="h-5 w-5 text-gray-600" />
            </button>
            <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
              <User className="h-5 w-5 text-gray-600" />
            </button> */}
          </div>
        </div>
      </div>

      {/* Навигационное меню */}
      <div className="border-t border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex items-center space-x-8 py-3 overflow-x-auto scrollbar-hide">
            {categories.map((category) => (
              <button
                key={category}
                className="flex-shrink-0 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors whitespace-nowrap"
              >
                {category}
              </button>
            ))}
          </nav>
        </div>
      </div>
    </header>
  );
};

export default Header;
