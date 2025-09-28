import React, { useEffect, useMemo, useRef, useState } from 'react';
import { format, isSameDay, addDays, startOfDay } from 'date-fns';
import { ru } from 'date-fns/locale';

export interface DateScrollerProps {
  startDate?: Date; // default: today
  totalDays?: number; // default: 60
  // Optional controlled range
  startSelectedDate?: Date;
  endSelectedDate?: Date;
  // Emits on every selection change
  onDateChange?: (startDate: Date, endDate?: Date) => void;
  className?: string;
}

interface DayItem {
  date: Date;
  dayLabel: string; // пн, вт, ср...
  dateNum: string; // 1..31
  isWeekend: boolean;
  monthLabel: string; // Сентябрь, Октябрь
}

const isWeekendRu = (date: Date): boolean => {
  const day = date.getDay(); // 0=Sun, 6=Sat
  return day === 0 || day === 6;
};

const DateScroller: React.FC<DateScrollerProps> = ({
  startDate,
  totalDays = 60,
  startSelectedDate,
  endSelectedDate,
  onDateChange,
  className = '',
}) => {
  const today = useMemo(() => startOfDay(startDate ?? new Date()), [startDate]);
  // rangeStart may be undefined (no date selected on initial load)
  const [rangeStart, setRangeStart] = useState<Date | undefined>(startSelectedDate ? startOfDay(startSelectedDate) : undefined);
  const [rangeEnd, setRangeEnd] = useState<Date | undefined>(endSelectedDate ? startOfDay(endSelectedDate) : undefined);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (startSelectedDate) setRangeStart(startOfDay(startSelectedDate));
  }, [startSelectedDate]);
  useEffect(() => {
    setRangeEnd(endSelectedDate ? startOfDay(endSelectedDate) : undefined);
  }, [endSelectedDate]);

  const days: DayItem[] = useMemo(() => {
    return Array.from({ length: totalDays }).map((_, idx) => {
      const date = startOfDay(addDays(today, idx));
      return {
        date,
        dayLabel: format(date, 'EE', { locale: ru }).replace('.', ''),
        dateNum: format(date, 'd', { locale: ru }),
        isWeekend: isWeekendRu(date),
        monthLabel: format(date, 'LLLL', { locale: ru }),
      };
    });
  }, [today, totalDays]);

  const handleSelect = (date: Date) => {
    // 3-state selection: start → end → restart
    if (!rangeStart || (rangeStart && rangeEnd)) {
      setRangeStart(date);
      setRangeEnd(undefined);
      onDateChange?.(date, undefined);
      return;
    }
    if (rangeStart && !rangeEnd) {
      if (date.getTime() === rangeStart.getTime()) {
        // Single date stays as-is (toggle off)
        setRangeStart(undefined);
        setRangeEnd(undefined);
        onDateChange?.(undefined as any, undefined);
        return;
      }
      const [start, end] = date < rangeStart ? [date, rangeStart] : [rangeStart, date];
      setRangeStart(start);
      setRangeEnd(end);
      onDateChange?.(start, end);
      return;
    }
  };

  const [showLeft, setShowLeft] = useState(false);

  const scrollByAmount = (dir: 'left' | 'right') => {
    const el = scrollRef.current;
    if (!el) return;
    // Scroll by ~1 week worth of items (approx 80% of viewport)
    const amount = Math.round(el.clientWidth * 0.8);
    el.scrollBy({ left: dir === 'left' ? -amount : amount, behavior: 'smooth' });
    // after scrolling, update left button visibility
    setTimeout(() => {
      const cur = scrollRef.current;
      if (!cur) return;
      setShowLeft(cur.scrollLeft > 10);
    }, 300);
  };

  // Auto-scroll to focused date (end or start). On initial mount keep scroller at left-most position
  const initialMount = useRef(true);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (initialMount.current) {
      // keep scroller at left-most position on first render so 'today' is at the beginning
      initialMount.current = false;
      el.scrollLeft = 0;
      setShowLeft(false);
      return;
    }
  const focusDate = rangeEnd ?? rangeStart;
  if (!focusDate) return;
  const btn = el.querySelector<HTMLButtonElement>(`button[data-date="${format(focusDate, 'yyyy-MM-dd')}"]`);
  if (btn) {
      const btnRect = btn.getBoundingClientRect();
      const elRect = el.getBoundingClientRect();
      if (btnRect.left < elRect.left || btnRect.right > elRect.right) {
        const offset = btn.offsetLeft - (el.clientWidth / 2 - btn.clientWidth / 2);
        el.scrollTo({ left: offset, behavior: 'smooth' });
      }
    }
  }, [rangeStart, rangeEnd]);

  // Update left button when user manually scrolls
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      setShowLeft(el.scrollLeft > 10);
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, []);

  // Group by month to show headers
  const monthGroups = useMemo(() => {
    const groups: Array<{ key: string; label: string; items: DayItem[] }> = [];
    let currentKey = '';
    let current: DayItem[] = [];
    days.forEach((d, idx) => {
      const key = format(d.date, 'yyyy-MM', { locale: ru });
      if (idx === 0) {
        currentKey = key;
        current = [d];
      } else if (key !== currentKey) {
        groups.push({ key: currentKey, label: format(current[0].date, 'LLLL yyyy', { locale: ru }), items: current });
        currentKey = key;
        current = [d];
      } else {
        current.push(d);
      }
    });
    if (current.length) {
      groups.push({ key: currentKey, label: format(current[0].date, 'LLLL yyyy', { locale: ru }), items: current });
    }
    return groups;
  }, [days]);

  return (
    <div className={`relative ${className}`}>
      <div className="flex items-center gap-3">
        {/* Left arrow appears only after user scrolled right */}
        {showLeft && (
          <button
            aria-label="Previous"
            onClick={() => scrollByAmount('left')}
            className="hidden md:flex h-10 w-10 items-center justify-center rounded-full bg-black/30 hover:bg-black/40 text-white backdrop-blur-sm transition-colors"
          >
            <span className="sr-only">Previous</span>
            ‹
          </button>
        )}

        <div
          ref={scrollRef}
          className="overflow-x-auto no-scrollbar scroll-smooth flex-1"
        >
          <div className="flex w-max select-none gap-6 px-2 py-2">
            {monthGroups.map(group => (
              <div key={group.key} className="min-w-max">
                <div className="px-2 pb-2 text-sm font-medium uppercase text-gray-500">
                  {group.label}
                </div>
                <div className="flex items-stretch gap-2">
                  {group.items.map(d => {
                    const inRange = rangeEnd ? (rangeStart && d.date >= rangeStart && d.date <= rangeEnd) : (rangeStart ? isSameDay(d.date, rangeStart) : false);
                    const isStart = rangeStart ? isSameDay(d.date, rangeStart) : false;
                    const isEnd = !!rangeEnd && rangeEnd ? isSameDay(d.date, rangeEnd) : false;
                    const base = 'flex flex-col items-center px-3 py-2 rounded-xl transition-colors duration-200';
                    const state = isStart || isEnd
                      ? 'bg-blue-600 text-white'
                      : inRange
                        ? 'bg-blue-100 text-gray-900'
                        : 'hover:bg-gray-100 bg-white text-gray-900';
                    const weekend = d.isWeekend && !(isStart || isEnd) ? 'text-red-600' : '';
                    return (
                      <button
                        key={d.date.toISOString()}
                        data-date={format(d.date, 'yyyy-MM-dd')}
                        onClick={() => handleSelect(d.date)}
                        className={`${base} ${state}`}
                      >
                        <span className={`text-[10px] uppercase tracking-wide ${weekend}`}>
                          {d.dayLabel}
                        </span>
                        <span className={`font-bold text-lg leading-5 ${weekend}`}>
                          {d.dateNum}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Next button placed after scroller */}
        <button
          aria-label="Next"
          onClick={() => scrollByAmount('right')}
          className="hidden md:flex h-10 w-10 items-center justify-center rounded-full bg-black/30 hover:bg-black/40 text-white backdrop-blur-sm transition-colors"
        >
          <span className="sr-only">Next</span>
          ›
        </button>
      </div>
    </div>
  );
};

export default DateScroller;


