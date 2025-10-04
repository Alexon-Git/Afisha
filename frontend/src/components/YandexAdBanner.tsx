import React from 'react';

interface YandexAdBannerProps {
  className?: string;
}

const YandexAdBanner: React.FC<YandexAdBannerProps> = ({ className = '' }) => {
  return (
    <div className={`yandex-ad-banner ${className}`}>
      {/* Заглушка для узкого баннера Яндекс.Директ */}
      <div className="w-full h-full flex items-center justify-between px-4 text-white">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
            <span className="text-sm">🎯</span>
          </div>
          <div>
            <div className="text-sm font-semibold">Реклама</div>
            <div className="text-xs opacity-75">728×90</div>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="text-right">
            <div className="text-sm font-medium">Специальное предложение</div>
            <div className="text-xs opacity-75">Узнать больше</div>
          </div>
          <div className="w-16 h-6 bg-white bg-opacity-20 rounded flex items-center justify-center">
            <span className="text-xs font-medium">КУПИТЬ</span>
          </div>
        </div>
      </div>
      
      {/* Комментарий для разработчика - заменить на реальный код Яндекс.Директ */}
      {/* 
      Для узкого баннера используйте размер 728×90 (Leaderboard) или 320×50 (Mobile Banner)
      <div id="yandex_rtb_R-A-1234567-1"></div>
      <script>
        (function(w, d, n, s, t) {
          w[n] = w[n] || [];
          w[n].push(function() {
            Ya.Context.AdvManager.render({
              blockId: "R-A-1234567-1",
              renderTo: "yandex_rtb_R-A-1234567-1",
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
      */}
    </div>
  );
};

export default YandexAdBanner;
