import React, { useState, useEffect } from 'react';
import { Category, Event, categoriesApi, eventsApi } from '../services/api';
import Header from '../components/Header';
import ThisWeekSection from '../components/ThisWeekSection';
import CategorySection from '../components/CategorySection';
import Contact from '../components/Contact';
import EventModal from '../components/EventModal';
import Footer from '../components/Footer';
import DateScroller from '../components/DateScroller';
import YandexAdBanner from '../components/YandexAdBanner';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

const HomePage: React.FC = () => {
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [startDate, setStartDate] = useState<Date | undefined>(undefined);
  const [endDate, setEndDate] = useState<Date | undefined>(undefined);
  const [thisWeekEvents, setThisWeekEvents] = useState<Event[]>([]);
  const [categorySections, setCategorySections] = useState<{ category: Category; events: Event[] }[]>([]);
  const [loading, setLoading] = useState(false);
  const city = 'Новосибирск';

  // Загрузка событий по категориям
  const loadEvents = async () => {
    setLoading(true);
    try {
      const [thisWeekResponse, categoriesResponse] = await Promise.all([
        eventsApi.getAll(1, 5),
        categoriesApi.getAll(),
      ]);

      setThisWeekEvents(thisWeekResponse.data.items ?? []);

      const activeCategories = (categoriesResponse.data ?? []).filter(category => category.is_active);
      const highlightedCategories = activeCategories.slice(0, 3);

      const sections = await Promise.all(
        highlightedCategories.map(async (category) => {
          const response = await eventsApi.getAll(1, 6, { category: category.slug });
          return {
            category,
            events: response.data.items ?? [],
          };
        })
      );

      setCategorySections(sections);
    } catch (error) {
      console.error('Ошибка загрузки событий:', error);
      setCategorySections([]);
    } finally {
      setLoading(false);
    }
  };

  // Загружаем события при монтировании компонента
  useEffect(() => {
    loadEvents();
  }, []);

  const handleEventClick = (event: Event) => {
    setSelectedEvent(event);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedEvent(null);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      {/* Баннер Яндекс.Директ */}
      <section className="bg-white py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <YandexAdBanner />
        </div>
      </section>
      
      <main>
        {/* Заголовок и выбор даты */}
        <section className="py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6 sm:p-8">
              <div className="text-center mb-6">
                <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
                  Афиша событий в {city}
                </h2>
                <p className="text-gray-600">
                  {startDate ? (
                    endDate
                      ? `События с ${format(startDate, 'd MMMM', { locale: ru })} по ${format(endDate, 'd MMMM yyyy', { locale: ru })}`
                      : `События на ${format(startDate, 'd MMMM yyyy', { locale: ru })}`
                  ) : (
                    'Выберите дату, чтобы отфильтровать мероприятия'
                  )}
                </p>
              </div>
              <DateScroller
                startSelectedDate={startDate}
                endSelectedDate={endDate}
                onDateChange={(start, end) => {
                  setStartDate(start as Date | undefined);
                  setEndDate(end as Date | undefined);
                }}
                totalDays={90}
              />
              
            </div>
          </div>
        </section>

        {/* Секция "На этой неделе" */}
        <ThisWeekSection 
          events={thisWeekEvents}
          onEventClick={handleEventClick}
          loading={loading}
        />

        {/* Секции по категориям */}
        {categorySections.map(({ category, events }) => (
          <CategorySection
            key={category.id}
            title={category.name}
            events={events}
            onEventClick={handleEventClick}
            loading={loading}
          />
        ))}

        <Contact />
      </main>
      
      <Footer />
      
      {isModalOpen && selectedEvent && (
        <EventModal 
          event={selectedEvent} 
          onClose={closeModal}
        />
      )}
    </div>
  );
};

export default HomePage;
