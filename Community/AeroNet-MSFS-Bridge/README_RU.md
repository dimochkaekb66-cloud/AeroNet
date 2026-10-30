# AeroNet MSFS 2020 Bridge — Community folder edition

Эта папка предназначена для размещения внутри каталога MSFS 2020 Community.

Важно: plugin.py — внешний Python SimConnect-клиент. MSFS не исполняет Python-файлы непосредственно из Community. Для автозапуска используется exe.xml: он запускает cmd.exe, который вызывает start.bat, а тот запускает Python-мост из этой папки.

## 1. Установка в Community

Скопируйте всю папку AeroNet-MSFS-Bridge непосредственно в активный каталог Community:

Community\AeroNet-MSFS-Bridge\plugin.py

Найдите активный Community через MSFS:
Developer Mode → Tools → Virtual File System → Open Community Folder.

Типовые пути:
- Microsoft Store / Xbox App: %LOCALAPPDATA%\Packages\Microsoft.FlightSimulator_8wekyb3d8bbwe\LocalCache\Packages\Community
- Steam: %APPDATA%\Microsoft Flight Simulator\Packages\Community

Используйте именно тот каталог, который открывает сам симулятор.

## 2. Установка Python и библиотек

Нужен 64-битный Python 3.11 для Windows. Установите Python с python.org, включив Python Launcher.

Затем дважды нажмите install-deps.bat внутри папки AeroNet-MSFS-Bridge. Скрипт установит:
- SimConnect (Python-SimConnect)
- websockets

Либо выполните вручную в терминале из этой папки:

py -3.11 -m pip install -r requirements.txt

## 3. Первый запуск вручную

1. Запустите MSFS 2020 и загрузите полёт.
2. Запустите start.bat.
3. Откройте AeroNet в браузере на том же компьютере.
4. В блоке MSFS 2020 Telemetry Link нажмите Connect.

Адрес WebSocket: ws://127.0.0.1:8787.

Пока MSFS не запущен, мост продолжает ждать и повторять подключение к SimConnect.

## 4. Автозапуск вместе с MSFS

exe.xml — конфигурация внешних приложений, а не файл внутри Community. Скопируйте только блок Launch.Addon из exe.xml.example в существующий exe.xml.

Сначала:
- Закройте MSFS.
- Сделайте резервную копию exe.xml, если он уже есть.
- Замените C:\YOUR\MSFS\Community\AeroNet-MSFS-Bridge\start.bat на полный реальный путь к start.bat.
- Не удаляйте другие записи Launch.Addon из существующего файла.

Типичные места exe.xml:
- Microsoft Store: %LOCALAPPDATA%\Packages\Microsoft.FlightSimulator_8wekyb3d8bbwe\LocalCache\exe.xml
- Steam: %APPDATA%\Microsoft Flight Simulator\exe.xml

После сохранения запустите MSFS. Он вызовет cmd.exe, который запустит start.bat и Python-мост. Консольное окно моста останется видимым.

## 5. Передача телеметрии

Мост отправляет JSON примерно раз в секунду:
- latitude
- longitude
- altitude_ft
- heading — истинный курс в градусах
- groundspeed_kts
- callsign

При остановке полёта, потере SimConnect или прекращении обновления телеметрии мост отправляет состояние connected: false. Сам AeroNet дополнительно удаляет маркер при разрыве WebSocket или тайм-ауте входящих координат.

## 6. Ограничения и безопасность

- Это внешний SimConnect companion, хранящийся в Community, а не встроенный WASM-модуль.
- Сервер слушает только 127.0.0.1, не открывается для других компьютеров в сети.
- Для работы требуется Windows, MSFS 2020, 64-битный Python 3.11 и установленный пакет SimConnect.
- Если используете защитное ПО, разрешите локальный loopback WebSocket на порту 8787.
