# Gas Management

[![Открыть Gas Management в Marketplace Home Assistant](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=Edheltur&repository=ha-gas-management&category=integration)

Учёт остатка CO₂ в баллонах по результатам взвешивания. Интеграция показывает остаток в граммах и заполнение в процентах.

## Установка

Требуется **Home Assistant 2026.11 или новее**.

Откройте Marketplace кнопкой выше или добавьте `Edheltur/ha-gas-management` через **Настройки → Marketplace → Добавить по ссылке**. Выберите **Gas Management → Установить**.

## Настройка баллона

В **Настройки → Устройства и службы → Добавить интеграцию → Gas Management** задайте имя, тару с вентилем и номинальную массу CO₂. Форма подставит случайное имя, а также 8,5 кг тары и 3 кг CO₂ для типового стального баллона 5 л. Сверьте массы для своего баллона.

После взвешивания обновите поля на странице устройства:

- **Вес оснастки** — редуктор, шланги и всё съёмное, что взвешивается вместе с баллоном.
- **Общий вес** — показание весов с баллоном, газом и оснасткой.

## Дашборд

Скопируйте [пример дашборда](examples/dashboard.yaml) в редактор YAML и подставьте ID своих сущностей. Для графика остатка нужна история Recorder.

## Разработка

В окружении с Python 3.14 установите зависимости из `requirements-dev.txt`. Запустите `ruff check .`, `ruff format --check .` и `python -m pytest`.
