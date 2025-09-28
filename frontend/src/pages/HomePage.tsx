import React, { useState } from 'react';
import { Event } from '../services/api';
import Header from '../components/Header';
import Hero from '../components/Hero';
import EventsFeed from '../components/EventsFeed';
import Contact from '../components/Contact';
import EventModal from '../components/EventModal';
import Footer from '../components/Footer';
import DateScroller from '../components/DateScroller';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

const HomePage: React.FC = () => {
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [startDate, setStartDate] = useState<Date | undefined>(undefined);
  const [endDate, setEndDate] = useState<Date | undefined>(undefined);
  const city = 'Санкт‑Петербург';

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
      <main>
        <Hero />
        
        {/* Date Selector Section */}
        <section className="py-8 bg-white border-b border-gray-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
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
        </section>

        <EventsFeed
          onEventClick={handleEventClick}
          dateFrom={startDate ? format(startDate, 'yyyy-MM-dd') : undefined}
          dateTo={startDate && endDate ? format(endDate, 'yyyy-MM-dd') : undefined}
        />
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
