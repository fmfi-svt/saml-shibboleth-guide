# Inštalačný postup pre lokálny SAML development environment

## Základ

Začneme s čistou Ubuntu mašinou. V mojom prípade na omege vyrábam novú noble (24.04) virtuálku s mojim obvyklým postupom:

    virt-install -n samltest --ram 4096 --vcpus 2 --cpu host --location ./ubuntu-24.04.1-live-server-amd64.iso --osinfo detect=on,require=on --disk size=10 --extra-args="console=ttyS0 textmode=1"
    # vedľa
    virsh console samltest

Všetko default, okrem: Na začiatku "View SSH instructions" lebo je to menej bolestivé. Vyberám si "Ubuntu Server (minimized)", dávam iný mirror lebo defaultný má asi práve nejaký problém, vypínam "Set up this disk as an LVM group" ale to je zhruba jedno, confirm destructive action, nastavujem nejaké meno a heslo a hostname, zapínam "Install OpenSSH server", nezapínam žiadne snaps.

    sudo unminimize
    sudo apt install aptitude neovim zip unzip git tig

Mám zapísané že vraj Uniba používa shibboleth IdP 4.2.1, neviem či ešte stále. Najnovší 4.x je teraz 4.3.3.
Tipujem že je istá šanca (aspoň malá) že Uniba bude v dohľadnej dobe upgradovať na v5, takže by sa hodilo potom otestovať aj v5.
(V4 nedávno vypršal support. Na stránke https://shibboleth.net/downloads/identity-provider/ sa píše: "NOTE: The latest version of each software branch is maintained below, but at present V5 is current, V4 will be end-of-life on Sept 1, 2024, and all older versions have reached end-of-life and should never be used. Doing so puts an organization at significant risk.")



## Java 17

Najprv treba Javu. Vyzerá že Amazon Corretto 17 je dobrá voľba, vraj je "fully supported" pre
[IDP4 SystemRequirements](https://shibboleth.atlassian.net/wiki/spaces/IDP4/pages/1265631833/SystemRequirements) aj
[IDP5 SystemRequirements](https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199511079/SystemRequirements).
Inštalujem podľa https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html.

    wget -O - https://apt.corretto.aws/corretto.key | sudo gpg --dearmor -o /usr/share/keyrings/corretto-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/corretto-keyring.gpg] https://apt.corretto.aws stable main" | sudo tee /etc/apt/sources.list.d/corretto.list
    sudo apt-get update; sudo apt-get install -y java-17-amazon-corretto-jdk



## IdP 4

Inštalujem samotný Shibboleth IdP.

    mkdir ~/instalacia-tmp
    cd ~/instalacia-tmp
    wget 'https://shibboleth.net/downloads/identity-provider/latest4/shibboleth-identity-provider-4.3.3.tar.gz'
    tar xvf shibboleth-identity-provider-4.3.3.tar.gz
    cd shibboleth-identity-provider-4.3.3/bin/
    sudo ./install.sh

Odpovedám takto:

- `Source (Distribution) Directory (...): [...] ?` nechávam default
- `Installation Directory: [/opt/shibboleth-idp] ?` píšem /opt/idp4
  (Lebo časom chcem mať v4 aj v5 vedľa seba, nie upgradovať. Dúfam že neštandardný adresár nebudem ľutovať.)
- `Host Name: [192.168.xxx.yyy] ?` píšem idp.unibatest.internal
- `Backchannel PKCS12 Password:` generujem s prvým `base64 /dev/urandom | head -c 32` (nikde som nenašiel oficiálne odporúčanie akú dĺžku treba)
- `Re-enter password:`
- `Cookie Encryption Key Password:` generujem s druhým `base64 /dev/urandom | head -c 32`
- `Re-enter password:`
- `SAML EntityID: [https://idp.unibatest.internal/idp/shibboleth] ?` nechávam default
- `Attribute Scope: [unibatest.internal] ?` nechávam default

Vyrobil /opt/idp4. Zvlášť povedal že vyrobil /opt/idp4/metadata/idp-metadata.xml a /opt/idp4/war/idp.war.



## Jetty 12

Ďalej treba servlet container (nech je to čokoľvek). Vyberám Jetty 12 lebo je podporovaný pre v4 aj v5. Uniba používa Tomcat 9 (vidno z 404 errorov) ale nevadí.

(Toto sa ukázalo ako veľká chyba. Rozbehať Jetty 12 s IdP 4 fakt bolelo. Nabudúce by som asi skúsil Tomcat 9 pre IdP 4 a vedľa nich Tomcat 10 a IdP 5.)

Nenachádzam dobrú príručku o Jetty 12. Nejako to zimprovizujeme.

Choď na https://jetty.org/download.html. Nájdi aktuálnu linku Jetty 12 tgz (teraz práve je to 12.0.14).

    cd /tmp
    wget 'https://repo1.maven.org/maven2/org/eclipse/jetty/jetty-home/12.0.14/jetty-home-12.0.14.tar.gz'
    cd /opt
    sudo tar xf /tmp/jetty-home-12*.tar.gz

Ďalej je v tom bordel.
https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3516104706/Jetty12 je dokumentácia pre Jetty 12 + IdP 5 ale neexistuje podobný článok pre Jetty 12 + IdP 4.
IdP 4 System Requirements síce tvrdí že s Jetty 12 funguje ale nikde sa nepíše ako ich donútiť aby kooperovali.
https://git.shibboleth.net/view/?p=java-idp-jetty-base.git;a=tree;h=refs/heads/12;hb=refs/heads/12 obsahuje example config pre Jetty 12 ale tiež funguje iba s IdP 5.
Nejak som z tých zdrojov niečo pozliepal, a menil veci až kým to nezačalo fungovať:

    sudo mkdir /opt/jettybase4
    cd /opt/jettybase4
    sudo java -jar /opt/jetty-home-12.0.14/start.jar --add-modules=server,http,http-forwarded,ee8-annotations,ee8-deploy,ee8-jsp,ee8-jstl,ee8-plus

Vyrob súbor /opt/jettybase4/webapps/idp.xml s obsahom:

    <?xml version="1.0"?>
    <!DOCTYPE Configure PUBLIC "-//Jetty//Configure//EN" "http://www.eclipse.org/jetty/configure.dtd">
    <Configure class="org.eclipse.jetty.ee8.webapp.WebAppContext">
      <Set name="war">/opt/idp4/war/idp.war</Set>
      <Set name="contextPath">/idp</Set>
      <Set name="extractWAR">false</Set>
      <Set name="copyWebDir">false</Set>
      <Set name="copyWebInf">true</Set>
    </Configure>

(V java-idp-jetty-base.git sú nejaké veci navyše ktoré dúfam že netreba ale v produkcii by ich možno bolo treba.
Napríklad: nejaký lepší logging, static vypnuté directory indexes lebo sú vraj deravé, niečo o SAML backchannel, apod.)

Vyrob usera jetty a daj mu všeličo:

    sudo adduser --system --group --verbose jetty
    cd /opt/idp4
    sudo chown -R jetty:jetty logs metadata credentials conf war

(FWIW: Neviem čo má vlastniť root a čo jetty. Tento zoznam nie je z oficiálnych zdrojov ale z náhodných tutoriálov. Zvlášť to že aj `conf` tiež vlastní jetty je mi nejaké podozrivé.)

Spusti server (a počkaj cca 40 sekúnd) a otestuj že funguje:

    sudo -u jetty env -C /opt/jettybase4/ java -Didp.home=/opt/idp4 -jar /opt/jetty-home-12.0.14/start.jar
    curl -v http://localhost:8080/idp/status

Jetty má nejakú vstavanú systemd integráciu (viď /opt/jetty-home-12.0.14/bin/) ale nepáči sa mi.

Vyrob súbor /etc/systemd/system/jetty-idp4.service s obsahom:

    [Unit]
    After=network.target remote-fs.target nss-lookup.target
    [Service]
    ExecStart=java -Didp.home=/opt/idp4 -jar /opt/jetty-home-12.0.14/start.jar
    WorkingDirectory=/opt/jettybase4
    User=jetty
    Group=jetty
    [Install]
    WantedBy=multi-user.target

Zapni a spusti ho:

    sudo systemctl enable --now jetty-idp4

(FWIW: Poriadny produkčný setup by asi obsahoval aj nejaké ďalšie veci, napr Restart=, PrivateTmp=, apod.)



## Apache

Ďalej chcem Apache. Teoreticky ho netreba, Jetty môže priamo počúvať na 443, ale neskôr budem chcieť ďalšie virtual hosts a mod_auth_mellon.

    sudo apt install apache2

Vyrob súbor /etc/apache2/sites-available/idp.conf s obsahom:

    <VirtualHost *:443>
            ServerName idp.unibatest.internal
            SSLEngine on
            SSLCertificateFile      /etc/ssl/certs/ssl-cert-snakeoil.pem
            SSLCertificateKeyFile   /etc/ssl/private/ssl-cert-snakeoil.key
            DocumentRoot /nonexistent
            ErrorLog ${APACHE_LOG_DIR}/idp-error.log
            CustomLog ${APACHE_LOG_DIR}/idp-access.log combined
            ProxyPreserveHost On
            ProxyAddHeaders On
            ProxyPass / http://localhost:8080/
            ProxyPassReverse / http://localhost:8080/
            RequestHeader set X-Forwarded-Proto "https"
    </VirtualHost>

Veľká škoda že Jetty nepodporuje AJP. :(
Myslím že tento setup je trochu deravý (napr. Jetty číta remote IP aj z hlavičky "Forwarded:" o ktorej Apache nevie) ale pre jednoduchosť na to kašlem.

Zapni ho:

    sudo a2enmod headers proxy proxy_http ssl
    sudo a2ensite idp
    sudo systemctl restart apache2
    curl -v --insecure --resolve '*:443:127.0.0.1' https://idp.unibatest.internal/idp/status



## Prístup z Chrome

Normálnym ľuďom asi stačí pridať si vhodné riadky do /etc/hosts na vonkajšej fyzickej mašine kde beží prehliadač. Ja to zbytočne komplikujem.

Pretuneluj sa cez jeden alebo sériu viacerých `ssh -L` z localhost:12399 na virtuálku samltest:443.

Spusti u seba Chrome s prepínačmi:

    chrome --user-data-dir=/tmp/blabla --guest --host-resolver-rules="MAP *.unibatest.internal:443 127.0.0.1:12399" --ignore-certificate-errors

(--user-data-dir treba iba aby ti dovolil spustiť nový proces v novom profile ak už Chrome beží. Inak iba povie bežiacemu procesu nech otvorí nové okno ale na prepínače kašle. --guest vlastne asi netreba.)

Otvor https://idp.unibatest.internal/ a mal by si niečo vidieť.



## IdP konfigurácia

(Odmietam inštalovať navyše ešte aj LDAP server.) Uprav /opt/idp4/conf/authn/password-authn-config.xml takto:

- Vykomentuj riadok `<ref bean="shibboleth.LDAPValidator" />`
- Odkomentuj riadok `<bean parent="shibboleth.HTPasswdValidator" p:resource="%{idp.home}/credentials/demo.htpasswd" />`

Vyrob nejakých userov a daj im nejaké heslá:

    sudo -u jetty touch /opt/idp4/credentials/demo.htpasswd
    sudo -u jetty htpasswd /opt/idp4/credentials/demo.htpasswd aaa
    sudo -u jetty htpasswd /opt/idp4/credentials/demo.htpasswd bbb
    sudo -u jetty htpasswd /opt/idp4/credentials/demo.htpasswd ccc

Uprav súbor /opt/idp4/metadata/idp-metadata.xml a na vrchu vymaž `validUntil="..."` atribút.
Neviem či je korektnejšie ho vymazať alebo zmeniť, ale Shibboleth SP (viď nižšie) nemá rád defaultnú hodnotu (Metadata instance was invalid at time of acquisition.), a oficiálny idp.uniba.sk metadata ho tiež nemá.

Reštartuj ho:

    sudo systemctl restart jetty-idp4

Teraz už by si mal vedieť navštíviť https://idp.unibatest.internal/idp/profile/admin/hello a dostať login formulár čo sa správa rôzne keď zadáš správne/nesprávne meno/heslo.
(Síce keď sa správne prihlásim tak som aj tak dostal access denied, ale nevadí. Niečo to robí.)
(Podľa /opt/idp4/logs/idp-process.log je to lebo "No policy named 'AccessByAdminUser' found, returning default denial policy".)

Aj všeličo iné by sa dalo konfigurovať ale zatiaľ vyzerá že toto stačí.



## SP používajúci mod_auth_mellon

Vyrob súbor /etc/apache2/sites-available/spmellon.conf s obsahom:

    <VirtualHost *:443>
            ServerName spmellon.unibatest.internal
            SSLEngine on
            SSLCertificateFile      /etc/ssl/certs/ssl-cert-snakeoil.pem
            SSLCertificateKeyFile   /etc/ssl/private/ssl-cert-snakeoil.key
            DocumentRoot /var/www/spmellon
            ErrorLog ${APACHE_LOG_DIR}/spmellon-error.log
            CustomLog ${APACHE_LOG_DIR}/spmellon-access.log combined
            WSGIScriptAlias /pyinfo /var/www/spmellon/pyinfo.py process-group=spmellonpy
            WSGIScriptAlias /secret/pyinfo /var/www/spmellon/pyinfo.py process-group=spmellonpy
            WSGIDaemonProcess spmellonpy processes=1 threads=1
            WSGIApplicationGroup %{GLOBAL}
            <Location />
                    MellonEnable "info"
                    MellonSPMetadataFile /etc/apache2/spmellon/https_spmellon.unibatest.internal_mellon_metadata.xml
                    MellonSPPrivateKeyFile /etc/apache2/spmellon/https_spmellon.unibatest.internal_mellon_metadata.key
                    MellonSPCertFile /etc/apache2/spmellon/https_spmellon.unibatest.internal_mellon_metadata.cert
                    MellonIdPMetadataFile /opt/idp4/metadata/idp-metadata.xml
            </Location>
            <Location /secret>
                    Require valid-user
                    AuthType "Mellon"
                    MellonEnable "auth"
            </Location>
    </VirtualHost>

(Keďže SP aj IdP bežia na tej istej virtuálke, pre pohodlie rovno používam cestu k idp-metadata.xml. V produkcii by sa to xml samozrejme kopírovalo na druhú mašinu.)

Vyrob súbor /var/www/spmellon/index.html (a jeho adresár) s obsahom:

    <a href="/pyinfo/">pyinfo</a><br>
    <a href="/secret/">secret</a><br>
    <a href="/secret/pyinfo/">secret pyinfo</a><br>

Vyrob súbor /var/www/spmellon/pyinfo.py s obsahom:

    import pprint
    def application(environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain;charset=UTF-8')])
        return [pprint.pformat(environ).encode('utf-8')]

Vyrob súbor /var/www/spmellon/secret/index.html (a jeho adresár) s obsahom:

    <h1>secret</h1>

Uprav /opt/idp4/conf/metadata-providers.xml a na spodok (tesne nad posledný riadok `</MetadataProvider>`) dopíš:

    <MetadataProvider id="LocalMetadata_spmellon" xsi:type="FilesystemMetadataProvider" metadataFile="/etc/apache2/spmellon/https_spmellon.unibatest.internal_mellon_metadata.xml"/>

Spusti:

    sudo apt install libapache2-mod-auth-mellon libapache2-mod-wsgi-py3
    sudo mkdir /etc/apache2/spmellon
    cd /etc/apache2/spmellon
    sudo mellon_create_metadata https://spmellon.unibatest.internal/mellon/metadata https://spmellon.unibatest.internal/mellon
    sudo a2ensite spmellon
    sudo systemctl restart apache2
    sudo systemctl restart jetty-idp4

Teraz už by si mal vedieť navštíviť https://spmellon.unibatest.internal/ a vidieť tam všelijaké veci.

Dozvedeli sme sa že shibboleth IdP nám defaultne dá iba škaredý transient NameID (niečo dlhé čo začína `AAdzZWNyZXQx...`) a jediný atribút `schacHomeOrganization` AKA `urn:oid:1.3.6.1.4.1.25178.1.2.9` ktorého hodnota je `unibatest.internal`.



## SP používajúci mod_shib (Shibboleth SP)

    sudo apt install libapache2-mod-shib
    cd /etc/shibboleth
    sudo shib-keygen -n sp-signing
    sudo shib-keygen -n sp-encrypt

Uprav /etc/shibboleth/shibboleth2.xml takto:

- Prepíš `<ApplicationDefaults entityID="https://sp.example.org/shibboleth"` na `<ApplicationDefaults entityID="https://spshib.unibatest.internal/shibboleth"`
- Prepíš `<SSO entityID="https://idp.example.org/idp/shibboleth"` na `<SSO entityID="https://idp.unibatest.internal/idp/shibboleth"`
- Prepíš `discoveryProtocol="SAMLDS" discoveryURL="https://ds.example.org/DS/WAYF">` na `>`
- Odkomentuj a prepíš `<MetadataProvider type="XML" validate="true" path="partner-metadata.xml"/>` na `<MetadataProvider type="XML" validate="true" path="/opt/idp4/metadata/idp-metadata.xml"/>`

Vyrob súbor /etc/apache2/sites-available/spshib.conf s obsahom:

    <VirtualHost *:443>
            ServerName spshib.unibatest.internal
            SSLEngine on
            SSLCertificateFile      /etc/ssl/certs/ssl-cert-snakeoil.pem
            SSLCertificateKeyFile   /etc/ssl/private/ssl-cert-snakeoil.key
            DocumentRoot /var/www/spshib
            ErrorLog ${APACHE_LOG_DIR}/spshib-error.log
            CustomLog ${APACHE_LOG_DIR}/spshib-access.log combined
            WSGIScriptAlias /pyinfo /var/www/spshib/pyinfo.py process-group=spshibpy
            WSGIScriptAlias /secret/pyinfo /var/www/spshib/pyinfo.py process-group=spshibpy
            WSGIDaemonProcess spshibpy processes=1 threads=1
            WSGIApplicationGroup %{GLOBAL}
            <Location />
                    AuthType Shibboleth
                    Require shibboleth
                    ShibRequestSetting requireSession false
            </Location>
            <Location /secret>
                    AuthType Shibboleth
                    Require shib-session
                    ShibRequestSetting requireSession 1
            </Location>
    </VirtualHost>

Uprav /etc/apache2/conf-available/shib.conf takto: prepíš `ShibCompatValidUser Off` na `ShibCompatValidUser On`.
(Lebo inak sa rozbije spmellon, hádže chybu 401. Normálne by to nebolo treba ale tu sú v tom istom apachi obidva.)

Spusti:

    sudo cp -a /var/www/spmellon /var/www/spshib
    sudo a2ensite spshib
    sudo systemctl restart shibd
    sudo systemctl restart apache2
    sudo curl --insecure --resolve '*:443:127.0.0.1' https://spshib.unibatest.internal/Shibboleth.sso/Metadata -o /opt/meta-spshib.xml

Uprav /opt/idp4/conf/metadata-providers.xml a na spodok (tesne nad posledný riadok `</MetadataProvider>`) dopíš:

    <MetadataProvider id="LocalMetadata_spshib" xsi:type="FilesystemMetadataProvider" metadataFile="/opt/meta-spshib.xml"/>

Spusti:

    sudo systemctl restart jetty-idp4

Teraz už by si mal vedieť navštíviť https://spshib.unibatest.internal/ a vidieť tam všelijaké veci.

Vyzerá že Shibboleth SP úplne kašle na NameID (neuložil ho do žiadnej premennej), aspoň keď je transient.
Fakt chce dostať (nejaký) atribút, a keď ho nedostane tak nechá REMOTE_USER prázdny.
To je asi prečo v /etc/shibboleth/shibboleth2.xml defaultne je `REMOTE_USER="eppn subject-id pairwise-id persistent-id"`.

Niečo sa o nich píše v https://docs.oasis-open.org/security/saml-subject-id-attr/v1.0/saml-subject-id-attr-v1.0.html



## IdP 5

Normálnym ľuďom asi stačí mať jeden IdP naraz (prípadne skúšať upgradovanie zo 4 na 5).
Ja chcem vyvíjať plugin čo funguje na obidvoch, preto táto komplikácia.
Cieľ je aby bežal iba jeden naraz ale dalo sa medzi nimi pomerne ľahko prepínať.

    cd ~/instalacia-tmp
    wget 'https://shibboleth.net/downloads/identity-provider/latest5/shibboleth-identity-provider-5.1.3.tar.gz'
    tar xvf shibboleth-identity-provider-5.1.3.tar.gz
    cd shibboleth-identity-provider-5.1.3/bin/
    sudo ./install.sh

Odpovedám takto:

- `Installation Directory: [/opt/shibboleth-idp] ?` píšem /opt/idp5
- `Host Name: [192.168.xxx.yyy] ?` píšem idp.unibatest.internal
- `SAML EntityID: [https://idp.unibatest.internal/idp/shibboleth] ?` nechávam default
- `Attribute Scope: [unibatest.internal] ?` nechávam default

Vyrobil /opt/idp5. Zvlášť povedal že vyrobil /opt/idp5/metadata/idp-metadata.xml a /opt/idp5/war/idp.war.

Uprav /opt/idp5/conf/authn/password-authn-config.xml tak ako je napísané vyššie.
Vyrob /opt/idp5/credentials/demo.htpasswd tak ako je napísané vyššie (alebo proste skopíruj).
Uprav /opt/idp5/conf/metadata-providers.xml tak ako je napísané vyššie.

Uprav /opt/idp5/metadata/idp-metadata.xml takto: prepíš `<md:EntityDescriptorentityID=` na `<md:EntityDescriptor entityID=`. (Known bug OSJ-409 fixnutý v IdP 5.2.0.)
Atribút validUntil už tam nie je takže ho netreba odstraňovať.

Ako servlet container používam zase Jetty 12.
Tentoraz už by teoreticky malo fungovať použiť priamo config z `java-idp-jetty-base.git` vetvy `12`. Ale nepáči sa mi, lebo zapína https a podobne.
Preto si vyrobím svoj vlastný jetty-base. V podstate len vraciam späť svoje zmeny (zvlášť z ee8 späť na ee9).

    sudo mkdir /opt/jettybase5
    cd /opt/jettybase5
    sudo java -jar /opt/jetty-home-12.0.14/start.jar --add-modules=server,http,http-forwarded,ee9-annotations,ee9-deploy,ee9-jsp,ee9-jstl,ee9-plus

Vyrob súbor /opt/jettybase5/webapps/idp.xml s obsahom:

    <?xml version="1.0"?>
    <!DOCTYPE Configure PUBLIC "-//Jetty//Configure//EN" "http://www.eclipse.org/jetty/configure.dtd">
    <Configure class="org.eclipse.jetty.ee9.webapp.WebAppContext">
      <Set name="war">/opt/idp5/war/idp.war</Set>
      <Set name="contextPath">/idp</Set>
      <Set name="extractWAR">false</Set>
      <Set name="copyWebDir">false</Set>
      <Set name="copyWebInf">true</Set>
    </Configure>

(V java-idp-jetty-base.git sú nejaké veci navyše ktoré dúfam že netreba ale v produkcii by ich možno bolo treba.
Napríklad: nejaký lepší logging, static vypnuté directory indexes lebo sú vraj deravé, niečo o SAML backchannel, apod.)

Vyrob usera jetty (ak sa tak nestalo vyššie) a daj mu všeličo:

    sudo adduser --system --group --verbose jetty
    cd /opt/idp5
    sudo chown -R jetty:jetty logs metadata credentials conf war

(FWIW: Neviem čo má vlastniť root a čo jetty. Tento zoznam nie je z oficiálnych zdrojov ale z náhodných tutoriálov. Zvlášť to že aj `conf` tiež vlastní jetty je mi nejaké podozrivé.)

Vypni predošlý jetty (ak existuje).

    sudo systemctl disable --now jetty-idp4

Spusti server (a počkaj cca 40 sekúnd) a otestuj že funguje:

    sudo -u jetty env -C /opt/jettybase5/ java -Didp.home=/opt/idp5 -jar /opt/jetty-home-12.0.14/start.jar
    curl -v http://localhost:8080/idp/status

Jetty má nejakú vstavanú systemd integráciu (viď /opt/jetty-home-12.0.14/bin/) ale nepáči sa mi.

Vyrob súbor /etc/systemd/system/jetty-idp5.service s obsahom:

    [Unit]
    After=network.target remote-fs.target nss-lookup.target
    [Service]
    ExecStart=java -Didp.home=/opt/idp5 -jar /opt/jetty-home-12.0.14/start.jar
    WorkingDirectory=/opt/jettybase5
    User=jetty
    Group=jetty
    [Install]
    WantedBy=multi-user.target

Zapni a spusti ho:

    sudo systemctl enable --now jetty-idp5

(FWIW: Poriadny produkčný setup by asi obsahoval aj nejaké ďalšie veci, napr Restart=, PrivateTmp=, apod.)

    sudo ln -sf idp5 /opt/idpcurrent

Uprav /etc/apache2/sites-available/spmellon.conf a /etc/shibboleth/shibboleth2.xml takto: prepíš `/opt/idp4/metadata/idp-metadata.xml` na `/opt/idpcurrent/metadata/idp-metadata.xml`.

Vďaka tomu by sa malo dať prepínať medzi 4 a 5 tak, že jeden disabluješ, druhý enabluješ, prepíšeš idpcurrent symlinku, a reštartuješ apache2 a shibd.



## memcached

    sudo apt install memcached libmemcached-tools

Uprav /opt/idp5/conf/global.xml a dole pridaj: (obsah z https://shibboleth.atlassian.net/wiki/spaces/IDP5/pages/3199509576/StorageConfiguration ale upravený na localhost)

    <bean id="shibboleth.MemcachedStorageService"
          class="org.opensaml.storage.impl.memcached.MemcachedStorageService"
          c:timeout="2">
        <constructor-arg name="client">
            <bean class="net.spy.memcached.spring.MemcachedClientFactoryBean"
                  p:servers="localhost:11211"
                  p:protocol="BINARY"
                  p:locatorType="CONSISTENT"
                  p:failureMode="Redistribute">
                <property name="hashAlg">
                    <util:constant static-field="net.spy.memcached.DefaultHashAlgorithm.FNV1_64_HASH" />
                </property>
                <property name="transcoder">
                    <!-- DO NOT MODIFY THIS PROPERTY -->
                    <bean class="org.opensaml.storage.impl.memcached.StorageRecordTranscoder" />
                </property>
            </bean>
        </constructor-arg>
    </bean>

Uprav /opt/idp5/conf/idp.properties takto:

- Prepíš `#idp.session.StorageService = shibboleth.ClientSessionStorageService` na `idp.session.StorageService = shibboleth.MemcachedStorageService`
- Prepíš `#idp.replayCache.StorageService = shibboleth.StorageService` na `idp.replayCache.StorageService = shibboleth.MemcachedStorageService`
- Prepíš `#idp.artifact.StorageService = shibboleth.StorageService` na `idp.artifact.StorageService = shibboleth.MemcachedStorageService`
- Prepíš `#idp.cas.StorageService=shibboleth.StorageService` na `idp.cas.StorageService = shibboleth.MemcachedStorageService`




## Neupratané

    cd
    wget https://dlcdn.apache.org/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz
    tar xvf apache-maven-3.9.9-bin.tar.gz
    echo 'PATH=$HOME/apache-maven-3.9.9/bin:$PATH' >> .bashrc

Vyrob ~/.m2/settings.xml a daj tam obsah z https://shibboleth.atlassian.net/wiki/spaces/DEV/pages/2891317253/MavenRepositories

    chmod 755 ~

    sudo chown -R jetty:jetty /opt/idp4 /opt/idp5

V /var/www/spmellon/secret/index.html som pridal logout link.

Uprav /opt/idp5/conf/access-control.xml, odkomentuj sekciu AccessByAdminUser a zmeň `jdoe` na `bbb`.

    env -C /opt/idp5/bin/ sudo -u jetty ./plugin.sh -I net.shibboleth.idp.plugin.nashorn

Kvôli andrvotr/fabricate bolo treba pridať už aj idp.unibatest.internal do /etc/hosts (`127.0.1.1 samltest idp.unibatest.internal`).

Uprav /opt/idp5/conf/idp.properties a dole pridaj:

    andrvotr.httpclient.connectionDisregardTLSCertificate=true

    curl -LsSf https://astral.sh/uv/install.sh | sh



# Zbierka príkazov na SAML debugging

Keď vidíš POST request v ktorého form data body je `SAMLResponse=PD94...` (cesta môže byť všelijaká), je to proste base64.

    printf 'PD94...' | base64 -d | sed 's/></>\n</g'

Napríklad odpoveď od WSO2 IdP pre AIS SP sa tým dá prečítať.
Bohužiaľ Shibboleth IdP defaultne produkuje šifrované assertions (`<saml2:EncryptedAssertion><xenc:EncryptedData>`).
Ak máš súkromný kľúč daného SP, dá sa dešifrovať takto:

    sudo apt install xmlsec1
    printf 'PD94bWwg...' | base64 -d | sudo xmlsec1 --decrypt --privkey-pem /etc/apache2/spmellon/https_spmellon.unibatest.internal_mellon_metadata.key - | sed 's/></>\n</g'

Ak dostaneš chybu `func=xmlSecTransformNodeRead:file=transforms.c:line=1324:obj=unknown:subj=xmlSecTransformIdListFindByHref:error=1:xmlsec library function failed:href=http://www.w3.org/2009/xmlenc11#rsa-oaep`, znamená to, že potrebuješ xmlsec >= 1.3.0. Ten zatiaľ nemá v ubuntu balíček, ale je napríklad v conda-forge (veľa šťastia).

Nový xmlsec >= 1.3.0 namiesto `-` potrebuje `--lax-key-search /dev/stdin`.

    cat subor | base64 -d | sudo .../bin/xmlsec1 --decrypt --privkey-pem /etc/shibboleth/sp-encrypt-key.pem --lax-key-search /dev/stdin | sed 's/></>\n</g'

Keď je request tvaru `GET https://.../idp/profile/SAML2/Redirect/SSO?SAMLRequest=nZ...`
(t.j. HTTP-Redirect binding), je to raw zlib, dekóduj ho takto:

    printf 'nZ...' | base64 -d | python3 -c "import zlib,sys; sys.stdout.buffer.write(zlib.decompress(sys.stdin.buffer.read(), -8))" | sed 's/></>\n</g'

Obskúrny detail:
Shibboleth IdP niekedy generuje symetricky AEAD-šifrované hodnoty tvaru `AAdzZWNy...`.
Napríklad sa môžu vyskytnúť ako opaque NameID, alebo ako hodnota v localStorage ak je zapnutý client-side session storage (defaultne áno ale na unibe nie).
Ak máš súkromné kľúče IdP, a zaujíma ťa čo je vnútri hodnoty, dajú sa dešifrovať takto:

    sudo -u jetty /opt/idp4/bin/runclass.sh -Didp.home=/opt/idp4 net.shibboleth.idp.cli.DataSealerCLI --verbose net/shibboleth/idp/conf/sealer.xml dec "$str"

- `sudo -u jetty` samozrejme závisí od vlastníka credentials/.
- Keby bol v štandardnom adresári, stačilo by `/opt/shibboleth-idp/bin/sealer.sh` namiesto `/opt/idp4/bin/runclass.sh -Didp.home=/opt/idp4 net.shibboleth.idp.cli.DataSealerCLI`.
- Ak sa to nepodarí (napr. lebo vypršal timestamp uložený vnútri šifrovanej hodnoty), vypíše odvecnú chybu "Unable to access DataSealer from Spring context". Preto `--verbose`.
- Hodnota `net/shibboleth/idp/conf/sealer.xml` nie je zdokumentovaná, bola zistená grepovaním. Bez nej to nefunguje.






# Bordel TODO

niekde som čítal že nechcem zapínať releasing of persistent nameID, tak dúfam že veru.
niekto inštaluje mysql s komentárom že to treba kvôli persistent nameID (čo asi nechcem) a storing user consent (čo aspoň v dev nechcem), tak dúfam že netreba.

niekto mení idp-metadata.xml (ale v3) takto:
- z protocolSupportEnumeration  ruší urn:oasis:names:tc:SAML:1.1:protocol a urn:mace:shibboleth:1.0
- v <Extensions> maže vykomentovaný text a nastavuje DisplayName , Description, Logo, Logo
- niekam hádže logo.png
- maže <ArtifactResolutionService Binding="urn:oasis:names:tc:SAML:1.0:bindings:SOAP-binding" Location="https://idp.YOUR-DOMAIN:8443/idp/profile/SAML1/SOAP/ArtifactResolution" index="1"/> a ďalšiemu dáva index="1"
- maže <SingleSignOnService Binding="urn:mace:shibboleth:1.0:profiles:AuthnRequest" Location="https://idp.YOUR-DOMAIN/idp/profile/Shibboleth/SSO"/>
- maže :8443 zo všetkých url
- odkomentuje SingleLogoutService
- v <AttributeAuthorityDescriptor> v protocolSupportEnumeration namiesto urn:oasis:names:tc:SAML:1.1:protocol píše urn:oasis:names:tc:SAML:2.0:protocol
- odkomentuje <AttributeService Binding="urn:oasis:names:tc:SAML:2.0:bindings:SOAP" Location="https://idp.YOUR-DOMAIN/idp/profile/SAML2/SOAP/AttributeQuery"/>
- maže <AttributeService Binding="urn:oasis:names:tc:SAML:1.0:bindings:SOAP-binding" Location="https://idp.YOUR-DOMAIN:8443/idp/profile/SAML1/SOAP/AttributeQuery"/>
zvyšok už ma nebaví ale bolo to v https://github.com/LEARN-LK/IAM/blob/master/IDPonUbuntu.md


prvý tutoriál
- strč idp.example.com do /etc/hosts
- stiahni idp 3.x
- (v sudo shelli) ./install.sh
    Installation Directory: _[/opt/shibboleth-idp]_
    Hostname: _[idp.appd.com]_
    SAML EntityID: _[https://idp.appd.com/idp/shibboleth]_
    Attribute Scope: _[appd.com]_
    Backchannel PKCS12 Password: _#PASSWORD-FOR-BACKCHANNEL#_
    Re-enter password: _#PASSWORD-FOR-BACKCHANNEL#_
    Cookie Encryption Key Password: _#PASSWORD-FOR-COOKIE-ENCRYPTION#_
    Re-enter password: _#PASSWORD-FOR-COOKIE-ENCRYPTION#_
- potom všelijaká konfigurácia na ktorú zatiaľ kašlem lebo v v4 bude určite inak

druhý tutoriál
- apt install vim wget gnupg ca-certificates openssl apache2 ntp libservlet3.1-java liblogback-java --no-install-recommends
  - chcem apache2
- corretto (done)
- strč idp.example.com do /etc/hosts
- strč JAVA_HOME=/usr/lib/jvm/java-11-amazon-corretto do /etc/environment (to spravím až keď fakt bude treba)
- stiahni idp 4.x, rozbaľ do /usr/local/src
- (v sudo shelli) ./install.sh
    cd /usr/local/src/shibboleth-identity-provider-4.*/bin
    bash install.sh -Didp.host.name=$(hostname -f) -Didp.keysize=3072
    Buildfile: /usr/local/src/shibboleth-identity-provider-4.x.y/bin/build.xml

    install:
    Source (Distribution) Directory (press <enter> to accept default): [/usr/local/src/shibboleth-identity-provider-4.x.y] ?
    Installation Directory: [/opt/shibboleth-idp] ?
    Backchannel PKCS12 Password: ###PASSWORD-FOR-BACKCHANNEL###
    Re-enter password:           ###PASSWORD-FOR-BACKCHANNEL###
    Cookie Encryption Key Password: ###PASSWORD-FOR-COOKIE-ENCRYPTION###
    Re-enter password:              ###PASSWORD-FOR-COOKIE-ENCRYPTION###
    SAML EntityID: [https://idp.example.org/idp/shibboleth] ?
    Attribute Scope: [example.org] ?
- inštalujeme jetty 9 (pch)
- konfigurujeme jetty 9
- konfigurujeme apache 2 ako front end pre jetty
- 
