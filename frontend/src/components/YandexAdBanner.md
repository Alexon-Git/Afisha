# Интеграция с Яндекс.Директ

## Описание
Компонент `YandexAdBanner` предназначен для отображения контекстной рекламы Яндекс.Директ между хэдером и основным контентом сайта.

## Размеры баннера
- **Десктоп**: 728×90 пикселей (Leaderboard)
- **Мобильные устройства**: 320×50 пикселей (Mobile Banner)
- **Адаптивность**: Автоматически подстраивается под размер экрана

## Интеграция с Яндекс.Директ

### 1. Получение кода рекламы
1. Войдите в [Яндекс.Директ](https://direct.yandex.ru/)
2. Создайте новую кампанию или используйте существующую
3. Выберите тип рекламы "Контекстная реклама"
4. Создайте рекламный блок с размером 728×90 (Leaderboard) для десктопа или 320×50 (Mobile Banner) для мобильных
5. Получите код для вставки на сайт

### 2. Замена заглушки на реальный код
В файле `YandexAdBanner.tsx` замените содержимое компонента на полученный код:

```tsx
const YandexAdBanner: React.FC<YandexAdBannerProps> = ({ className = '' }) => {
  return (
    <div className={`yandex-ad-banner ${className}`}>
      {/* Вставьте сюда код от Яндекс.Директ */}
      <div id="yandex_rtb_R-A-XXXXXXX-X"></div>
      <script>
        (function(w, d, n, s, t) {
          w[n] = w[n] || [];
          w[n].push(function() {
            Ya.Context.AdvManager.render({
              blockId: "R-A-XXXXXXX-X",
              renderTo: "yandex_rtb_R-A-XXXXXXX-X",
              async: true
            });
          });
          t = d.getElementsByTagName("script")[0];
          s = d.createElement("script");
          s.type = "text/javascript";
          s.src = "//an.yandex.ru/system/context.js";
          s.async = true;
          t.parentNode.insertBefore(s, t);
        })(this, this.document, "yandexContextAsyncCallbacks");
      </script>
    </div>
  );
};
```

### 3. Альтернативный способ (рекомендуемый)
Для лучшей производительности используйте `useEffect` для загрузки скрипта:

```tsx
import React, { useEffect } from 'react';

const YandexAdBanner: React.FC<YandexAdBannerProps> = ({ className = '' }) => {
  useEffect(() => {
    // Загружаем скрипт Яндекс.Директ
    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.src = '//an.yandex.ru/system/context.js';
    script.async = true;
    document.head.appendChild(script);

    // Инициализируем рекламный блок
    if (window.Ya && window.Ya.Context) {
      window.Ya.Context.AdvManager.render({
        blockId: "R-A-XXXXXXX-X",
        renderTo: "yandex_rtb_R-A-XXXXXXX-X",
        async: true
      });
    }

    return () => {
      // Очистка при размонтировании компонента
      const existingScript = document.querySelector('script[src="//an.yandex.ru/system/context.js"]');
      if (existingScript) {
        existingScript.remove();
      }
    };
  }, []);

  return (
    <div className={`yandex-ad-banner ${className}`}>
      <div id="yandex_rtb_R-A-XXXXXXX-X"></div>
    </div>
  );
};
```

## Стили
Стили для баннера уже добавлены в `index.css`:
- Фиксированные размеры 300×250px
- Центрирование по горизонтали
- Адаптивность для мобильных устройств
- Отступы для лучшей интеграции в дизайн

## Требования Яндекс.Директ
- Минимальная ширина контейнера: 728px (десктоп) / 320px (мобильные)
- Минимальная высота контейнера: 90px (десктоп) / 50px (мобильные)
- Видимость баннера: не менее 50% площади
- Отсутствие наложения других элементов

## Тестирование
1. Проверьте отображение на разных устройствах
2. Убедитесь, что баннер не нарушает верстку
3. Проверьте загрузку рекламы в разных браузерах
4. Убедитесь, что баннер виден пользователям

## Примечания
- Замените `R-A-XXXXXXX-X` на реальный ID вашего рекламного блока
- Убедитесь, что домен добавлен в настройки кампании в Яндекс.Директ
- Для продакшена добавьте домен в CORS настройки backend

