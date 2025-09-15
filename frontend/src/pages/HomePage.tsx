import React, { useState, useEffect } from 'react';
import { eventsApi, Event } from '../services/api';
import Header from '../components/Header';
import Hero from '../components/Hero';
import About from '../components/About';
import CalendarGrid from '../components/CalendarGrid';
import Contact from '../components/Contact';
import EventModal from '../components/EventModal';
import Footer from '../components/Footer';

const HomePage: React.FC = () => {
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEvents();
  }, []);

  const fetchEvents = async () => {
    try {
      const response = await eventsApi.getAll();
      setEvents(response.data);
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
        <About />
        {loading ? (
          <section id="events" className="py-20 bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
                <p className="mt-4 text-gray-600">Загрузка мероприятий...</p>
              </div>
            </div>
          </section>
        ) : (
          <CalendarGrid
            events={events}
            onEventClick={handleEventClick}
          />
        )}
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
