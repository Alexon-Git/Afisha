# Административная модерация импорта — PR-14A.2a

Backend prefix `/admin/import/candidates`, через gateway — `/api/admin/import/candidates`.
Каждый маршрут требует Bearer JWT и актуального администратора из БД.

- `GET /admin/import/candidates`: `page` (от 1), `limit` (1–100, default 20),
  фильтры `source_id`, `run_id` (first_run или last_run), `review_status`,
  `normalized_city` (точное значение). Фильтры объединяются через AND.
  Порядок: discovered_at DESC, id DESC. Ответ items/page/limit/total_items/total_pages.
  Пустая выдача имеет total_pages=0; страница за пределами списка возвращает items=[].
- `GET /admin/import/candidates/{id}`: все поля кандидата, warnings/provenance,
  observed/reviewed payload и сохранённые matches с их объяснениями и audit.
  Метаданные source/run (включая worker lease) этим API не выдаются.
- `POST /admin/import/candidates/{id}/approve`: тело ниже. Сохраняет только approved,
  reviewed_by/at/revision/note и reviewed_payload с fingerprint и явными решениями.
- `POST /admin/import/candidates/{id}/reject`: expected_revision + обязательная
  непустая review_note (до 2048 символов). Сохраняет rejected и серверный audit.

Пример approve:

```json
{
  "expected_revision": 1,
  "review_note": "Факты просмотрены редактором",
  "time_decision": "accept",
  "organizer_decision": "unresolved",
  "match_decisions": []
}
```

Time accept требует start_at и time_resolution explicit_offset/manual_confirmed;
неоднозначное время блокирует approve (422). Редактирование времени не входит в API.
Organizer: accept_proposed требует существующего proposed_organizer_id; unresolved
явно фиксирует, что организатор ещё не сопоставлен, и не создаёт Organizer.
Match decisions — полный список текущих matches, максимум 100, без повторов:
`{"match_id": 123, "decision": "defer"}` либо `not_a_duplicate`.
Чужой/пропущенный match или устаревшая candidate_revision match даёт 409.
Это только редакторские решения в reviewed_payload; состояние CandidateMatch,
связь с Event и дедупликация этим действием не меняются.

Допустимые переходы: pending/needs_review → approved либо rejected.
Все повторы и решения для approved/rejected/converted/linked возвращают 409;
переоткрытия нет. revision не увеличивается от решения; reviewed_revision фиксирует
версию просмотренных фактов. Неверная expected_revision → 409.
Дополнительные поля тела запрещены (422), audit/статусы/связи задаёт только сервер.
Нет передачи verified_at, publication_status или произвольного payload.

Транзакция блокирует и обновляет кандидата с refresh, проверяет источник обоих
referenced runs под блокировками, использует conditional UPDATE по исходным
revision/status/source/run IDs. Ровно один конкурентный редактор может сохранить
решение. Любая ошибка до commit откатывает все изменения; сбой БД → безопасный 503.
Отсутствующий кандидат → 404; нет Bearer → 403 по существующему HTTPBearer,
невалидный/истёкший JWT → 401, обычный пользователь → 403.

Ограничения: approve не создаёт Event, не ставит verified_at и не публикует.
Approval кандидата не означает готовность Event к публикации. Будущий promote/link
обязан повторно проверить revision, актуальные факты, policy, организатора и matches.
Вставка/изменение кандидатов и сброс approval, worker, сеть, source/run management,
PATCH/recheck/link/promote, UI отсутствуют. Более 100 matches требует отдельного
решения, approve такого кандидата сейчас блокируется. Cross-source целостность
проверяется при модерации; универсальной DB-гарантии для будущих писателей пока нет.
