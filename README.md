![](https://github.com/STBobcat/Bobcat-Proxy-xray/blob/main/BobcatProxy%20main%20logo.png)

# BobcatProxy - альтернативный клиент на базе xray 
  
**Используемые порты:** `SOCKS5` - 127.0.0.1:25443 
  

**Поддержка:**
+ VLESS со многими транспортами , Trojan , Hysteria2 , Shadowsocks ( в версии 3.0 его поддержка будет выпилена )
+ Сабки с vless:// ссылками
+ JSON сабки ( в тестовом режиме )
+ Смена user-agent ( в дальнейшем будет развиваться для маскировки клиента для особо наглых VPN сервисов которые локают сервис на клиенте Happ)

  
**История:** Изначально BobcatProxy был простым клиентом вдохновленным https://github.com/AKotov-dev/XRayGUI . Часть интерфейса была вдохновлена Happ ( который перестал нынче обновлять xray-core ) . В основном проблему с апдейтом xray-core он и решает .


**Изменения пре-релизов** 
+ 3.0 pre1 Добавлена частичная поддержка YAML сабок
+ 3.0 pre2 Полная поддержка YAML ( Clash ) сабок 


# Как запускать ? 
+ Скачайте последнюю версию
## 📥 Скачать / Download

<div align="left">
<table>
    <thead align="left">
        <tr>
            <th>ОС / Платформа</th>
            <th>Готовые сборки</th>
        </tr>
    </thead>
    <tbody align="left">
        <tr>
            <td><b>🪟 Windows (AMD64)</b></td>
            <td>
                <a href="https://github.com/STBobcat/Bobcat-Proxy-xray/releases/download/bobcat2.9/bobcat-proxy_2.9_win_amd64.exe"><img src="https://img.shields.io/badge/Windows-0078D6?style=flat&logo=windows&logoColor=white" alt="Windows 10/11"></a>
            </td>
        </tr>
        <tr>
            <td><b>🐧 Linux (AMD64) </b></td>
            <td>
                <a href="https://github.com/STBobcat/Bobcat-Proxy-xray/releases/download/bobcat2.9/bobcat-proxy_2.9_debian_amd64.deb"><img src="https://img.shields.io/badge/Debian-A81D33?style=flat&logo=debian&logoColor=white" alt="Debian x86_64"></a>
                <a href="https://github.com/STBobcat/Bobcat-Proxy-xray/releases/download/bobcat2.9/bobcat-proxy_2.9_linux_amd64"><img src="https://img.shields.io/badge/Linux-FCC624?style=flat&logo=linux&logoColor=black" alt="Linux x86_64"></a>
            </td>
        </tr>
        <tr>
       </tbody>
</table>
</div>

# Минимальные требования 
+ Под Linux glibc 2.41 ( минимальная ) . Под Windows минимум Win10 22H2 ( на более ранней может заработать но не гарантируется ) .
+ Можно понизить путем самостоятельной сборки через PyInstaller 
# Контакты :
+ OpenVK https://openvk.org/id45209
+ Telegram https://t.me/STBobcatchannel
  

