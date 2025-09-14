import React from 'react';
import { Calendar, Heart } from 'lucide-react';

const Footer: React.FC = () => {
  return (
    <footer className="bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Логотип и описание */}
          <div>
            <div className="flex items-center space-x-3 mb-4">
              <div className="bg-primary-600 p-2 rounded-lg">
                <Calendar className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-bold">Афиша мероприятий</h3>
            </div>
            <p className="text-gray-400 mb-4">
              Современная площадка для организации и просмотра событий. 
              Объединяем людей через искусство и культуру.
            </p>
            <p className="text-sm text-gray-500">
              © 2024 Афиша мероприятий. Все права защищены.
            </p>
          </div>
          
          {/* Быстрые ссылки */}
          <div>
            <h4 className="text-lg font-semibold mb-4">Быстрые ссылки</h4>
            <ul className="space-y-2">
              <li>
                <a href="#events" className="text-gray-400 hover:text-white transition-colors">
                  Мероприятия
                </a>
              </li>
              <li>
                <a href="#about" className="text-gray-400 hover:text-white transition-colors">
                  О нас
                </a>
              </li>
              <li>
                <a href="#contact" className="text-gray-400 hover:text-white transition-colors">
                  Контакты
                </a>
              </li>
              <li>
                <a href="/admin" className="text-gray-400 hover:text-white transition-colors">
                  Админ-панель
                </a>
              </li>
            </ul>
          </div>
          
          {/* Контактная информация */}
          <div>
            <h4 className="text-lg font-semibold mb-4">Контакты</h4>
            <div className="space-y-2 text-gray-400">
              <p>Москва, ул. Примерная, 123</p>
              <p>+7 (495) 123-45-67</p>
              <p>info@afisha.ru</p>
            </div>
          </div>
        </div>
        
        <div className="border-t border-gray-800 mt-8 pt-8 text-center">
          <p className="text-gray-400 flex items-center justify-center space-x-2">
            <span>Сделано с</span>
            <Heart className="h-4 w-4 text-red-500" />
            <span>для любителей искусства</span>
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
