# AeroNet

AeroNet — лёгкая глобальная карта для виртуальной авиации и MSFS 2020.

## Что сейчас есть

- Карта мира на Leaflet с подложкой OpenStreetMap.
- Аэропортовые точки из ежедневной открытой базы OurAirports: аэропорты, аэродромы, вертолётные и гидроаэродромы, включая записи о закрытых объектах.
- Кластеризация точек, чтобы карта оставалась отзывчивой при большом количестве объектов.
- Поиск аэропортов по ICAO, IATA, названию и городу.
- Карточка аэропорта с запросом METAR по ICAO.
- Самолёты и диспетчеры пока не отображаются: интеграция реального трафика JoinFS/MSFS ещё не подключена.

## Источники данных

- Airport database: [OurAirports](https://ourairports.com/data/) — public domain, обновляется ежедневно; данные не гарантируют точность.
- Map tiles: [OpenStreetMap](https://www.openstreetmap.org/copyright). Не скрывайте атрибуцию и соблюдайте [политику тайлов](https://operations.osmfoundation.org/policies/tiles/).
- METAR: [metars.eu API](https://metars.eu/learn/api), без API-ключа; данные поступают из NOAA Aviation Weather Center. Не использовать для реальных полётов.

## Публикация

Сайт — статическая страница `index.html`, публикация настроена через GitHub Pages.
