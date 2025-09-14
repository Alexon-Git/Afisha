import React from 'react';
import { Heart, Music, Camera, Palette } from 'lucide-react';

const About: React.FC = () => {
  return (
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            О нашей площадке
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Мы создаем пространство, где искусство встречается с технологиями, 
            а традиции переплетаются с инновациями
          </p>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">
              Наша миссия
            </h3>
            <p className="text-gray-600 mb-6 leading-relaxed">
              Мы стремимся объединить людей через искусство и культуру, создавая 
              уникальные пространства для творческого самовыражения и культурного обмена. 
              Наша площадка — это место, где каждый может найти вдохновение и открыть 
              для себя что-то новое.
            </p>
            <p className="text-gray-600 leading-relaxed">
              С 2020 года мы организуем мероприятия различных форматов: от камерных 
              концертов до масштабных фестивалей, от художественных выставок до 
              образовательных лекций.
            </p>
          </div>
          
          <div className="grid grid-cols-2 gap-6">
            <div className="text-center p-6 bg-gray-50 rounded-xl">
              <div className="bg-primary-100 p-3 rounded-full w-12 h-12 mx-auto mb-4 flex items-center justify-center">
                <Music className="h-6 w-6 text-primary-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">Музыка</h4>
              <p className="text-sm text-gray-600">Концерты и музыкальные вечера</p>
            </div>
            
            <div className="text-center p-6 bg-gray-50 rounded-xl">
              <div className="bg-primary-100 p-3 rounded-full w-12 h-12 mx-auto mb-4 flex items-center justify-center">
                <Palette className="h-6 w-6 text-primary-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">Искусство</h4>
              <p className="text-sm text-gray-600">Выставки и арт-проекты</p>
            </div>
            
            <div className="text-center p-6 bg-gray-50 rounded-xl">
              <div className="bg-primary-100 p-3 rounded-full w-12 h-12 mx-auto mb-4 flex items-center justify-center">
                <Camera className="h-6 w-6 text-primary-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">Фотография</h4>
              <p className="text-sm text-gray-600">Мастер-классы и выставки</p>
            </div>
            
            <div className="text-center p-6 bg-gray-50 rounded-xl">
              <div className="bg-primary-100 p-3 rounded-full w-12 h-12 mx-auto mb-4 flex items-center justify-center">
                <Heart className="h-6 w-6 text-primary-600" />
              </div>
              <h4 className="font-semibold text-gray-900 mb-2">Сообщество</h4>
              <p className="text-sm text-gray-600">Встречи и общение</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default About;
