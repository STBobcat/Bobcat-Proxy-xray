<div align="center">
  <img src="https://github.com/STBobcat/Bobcat-Proxy-xray/blob/main/BobcatProxy%20main%20logo.png" alt="BobcatProxy Logo" width="220">
  <h1>BobcatProxy</h1>
  <p>Альтернативный GUI-клиент на базе <b>Xray-core</b></p>
</div>

---

## ⚙️ Базовая конфигурация
По умолчанию клиент поднимает локальный прокси-сервер:
- **Тип:** `SOCKS5`
- **Адрес:** `127.0.0.1`
- **Порт:** `25443`

---

## ⚡ Возможности и поддержка
- **Протоколы:** VLESS (с различными типами транспорта), Trojan, Hysteria2, Shadowsocks *(поддержка SS будет прекращена в версии 3.0)*.
- **Импорт конфигураций:** 
  - Ссылки формата `vless://`
  - JSON-конфиги *(тестовый режим)*
  - YAML / Clash-сабки *(полная поддержка с версии 3.0)*
- **Маскировка:** Смена User-Agent *(в разработке: расширенная маскировка для обхода блокировок на уровне клиента со стороны недобросовестных VPN-сервисов)*.

---

## 📖 О проекте
Изначально BobcatProxy был вдохновлен проектом [XRayGUI](https://github.com/AKotov-dev/XRayGUI), а элементы интерфейса заимствованы из клиента Happ (разработка которого, к сожалению, приостановлена). 

**Главная цель проекта** — предоставить стабильный, обновляемый и независимый клиент с актуальной версией `xray-core`, решая проблему устаревания ядер в аналогичных решениях.

### 🔄 История изменений
- **3.0:** Релизная версия. Полная поддержка YAML (Clash) сабок, актуальные сборки под все основные платформы.
- **3.0 pre2:** Полная поддержка YAML (Clash) сабок.
- **3.0 pre1:** Добавлена частичная поддержка YAML сабок.

---

## 📥 Скачать (Download)

| ОС / Платформа | Архитектура | Ссылка для скачивания |
| :--- | :---: | :---: |
| 🪟 **Windows** | AMD64 | [Скачать .exe](https://github.com/STBobcat/Bobcat-Proxy-xray/releases/download/bobcat3.1/bobcat_proxy_3.1_win_amd64.exe) <br>![Windows](https://img.shields.io/badge/Windows-0078D6?style=flat&logo=windows&logoColor=white) |
| 🐧 **Linux (Debian/Ubuntu)** | AMD64 | [Скачать .deb](https://github.com/STBobcat/Bobcat-Proxy-xray/releases/download/bobcat3.1/bobcat_proxy_3.1_debian_amd64.deb) <br>![Debian](https://img.shields.io/badge/Debian-A81D33?style=flat&logo=debian&logoColor=white) |
| 🐧 **Linux (Generic Binary)** | AMD64 | [Скачать бинарник](https://github.com/STBobcat/Bobcat-Proxy-xray/releases/download/bobcat3.1/bobcat_proxy_3.1_linux_amd64) <br>![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat&logo=linux&logoColor=black) |
| 🚩 **FreeBSD** | AMD64 | [Скачать бинарник](https://github.com/STBobcat/Bobcat-Proxy-xray/releases/download/bobcat3.1/bobcat_proxy_3.1_freebsd_amd64) <br>![FreeBSD](https://img.shields.io/badge/FreeBSD-8C0000?style=flat&logo=freebsd&logoColor=white) |

---

## 💻 Системные требования
- **Linux:** `glibc` версии 2.41 и выше *(минимальная)*. *(Примечание: при необходимости требования можно понизить путем самостоятельной компиляции через `PyInstaller`)*.
- **Windows:** Windows 10 (22H2) или новее *(на более ранних версиях работа не гарантируется , но возможна )*.
- **FreeBSD:** FreeBSD 15.1 и новее ( если выйдет )

---

## 📬 Контакты
- 💬 **Telegram:** [@STBobcatchannel](https://t.me/STBobcatchannel)
- 🌐 **OpenVK:** [id45209](https://openvk.org/id45209)
