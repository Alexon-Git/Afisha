import React from 'react';
import { ArrowDown, Star, Users, Calendar } from 'lucide-react';

const Hero: React.FC = () => {
  return (
    <section className="relative bg-gradient-to-br from-primary-600 via-primary-700 to-primary-800 text-white">
      <div className="absolute inset-0 bg-black opacity-20"></div>
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center">
          <h1 className="text-4xl md:text-6xl font-bold mb-6">
            Добро пожаловать в мир
            <span className="block text-yellow-300">ярких событий</span>
          </h1>
          <p className="text-xl md:text-2xl mb-8 text-primary-100 max-w-3xl mx-auto">
            Откройте для себя удивительные мероприятия, концерты, выставки и многое другое. 
            Ваше следующее незабываемое впечатление ждет вас!
          </p>
          <div className="flex justify-center">
            <a 
              href="#events" 
              className="inline-flex items-center space-x-2 bg-yellow-400 hover:bg-yellow-500 text-gray-900 font-semibold px-8 py-4 rounded-lg transition-colors duration-200"
            >
              <Calendar className="h-5 w-5" />
              <span>Посмотреть мероприятия</span>
              <ArrowDown className="h-5 w-5" />
            </a>
          </div>
        </div>
        
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="text-center">
            <div className="bg-white bg-opacity-20 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
              <Star className="h-8 w-8" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Качественные события</h3>
            <p className="text-primary-100">Тщательно отобранные мероприятия от лучших организаторов</p>
          </div>
          
          <div className="text-center">
            <div className="bg-white bg-opacity-20 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
              <Users className="h-8 w-8" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Сообщество</h3>
            <p className="text-primary-100">Присоединяйтесь к активному сообществу любителей событий</p>
          </div>
          
          <div className="text-center">
            <div className="bg-white bg-opacity-20 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
              <Calendar className="h-8 w-8" />
            </div>
            <h3 className="text-xl font-semibold mb-2">Удобный календарь</h3>
            <p className="text-primary-100">Планируйте свое время с помощью интуитивного календаря</p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
