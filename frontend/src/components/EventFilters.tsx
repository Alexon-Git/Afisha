import React, { useMemo, useState } from 'react';
import { Calendar, Filter, X, MapPin, Clock } from 'lucide-react';
import { format, addDays, startOfWeek, endOfWeek } from 'date-fns';

import { Category } from '../services/api';

export interface FilterState {
  date?: string;
  date_from?: string;
  date_to?: string;
  category?: string;
  location?: string;
  sort?: 'asc' | 'desc';
}

interface EventFiltersProps {
  filters: FilterState;
  categories: Category[];
  categoriesLoading?: boolean;
  onFiltersChange: (filters: FilterState) => void;
  onClearFilters: () => void;
}

const EventFilters: React.FC<EventFiltersProps> = ({
  filters,
  categories,
  categoriesLoading = false,
  onFiltersChange,
  onClearFilters
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const datePresets = [
    { key: 'today', label: 'Сегодня', icon: '📅' },
    { key: 'tomorrow', label: 'Завтра', icon: '📆' },
    { key: 'weekend', label: 'Выходные', icon: '🎉' },
    { key: 'week', label: 'Эта неделя', icon: '📊' },
  ];

  const categoryOptions = useMemo(
    () => [
      { slug: '', label: 'Все категории' },
      ...categories
        .filter(category => category.is_active)
        .map(category => ({ slug: category.slug, label: category.name })),
    ],
    [categories]
  );

  const locations = [
    { key: '', label: 'Все места' },
    { key: 'center', label: 'Центр города' },
    { key: 'vasileostrovskaya', label: 'Васильевский остров' },
    { key: 'petrogradskaya', label: 'Петроградская' },
    { key: 'nevsky', label: 'Невский проспект' },
  ];

  const sortOptions = [
    { key: 'asc', label: 'Сначала ближайшие' },
    { key: 'desc', label: 'Сначала дальние' },
  ];

  const handleDatePreset = (preset: string) => {
    const today = new Date();
    let dateFrom = '';
    let dateTo = '';

    switch (preset) {
      case 'today':
        dateFrom = format(today, 'yyyy-MM-dd');
        dateTo = format(today, 'yyyy-MM-dd');
        break;
      case 'tomorrow':
        const tomorrow = addDays(today, 1);
        dateFrom = format(tomorrow, 'yyyy-MM-dd');
        dateTo = format(tomorrow, 'yyyy-MM-dd');
        break;
      case 'weekend':
        const saturday = startOfWeek(today, { weekStartsOn: 6 });
        const sunday = endOfWeek(today, { weekStartsOn: 6 });
        dateFrom = format(saturday, 'yyyy-MM-dd');
        dateTo = format(sunday, 'yyyy-MM-dd');
        break;
      case 'week':
        const weekStart = startOfWeek(today, { weekStartsOn: 1 });
        const weekEnd = endOfWeek(today, { weekStartsOn: 1 });
        dateFrom = format(weekStart, 'yyyy-MM-dd');
        dateTo = format(weekEnd, 'yyyy-MM-dd');
        break;
    }

    onFiltersChange({
      ...filters,
      date: preset,
      date_from: dateFrom,
      date_to: dateTo,
    });
  };

  const handleCustomDate = (field: 'date_from' | 'date_to', value: string) => {
    onFiltersChange({
      ...filters,
      [field]: value,
      date: undefined, // Clear preset when using custom date
    });
  };

  const hasActiveFilters = Object.values(filters).some(value => value && value !== '');

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 shadow-sm">
      {/* Main Filters Row */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        {/* Date Presets */}
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">Дата:</span>
          <div className="flex gap-1">
            {datePresets.map(preset => (
              <button
                key={preset.key}
                onClick={() => handleDatePreset(preset.key)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  filters.date === preset.key
                    ? 'bg-blue-100 text-blue-700 border border-blue-200'
                    : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'
                }`}
              >
                <span className="mr-1">{preset.icon}</span>
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        {/* Custom Date Range */}
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={filters.date_from || ''}
            onChange={(e) => handleCustomDate('date_from', e.target.value)}
            className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="От"
          />
          <span className="text-gray-400">—</span>
          <input
            type="date"
            value={filters.date_to || ''}
            onChange={(e) => handleCustomDate('date_to', e.target.value)}
            className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="До"
          />
        </div>

        {/* Category Filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-500" />
          <select
            value={filters.category || ''}
            onChange={(e) => onFiltersChange({ ...filters, category: e.target.value || undefined })}
            className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={categoriesLoading}
          >
            {categoryOptions.map(cat => (
              <option key={cat.slug} value={cat.slug}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>

        {/* Sort */}
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-gray-500" />
          <select
            value={filters.sort || 'asc'}
            onChange={(e) => onFiltersChange({ ...filters, sort: e.target.value as 'asc' | 'desc' })}
            className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {sortOptions.map(option => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Advanced Filters Toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="px-3 py-1.5 text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          {showAdvanced ? 'Скрыть' : 'Ещё фильтры'}
        </button>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <button
            onClick={onClearFilters}
            className="px-3 py-1.5 text-sm text-red-600 hover:text-red-700 font-medium flex items-center gap-1"
          >
            <X className="h-3 w-3" />
            Очистить
          </button>
        )}
      </div>

      {/* Advanced Filters */}
      {showAdvanced && (
        <div className="border-t border-gray-100 pt-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Location Filter */}
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Район:</span>
              <select
                value={filters.location || ''}
                onChange={(e) => onFiltersChange({ ...filters, location: e.target.value || undefined })}
                className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {locations.map(loc => (
                  <option key={loc.key} value={loc.key}>
                    {loc.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Price Range (placeholder for future) */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">Цена:</span>
              <select className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                <option>Любая</option>
                <option>Бесплатно</option>
                <option>До 500 ₽</option>
                <option>500-1000 ₽</option>
                <option>1000-2000 ₽</option>
                <option>От 2000 ₽</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Active Filters Display */}
      {hasActiveFilters && (
        <div className="border-t border-gray-100 pt-3 mt-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-gray-600">Активные фильтры:</span>
            {filters.date && (
              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                {datePresets.find(p => p.key === filters.date)?.label}
              </span>
            )}
            {filters.category && (
              <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">
                {categoryOptions.find(c => c.slug === filters.category)?.label || filters.category}
              </span>
            )}
            {filters.location && (
              <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">
                {locations.find(l => l.key === filters.location)?.label}
              </span>
            )}
            {(filters.date_from || filters.date_to) && (
              <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded text-xs">
                {filters.date_from && filters.date_to 
                  ? `${filters.date_from} — ${filters.date_to}`
                  : filters.date_from || filters.date_to
                }
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default EventFilters;

