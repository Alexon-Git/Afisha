import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  categoriesApi,
  Category,
  CategoryCreatePayload,
  CategoryUpdatePayload,
  Event,
  EventCreate,
  eventsApi,
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

const AdminDashboard: React.FC = () => {
  const [events, setEvents] = useState<Event[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [editingEvent, setEditingEvent] = useState<Event | null>(null);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [formData, setFormData] = useState<EventCreate>({
    title: '',
    description: '',
    datetime: '',
    location: '',
    image_url: '',
    category_id: null
  });
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

  useEffect(() => {
    fetchEvents();
    fetchCategories();
  }, []);

  const fetchEvents = async () => {
    try {
      const response = await eventsApi.getAll(1, 50);
      setEvents(response.data.items ?? []);
    } catch (error) {
      toast.error('Ошибка при загрузке мероприятий');
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    setCategoriesLoading(true);
    try {
      const response = await categoriesApi.getAll(true);
      setCategories(response.data ?? []);
    } catch (error) {
      toast.error('Ошибка при загрузке категорий');
    } finally {
      setCategoriesLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    navigate('/admin/login');
  };

  const handleCreateEvent = () => {
    setEditingEvent(null);
    setFormData({
      title: '',
      description: '',
      datetime: '',
      location: '',
      image_url: '',
      category_id: null
    });
    setShowModal(true);
  };

  const handleEditEvent = (event: Event) => {
    setEditingEvent(event);
    setFormData({
      title: event.title,
      description: event.description || '',
      datetime: new Date(event.datetime).toISOString().slice(0, 16),
      location: event.location,
      image_url: event.image_url || '',
      category_id: event.category?.id ?? null
    });
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Ensure datetime is sent as full ISO string (with seconds) or undefined
      const payload: EventCreate = {
        ...formData,
        category_id: formData.category_id ?? null,
        datetime: new Date(formData.datetime).toISOString(),
      };

      if (editingEvent) {
        await eventsApi.update(editingEvent.id, payload);
        toast.success('Мероприятие обновлено');
      } else {
        await eventsApi.create(payload);
        toast.success('Мероприятие создано');
      }
      setShowModal(false);
      fetchEvents();
    } catch (error) {
      toast.error('Ошибка при сохранении мероприятия');
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

  const formatDateTime = (datetime: string) => {
    return new Date(datetime).toLocaleString('ru-RU');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
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

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Actions */}
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

        {/* Events List */}
        <div className="bg-white shadow-sm rounded-lg overflow-hidden">
          {events.length === 0 ? (
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
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Мероприятие
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Дата и время
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Место
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Категория
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
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
                            </div>
                            {event.description && (
                              <div className="text-sm text-gray-500 truncate max-w-xs">
                                {event.description}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatDateTime(event.datetime)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {event.location}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {event.category?.name ?? '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end space-x-2">
                          <button
                            onClick={() => handleEditEvent(event)}
                            className="text-primary-600 hover:text-primary-900"
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                          <button
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

        {/* Categories management */}
        <div className="mt-16">
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
        </div>
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
                      Дата и время *
                    </label>
                    <input
                      type="datetime-local"
                      required
                      value={formData.datetime}
                      onChange={(e) => setFormData(prev => ({ ...prev, datetime: e.target.value }))}
                      className="input-field"
                    />
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
              </form>
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
