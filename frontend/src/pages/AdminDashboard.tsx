import { pricingFromEvent, pricingPayload, pricingFields } from '../utils/pricing';
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  categoriesApi,
  Category,
  CategoryCreatePayload,
  CategoryUpdatePayload,
  Event,
  EventCreate,
  EventUpdate,
  eventsApi,
  organizersApi,
  Organizer,
  PublicationStatus,
  EventStatus,
} from '../services/api';
import {
  Plus,
  Edit,
  Trash2,
  LogOut,
  Calendar,
  Tag,
  Loader2,
  X
} from 'lucide-react';
import toast from 'react-hot-toast';
import { instantToEventInput, eventInputToInstant } from '../utils/eventTime';

const AdminDashboard: React.FC = () => {
  const [events, setEvents] = useState<Event[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [organizers, setOrganizers] = useState<Organizer[]>([]);
  const [organizersError, setOrganizersError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editorialBusy, setEditorialBusy] = useState(false);
  const [editorialError, setEditorialError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [eventsError, setEventsError] = useState<string | null>(null);
  const [eventsVersion, setEventsVersion] = useState(0);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [editingEvent, setEditingEvent] = useState<Event | null>(null);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const createEmptyEventForm = (): EventCreate => ({
    title: '',
    description: '',
    datetime: '',
    end_at: '',
    location: '',
    image_url: '',
    category_id: null,
    price_kind: 'unknown',
    price_amount: null,
    price_max: null,
    currency: null,
    rating: null,
    discount: null,
    payment_url: null,
    organizer_id: null,
    event_url: null,
    source: null,
  });
  const [formData, setFormData] = useState<EventCreate>(createEmptyEventForm());
  const [originalFormData, setOriginalFormData] = useState<EventCreate | null>(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [categoryFormData, setCategoryFormData] = useState<CategoryCreatePayload>({
    name: '',
    slug: '',
    is_active: true
  });
  const [categorySaving, setCategorySaving] = useState(false);
  const navigate = useNavigate();

  const slugify = (value: string) =>
    value
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-');

  const fetchEvents = () => setEventsVersion(version => version + 1);

  const fetchCategories = useCallback(async () => {
    setCategoriesLoading(true);
    try {
      const response = await categoriesApi.getAll(true);
      setCategories(response.data ?? []);
    } catch (error) {
      toast.error('Ошибка при загрузке категорий');
    } finally {
      setCategoriesLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setEventsError(null);
    setEvents([]);
    const load = async () => {
      try {
        const { data } = await eventsApi.getAdminAll(page, 50);
        if (!active) return;
        setTotalItems(data.total_items);
        setTotalPages(data.total_pages);
        const lastPage = Math.max(1, data.total_pages);
        if (page > lastPage) {
          setPage(lastPage);
          return;
        }
        setEvents(data.items ?? []);
      } catch (error) {
        if (!active) return;
        setEventsError('Ошибка при загрузке мероприятий');
        setTotalItems(0);
        setTotalPages(0);
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => { active = false; };
  }, [page, eventsVersion]);

  useEffect(() => {
    let active = true;
    organizersApi.getAll().then(({ data }) => {
      if (active) setOrganizers(data);
    }).catch(() => { if (active) setOrganizersError(true); });
    return () => { active = false; };
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    navigate('/login');
  };

  const handleCreateEvent = () => {
    setEditorialError(null);
    setEditingEvent(null);
    setOriginalFormData(null);
    setFormData(createEmptyEventForm());
    setShowModal(true);
  };

  const handleEditEvent = (event: Event) => {
    setEditorialError(null);
    setEditingEvent(event);
    const initialForm: EventCreate = {
      title: event.title,
      description: event.description || '',
      datetime: instantToEventInput(event.datetime),
      end_at: event.end_at ? instantToEventInput(event.end_at) : '',
      location: event.location,
      image_url: event.image_url || '',
      category_id: event.category_id ?? event.category?.id ?? null,
      ...pricingFromEvent(event),
      rating: event.rating ?? null,
      discount: event.discount ?? null,
      payment_url: event.payment_url ?? null,
      organizer_id: event.organizer_id ?? null,
      event_url: event.event_url ?? null,
      source: event.source ?? null,
    };
    setFormData(initialForm);
    setOriginalFormData(initialForm);
    setShowModal(true);
  };

  const handleDeleteEvent = async (id: number) => {
    if (window.confirm('Вы уверены, что хотите удалить это мероприятие?')) {
      try {
        await eventsApi.delete(id);
        toast.success('Мероприятие удалено');
        fetchEvents();
      } catch (error) {
        toast.error('Ошибка при удалении мероприятия');
      }
    }
  };

  const handleImageUpload = async (file: File) => {
    setUploadingImage(true);
    try {
      const response = await eventsApi.uploadImage(file);
      setFormData(prev => ({ ...prev, image_url: response.data.image_url }));
      toast.success('Изображение загружено');
    } catch (error) {
      toast.error('Ошибка при загрузке изображения');
    } finally {
      setUploadingImage(false);
    }
  };

  const apiError = (error: unknown): string => {
    const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
    if (detail && typeof detail === 'object' && 'fields' in detail) {
      const fields = (detail as { fields: Record<string, string> }).fields;
      return Object.entries(fields).map(([field, reason]) => `${field}: ${reason}`).join('; ');
    }
    return typeof detail === 'string' ? detail : error instanceof Error ? error.message : 'Ошибка сохранения';
  };

  const hasUnsavedChanges = originalFormData !== null && JSON.stringify(formData) !== JSON.stringify(originalFormData);

  // Editorial actions never submit unsaved form values or combine verification/publication.
  const handleEditorial = async (action: () => Promise<{ data: Event }>) => {
    if (!editingEvent || editorialBusy || saving || hasUnsavedChanges) return;
    setEditorialBusy(true);
    setEditorialError(null);
    try {
      const { data } = await action();
      setEditingEvent(data);
      fetchEvents();
      toast.success('Редакционное действие выполнено');
    } catch (error) {
      setEditorialError(apiError(error));
    } finally {
      setEditorialBusy(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving || editorialBusy) return;
    setSaving(true);
    setEditorialError(null);
    try {
      const normalizeNumber = (value: number | null | undefined) =>
        value !== null && value !== undefined && !Number.isNaN(value) ? value : null;

      const normalizeFields = (data: EventCreate): Omit<EventCreate, 'datetime' | 'end_at'> => {
        const normalizedRating = normalizeNumber(data.rating);
        const normalizedDiscount = normalizeNumber(data.discount);

        return {
          title: data.title,
          description: data.description || '',
          location: data.location,
          image_url: data.image_url || null,
          category_id: data.category_id ?? null,
          ...pricingPayload(data),
          rating:
            normalizedRating !== null
              ? Math.round(Math.min(10, Math.max(0, normalizedRating)) * 10) / 10
              : null,
          discount:
            normalizedDiscount !== null
              ? Math.round(Math.min(100, Math.max(0, normalizedDiscount)))
              : null,
          payment_url: data.payment_url ? data.payment_url.trim() || null : null,
          organizer_id: data.organizer_id ?? null,
          event_url: data.event_url?.trim() || null,
          source: data.source?.trim() || null,
        };
      };

      // Convert using the same Novosibirsk helpers; keep original microseconds.
      const start = editingEvent && formData.datetime === originalFormData?.datetime
        ? editingEvent.datetime : eventInputToInstant(formData.datetime, editingEvent?.datetime);
      const end = !formData.end_at ? null
        : editingEvent?.end_at && formData.end_at === originalFormData?.end_at ? editingEvent.end_at
        : eventInputToInstant(formData.end_at, editingEvent?.end_at || undefined);
      const comparable = (instant: string) => instant.replace(/(?:\.(\d+))?Z$/, (_, fraction = '') => `.${fraction.padEnd(6, '0')}Z`);
      if (end !== null && comparable(end) <= comparable(start)) {
        throw new Error('Дата окончания должна быть позже начала');
      }
      const fields = normalizeFields(formData);
      if (editingEvent && originalFormData) {
        const original = normalizeFields(originalFormData);
        const payload: EventUpdate = Object.fromEntries(
          Object.entries(fields).filter(([key, value]) =>
            value !== original[key as keyof typeof original])
        );
        if (pricingFields.some(key => fields[key] !== original[key])) {
          Object.assign(payload, pricingPayload(formData));
        }
        // Compare the Novosibirsk form snapshot first: untouched/reverted dates
        // never enter PUT, preserving server-side publication checks and precision.
        if (formData.datetime !== originalFormData.datetime) {
          const instant = eventInputToInstant(formData.datetime, editingEvent.datetime);
          if (instantToEventInput(instant) !== instantToEventInput(editingEvent.datetime)) {
            payload.datetime = instant;
          }
        }
        if ((formData.end_at || '') !== (originalFormData.end_at || '')) {
          if (end === null || !editingEvent.end_at ||
              instantToEventInput(end) !== instantToEventInput(editingEvent.end_at)) {
            payload.end_at = end;
          }
        }
        if (Object.keys(payload).length === 0) {
          setShowModal(false);
          return;
        }
        await eventsApi.update(editingEvent.id, payload);
        toast.success('Мероприятие обновлено');
      } else {
        const payload: EventCreate = {
          ...fields,
          datetime: start,
          end_at: end,
        };
        await eventsApi.create(payload);
        toast.success('Мероприятие создано');
      }
      setShowModal(false);
      if (!editingEvent && page !== 1) {
        setPage(1);
      } else {
        fetchEvents();
      }
    } catch (error) {
      setEditorialError(apiError(error));
    } finally {
      setSaving(false);
    }
  };

  const resetCategoryForm = () => {
    setCategoryFormData({ name: '', slug: '', is_active: true });
    setEditingCategory(null);
  };

  const handleCreateCategory = () => {
    resetCategoryForm();
    setShowCategoryModal(true);
  };

  const handleEditCategory = (category: Category) => {
    setEditingCategory(category);
    setCategoryFormData({
      name: category.name,
      slug: category.slug,
      is_active: category.is_active,
    });
    setShowCategoryModal(true);
  };

  const handleDeleteCategory = async (id: number) => {
    if (!window.confirm('Вы уверены, что хотите удалить эту категорию?')) {
      return;
    }
    try {
      await categoriesApi.delete(id);
      toast.success('Категория удалена');
      fetchCategories();
      fetchEvents();
    } catch (error) {
      toast.error('Ошибка при удалении категории');
    }
  };

  const handleCategoryNameChange = (value: string) => {
    setCategoryFormData(prev => {
      const next = { ...prev, name: value } as CategoryCreatePayload;
      const shouldUpdateSlug =
        !editingCategory ||
        !prev.slug ||
        slugify(prev.slug || '') === slugify(prev.name || '');
      if (shouldUpdateSlug) {
        next.slug = slugify(value);
      }
      return next;
    });
  };

  const handleCategorySlugChange = (value: string) => {
    setCategoryFormData(prev => ({ ...prev, slug: slugify(value) }));
  };

  const handleCategorySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = categoryFormData.name?.trim() ?? '';
    if (!trimmedName) {
      toast.error('Введите название категории');
      return;
    }

    const payloadBase = {
      name: trimmedName,
      slug: categoryFormData.slug ? slugify(categoryFormData.slug) : undefined,
      is_active: categoryFormData.is_active,
    } satisfies CategoryCreatePayload & CategoryUpdatePayload;

    setCategorySaving(true);
    try {
      if (editingCategory) {
        await categoriesApi.update(editingCategory.id, payloadBase);
        toast.success('Категория обновлена');
      } else {
        await categoriesApi.create(payloadBase);
        toast.success('Категория создана');
      }
      setShowCategoryModal(false);
      resetCategoryForm();
      fetchCategories();
      fetchEvents();
    } catch (error) {
      toast.error('Ошибка при сохранении категории');
    } finally {
      setCategorySaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <a href="/admin/import" className="block px-6 py-2">Импорт мероприятий</a>
      <a href="/admin/articles" className="block px-6 py-2">Статьи</a>
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <div className="bg-primary-600 p-2 rounded-lg">
                <Calendar className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Админ-панель</h1>
                <p className="text-sm text-gray-600">Управление мероприятиями</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center space-x-2 text-gray-600 hover:text-gray-900"
            >
              <LogOut className="h-5 w-5" />
              <span>Выйти</span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-12">
        {/* Categories management */}
        <section>
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">Категории</h2>
            <button
              onClick={handleCreateCategory}
              className="btn-primary flex items-center space-x-2"
            >
              <Tag className="h-5 w-5" />
              <span>Добавить категорию</span>
            </button>
          </div>

          <div className="bg-white shadow-sm rounded-lg overflow-hidden">
            {categoriesLoading ? (
              <div className="flex items-center justify-center py-12 space-x-3">
                <Loader2 className="h-5 w-5 animate-spin text-primary-600" />
                <span className="text-sm text-gray-600">Загрузка категорий...</span>
              </div>
            ) : categories.length === 0 ? (
              <div className="text-center py-12">
                <Tag className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Категории не созданы</h3>
                <p className="text-gray-500 mb-4">Добавьте первую категорию, чтобы организовать мероприятия</p>
                <button onClick={handleCreateCategory} className="btn-primary">
                  Добавить категорию
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Название
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Слаг
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Статус
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Действия
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {categories.map(category => (
                      <tr key={category.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {category.name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {category.slug}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`px-2 py-1 rounded-full text-xs font-medium ${
                              category.is_active
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {category.is_active ? 'Активна' : 'Скрыта'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex justify-end space-x-2">
                            <button
                              onClick={() => handleEditCategory(category)}
                              className="text-primary-600 hover:text-primary-900"
                            >
                              <Edit className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteCategory(category.id)}
                              className="text-red-600 hover:text-red-900"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        {/* Events */}
        <section>
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900">Мероприятия</h2>
            <button
              onClick={handleCreateEvent}
              className="btn-primary flex items-center space-x-2"
            >
              <Plus className="h-5 w-5" />
              <span>Добавить мероприятие</span>
            </button>
          </div>

          <div className="bg-white shadow-sm rounded-lg overflow-hidden">
            {loading ? (
              <div role="status" className="flex items-center justify-center py-12 space-x-3">
                <Loader2 className="h-5 w-5 animate-spin text-primary-600" />
                <span>Загрузка мероприятий...</span>
              </div>
            ) : eventsError ? (
              <div role="alert" className="text-center py-12">
                <p className="text-red-600 mb-4">{eventsError}</p>
                <button onClick={fetchEvents} className="btn-secondary">Повторить загрузку</button>
              </div>
            ) : events.length === 0 ? (
              <div className="text-center py-12">
                <Calendar className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Нет мероприятий</h3>
                <p className="text-gray-500 mb-4">Создайте первое мероприятие</p>
                <button onClick={handleCreateEvent} className="btn-primary">
                  Добавить мероприятие
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full table-fixed divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 w-2/5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Мероприятие
                      </th>
                      <th className="px-6 py-3 w-1/4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Место
                      </th>
                      <th className="px-6 py-3 w-1/4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Категория
                      </th>
                      <th className="px-6 py-3 w-1/6 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Действия
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {events.map((event) => (
                      <tr key={event.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            {event.image_url && (
                              <img
                                className="h-12 w-12 rounded-lg object-cover mr-4"
                                src={event.image_url}
                                alt={event.title}
                              />
                            )}
                            <div>
                              <div className="text-sm font-medium text-gray-900">
                                {event.title}
                                <div className="text-xs text-gray-500">
                                  {instantToEventInput(event.datetime).replace('T', ' ')} · Asia/Novosibirsk
                                </div>
                                <div className="text-xs text-gray-500">
                                  {event.publication_status} · {event.event_status}
                                </div>
                              </div>
                              {event.description && (
                                <div className="text-sm text-gray-500 truncate max-w-xs">
                                  {event.description}
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 truncate">
                          {event.location}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 truncate">
                          {event.category?.name ?? '—'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex justify-end space-x-2">
                            <button
                              aria-label={`Редактировать ${event.title}`}
                              onClick={() => handleEditEvent(event)}
                              className="text-primary-600 hover:text-primary-900"
                            >
                              <Edit className="h-4 w-4" />
                            </button>
                            <button
                              aria-label={`Удалить ${event.title}`}
                              onClick={() => handleDeleteEvent(event.id)}
                              className="text-red-600 hover:text-red-900"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          {!eventsError && (
            <nav aria-label="Страницы мероприятий" className="flex items-center justify-between mt-4 gap-4">
              <p className="text-sm text-gray-600">
                Страница {page} из {Math.max(1, totalPages)} · Всего мероприятий: {totalItems}
              </p>
              <div className="flex space-x-2">
                <button className="btn-secondary disabled:opacity-50" disabled={loading || page <= 1}
                  onClick={() => setPage(current => current - 1)}>Предыдущая</button>
                <button className="btn-secondary disabled:opacity-50" disabled={loading || page >= totalPages}
                  onClick={() => setPage(current => current + 1)}>Следующая</button>
              </div>
            </nav>
          )}
        </section>
      </main>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-semibold text-gray-900">
                  {editingEvent ? 'Редактировать мероприятие' : 'Создать мероприятие'}
                </h3>
                <button
                  onClick={() => setShowModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                {editorialError && <p role="alert" className="text-red-600">{editorialError}</p>}
                <fieldset disabled={saving || editorialBusy} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Название *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.title}
                    onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                    className="input-field"
                    placeholder="Введите название мероприятия"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Описание
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    className="input-field"
                    rows={4}
                    placeholder="Введите описание мероприятия"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Дата и время (Asia/Novosibirsk) *
                    </label>
                    <input
                      type="datetime-local"
                      aria-label="Дата и время Новосибирска"
                      step="any"
                      required
                      value={formData.datetime}
                      onChange={(e) => setFormData(prev => ({ ...prev, datetime: e.target.value }))}
                      className="input-field"
                    />
                  </div>

                  <div>
                    <label htmlFor="event-end-at" className="block text-sm font-medium text-gray-700 mb-2">
                      Дата и время окончания (Asia/Novosibirsk)
                    </label>
                    <input id="event-end-at" type="datetime-local" step="any"
                      aria-label="Дата и время окончания Новосибирска"
                      value={formData.end_at || ''}
                      onChange={(e) => setFormData(prev => ({ ...prev, end_at: e.target.value }))}
                      className="input-field" />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Место *
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.location}
                      onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))}
                      className="input-field"
                      placeholder="Введите место проведения"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Категория
                  </label>
                  <select
                    value={formData.category_id ?? ''}
                    onChange={(e) =>
                      setFormData(prev => ({
                        ...prev,
                        category_id: e.target.value ? Number(e.target.value) : null,
                      }))
                    }
                    className="input-field"
                    disabled={categoriesLoading}
                  >
                    <option value="">Не указано</option>
                    {categories
                      .filter(category => category.is_active)
                      .map(category => (
                        <option key={category.id} value={category.id}>
                          {category.name}
                        </option>
                      ))}
                  </select>
                  {!categoriesLoading && categories.filter(category => category.is_active).length === 0 && (
                    <p className="text-xs text-gray-500 mt-1">
                      Активных категорий пока нет. Добавьте их в разделе «Категории» ниже.
                    </p>
                  )}
                </div>

                <div>
                  <label htmlFor="event-organizer" className="block text-sm font-medium text-gray-700 mb-2">Организатор</label>
                  <select id="event-organizer" className="input-field" value={formData.organizer_id ?? ''}
                    disabled={organizersError}
                    onChange={e => setFormData(prev => ({ ...prev, organizer_id: e.target.value ? Number(e.target.value) : null }))}>
                    <option value="">Не указано</option>
                    {formData.organizer_id && !organizers.some(item => item.id === formData.organizer_id) &&
                      <option value={formData.organizer_id}>{editingEvent?.organizer?.name || `#${formData.organizer_id}`}</option>}
                    {organizers.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                  {organizersError && <p role="alert">Не удалось загрузить организаторов. Текущее значение сохранено.</p>}
                  {!organizersError && organizers.length === 0 && <p>Организаторы пока не заведены. Управление справочником отдельно.</p>}
                </div>
                <div>
                  <label htmlFor="event-url" className="block text-sm font-medium text-gray-700 mb-2">Событие / регистрация</label>
                  <input id="event-url" type="url" className="input-field" value={formData.event_url ?? ''}
                    onChange={e => setFormData(prev => ({ ...prev, event_url: e.target.value || null }))} />
                </div>
                <div>
                  <label htmlFor="event-source" className="block text-sm font-medium text-gray-700 mb-2">Первоисточник</label>
                  <input id="event-source" type="url" className="input-field" value={formData.source ?? ''}
                    onChange={e => setFormData(prev => ({ ...prev, source: e.target.value || null }))} />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <label htmlFor="price-kind" className="block text-sm font-medium text-gray-700 mb-2">Тип стоимости</label>
                    <select id="price-kind" className="input-field" value={formData.price_kind || 'unknown'}
                      onChange={e => setFormData(prev => ({ ...prev, price_kind: e.target.value as EventCreate['price_kind'],
                        price_amount: null, price_max: null, currency: ['fixed','from','range'].includes(e.target.value) ? 'RUB' : null }))}>
                      <option value="unknown">Стоимость неизвестна</option><option value="free">Бесплатно</option>
                      <option value="fixed">Фиксированная</option><option value="from">От</option>
                      <option value="range">Диапазон</option><option value="by_request">По запросу</option>
                    </select>
                    {['fixed','from','range'].includes(formData.price_kind || '') && <>
                      <label htmlFor="price-amount">{formData.price_kind === 'fixed' ? 'Сумма' : 'Минимальная сумма'}</label>
                      <input id="price-amount" className="input-field" inputMode="decimal" value={formData.price_amount ?? ''}
                        onChange={e => setFormData(prev => ({ ...prev, price_amount: e.target.value }))} />
                      {formData.price_kind === 'range' && <><label htmlFor="price-max">Максимальная сумма</label>
                        <input id="price-max" className="input-field" inputMode="decimal" value={formData.price_max ?? ''}
                          onChange={e => setFormData(prev => ({ ...prev, price_max: e.target.value }))} /></>}
                      <label htmlFor="price-currency">Валюта ISO 4217</label>
                      <input id="price-currency" className="input-field" value={formData.currency ?? ''}
                        onChange={e => setFormData(prev => ({ ...prev, currency: e.target.value.toUpperCase() }))} />
                    </>}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Рейтинг
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={10}
                      step="0.1"
                      value={formData.rating ?? ''}
                      onChange={(e) =>
                        setFormData(prev => ({
                          ...prev,
                          rating: e.target.value === '' ? null : Math.min(10, Math.max(0, Number(e.target.value))),
                        }))
                      }
                      className="input-field"
                      placeholder="Например, 8.5"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Скидка (%)
                    </label>
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step="1"
                      value={formData.discount ?? ''}
                      onChange={(e) =>
                        setFormData(prev => ({
                          ...prev,
                          discount: e.target.value === '' ? null : Math.min(100, Math.max(0, Number(e.target.value))),
                        }))
                      }
                      className="input-field"
                      placeholder="Например, 15"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Ссылка на оплату
                  </label>
                  <input
                    type="url"
                    aria-label="Ссылка на оплату"
                    value={formData.payment_url ?? ''}
                    onChange={(e) =>
                      setFormData(prev => ({
                        ...prev,
                        payment_url: e.target.value ? e.target.value : null,
                      }))
                    }
                    className="input-field"
                    placeholder="https://..."
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Укажите ссылку, по которой можно оплатить участие в мероприятии.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Изображение (афиша)
                  </label>
                  <div className="space-y-4">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          handleImageUpload(file);
                        }
                      }}
                      className="input-field"
                      disabled={uploadingImage}
                    />
                    {uploadingImage && (
                      <p className="text-sm text-gray-500">Загрузка изображения...</p>
                    )}
                    {formData.image_url && (
                      <div className="relative">
                        <img
                          src={formData.image_url}
                          alt="Предварительный просмотр"
                          className="w-full h-48 object-cover rounded-lg"
                        />
                        <button
                          type="button"
                          aria-label="Удалить изображение"
                          onClick={() => setFormData(prev => ({ ...prev, image_url: '' }))}
                          className="absolute top-2 right-2 bg-red-600 text-white rounded-full p-1"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex space-x-4">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="flex-1 btn-secondary"
                  >
                    Отмена
                  </button>
                  <button
                    type="submit"
                    className="flex-1 btn-primary"
                  >
                    {editingEvent ? 'Обновить' : 'Создать'}
                  </button>
                </div>
                </fieldset>
              </form>
              {editingEvent && (
                <fieldset disabled={saving || editorialBusy || hasUnsavedChanges} className="mt-6 space-y-3">
                  <p>Публикация: {editingEvent.publication_status} · Событие: {editingEvent.event_status}</p>
                  <p>Проверено: {editingEvent.verified_at || 'Нет'}</p>
                  <p className="text-sm text-gray-600">Сначала сохраните и заново откройте форму. Для критичных правок опубликованного события: в черновик → правки → проверка → публикация.</p>
                  <button type="button" className="btn-secondary" onClick={() => handleEditorial(() => eventsApi.verify(editingEvent.id))}>Подтвердить проверку</button>
                  <label className="block">Статус публикации
                    <select aria-label="Статус публикации" value={editingEvent.publication_status}
                      onChange={e => {
                        const status = e.target.value as PublicationStatus;
                        handleEditorial(() => eventsApi.changePublication(editingEvent.id, status));
                      }}>
                      <option value="draft">Черновик</option><option value="published">Опубликовано</option><option value="archived">Архив</option>
                    </select>
                  </label>
                  <label className="block">Статус мероприятия
                    <select aria-label="Статус мероприятия" value={editingEvent.event_status}
                      onChange={e => {
                        const status = e.target.value as EventStatus;
                        handleEditorial(() => eventsApi.changeStatus(editingEvent.id, status));
                      }}>
                      <option value="scheduled">Запланировано</option><option value="cancelled">Отменено</option><option value="postponed">Перенесено</option>
                    </select>
                  </label>
                </fieldset>
              )}
            </div>
          </div>
        </div>
      )}

      {showCategoryModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-semibold text-gray-900">
                  {editingCategory ? 'Редактировать категорию' : 'Создать категорию'}
                </h3>
                <button
                  onClick={() => {
                    setShowCategoryModal(false);
                    resetCategoryForm();
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>

              <form onSubmit={handleCategorySubmit} className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Название *
                  </label>
                  <input
                    type="text"
                    required
                    value={categoryFormData.name}
                    onChange={(e) => handleCategoryNameChange(e.target.value)}
                    className="input-field"
                    placeholder="Например, Концерты"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Слаг
                  </label>
                  <input
                    type="text"
                    value={categoryFormData.slug || ''}
                    onChange={(e) => handleCategorySlugChange(e.target.value)}
                    className="input-field"
                    placeholder="konce-rty"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Используется в адресной строке и фильтрах. Допустимы латинские буквы, цифры и дефис.
                  </p>
                </div>

                <div className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
                  <div>
                    <p className="text-sm font-medium text-gray-700">Категория активна</p>
                    <p className="text-xs text-gray-500">Неактивные категории не отображаются на сайте</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={categoryFormData.is_active !== false}
                    onChange={(e) =>
                      setCategoryFormData(prev => ({ ...prev, is_active: e.target.checked }))
                    }
                    className="h-5 w-5 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                  />
                </div>

                <div className="flex space-x-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowCategoryModal(false);
                      resetCategoryForm();
                    }}
                    className="flex-1 btn-secondary"
                  >
                    Отмена
                  </button>
                  <button
                    type="submit"
                    className="flex-1 btn-primary"
                    disabled={categorySaving}
                  >
                    {categorySaving ? 'Сохранение...' : 'Сохранить'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
