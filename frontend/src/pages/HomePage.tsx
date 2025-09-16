import React, { useState, useEffect } from 'react';
import { eventsApi, Event } from '../services/api';
import Header from '../components/Header';
import Hero from '../components/Hero';
import About from '../components/About';
import EventsFeed from '../components/EventsFeed';
import Contact from '../components/Contact';
import EventModal from '../components/EventModal';
import Footer from '../components/Footer';
import DateScroller from '../components/DateScroller';
import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

const HomePage: React.FC = () => {
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState<Date>(new Date());
  const [endDate, setEndDate] = useState<Date | undefined>(undefined);
  const city = 'Санкт‑Петербург';

  useEffect(() => {
    fetchEvents();
  }, []);

  const fetchEvents = async () => {
    try {
      const response = await eventsApi.getAll();
      const paginated = response.data as any;
      setEvents(paginated.items ?? paginated);
    } catch (error) {
      console.error('Ошибка при загрузке мероприятий:', error);
    } finally {
      setLoading(false);
    }
  };

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
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
          <h2 className="text-xl sm:text-2xl font-semibold mb-3">
            Афиша событий в {city}{' '}
            {endDate
              ? `[${format(startDate, 'd', { locale: ru })}–${format(endDate, 'd LLLL', { locale: ru })}]`
              : `[${format(startDate, 'd LLLL', { locale: ru })}]`}
          </h2>
          <DateScroller
            startSelectedDate={startDate}
            endSelectedDate={endDate}
            onDateChange={(start, end) => {
              setStartDate(start);
              setEndDate(end);
            }}
            totalDays={90}
          />
        </div>
        <About />
        <EventsFeed
          onEventClick={(ev) => { setSelectedEvent(ev); setIsModalOpen(true); }}
          dateFrom={format(startDate, 'yyyy-MM-dd')}
          dateTo={endDate ? format(endDate, 'yyyy-MM-dd') : undefined}
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
