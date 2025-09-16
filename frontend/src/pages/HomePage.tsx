import React, { useState, useEffect } from 'react';
import { eventsApi, Event } from '../services/api';
import Header from '../components/Header';
import Hero from '../components/Hero';
import About from '../components/About';
import EventsFeed from '../components/EventsFeed';
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
        <About />
        <EventsFeed onEventClick={(ev) => { setSelectedEvent(ev); setIsModalOpen(true); }} />
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
