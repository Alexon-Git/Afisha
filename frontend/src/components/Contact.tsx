import React from 'react';
import { MapPin, Phone, Mail, Clock, Facebook, Instagram, Twitter } from 'lucide-react';

const Contact: React.FC = () => {
  return (
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Контакты
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Свяжитесь с нами для получения дополнительной информации
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          {/* Контактная информация */}
          <div>
            <h3 className="text-2xl font-semibold text-gray-900 mb-8">
              Свяжитесь с нами
            </h3>
            
            <div className="space-y-6">
              <div className="flex items-start space-x-4">
                <div className="bg-primary-100 p-3 rounded-lg">
                  <MapPin className="h-6 w-6 text-primary-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Адрес</h4>
                  <p className="text-gray-600">
                    Москва, ул. Примерная, 123<br />
                    Ближайшее метро: Примерная
                  </p>
                </div>
              </div>
              
              <div className="flex items-start space-x-4">
                <div className="bg-primary-100 p-3 rounded-lg">
                  <Phone className="h-6 w-6 text-primary-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Телефон</h4>
                  <p className="text-gray-600">+7 (495) 123-45-67</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-4">
                <div className="bg-primary-100 p-3 rounded-lg">
                  <Mail className="h-6 w-6 text-primary-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Email</h4>
                  <p className="text-gray-600">info@afisha.ru</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-4">
                <div className="bg-primary-100 p-3 rounded-lg">
                  <Clock className="h-6 w-6 text-primary-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Часы работы</h4>
                  <p className="text-gray-600">
                    Пн-Пт: 10:00 - 22:00<br />
                    Сб-Вс: 12:00 - 24:00
                  </p>
                </div>
              </div>
            </div>
            
            {/* Социальные сети */}
            <div className="mt-8">
              <h4 className="font-semibold text-gray-900 mb-4">Мы в социальных сетях</h4>
              <div className="flex space-x-4">
                <a
                  href="https://facebook.com"
                  target="_blank"
                  rel="noreferrer"
                  className="bg-gray-100 hover:bg-gray-200 p-3 rounded-lg transition-colors"
                >
                  <Facebook className="h-5 w-5 text-gray-600" />
                </a>
                <a
                  href="https://instagram.com"
                  target="_blank"
                  rel="noreferrer"
                  className="bg-gray-100 hover:bg-gray-200 p-3 rounded-lg transition-colors"
                >
                  <Instagram className="h-5 w-5 text-gray-600" />
                </a>
                <a
                  href="https://twitter.com"
                  target="_blank"
                  rel="noreferrer"
                  className="bg-gray-100 hover:bg-gray-200 p-3 rounded-lg transition-colors"
                >
                  <Twitter className="h-5 w-5 text-gray-600" />
                </a>
              </div>
            </div>
          </div>
          
          {/* Карта */}
          <div>
            <h3 className="text-2xl font-semibold text-gray-900 mb-8">
              Как нас найти
            </h3>
            
            <div className="bg-gray-200 rounded-xl h-96 flex items-center justify-center">
              <div className="text-center">
                <MapPin className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">Интерактивная карта</p>
                <p className="text-sm text-gray-400 mt-2">
                  Здесь будет встроена карта с нашим местоположением
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Contact;
